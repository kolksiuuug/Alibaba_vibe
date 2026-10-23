"""Сервис переходов: аудит и уведомление в одной транзакции, 409, идемпотентность."""

import pytest
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, select

from app.domain.errors import CommentRequired, InvalidTransition
from app.domain.state_machine import Actor
from app.domain.statuses import Status
from app.models import Application, AuditEvent, Notification
from app.services.transitions import transition
from tests.factories import make_analyst, make_application

S = Status


def _count(db: SQLAlchemy, model: type) -> int:
    return db.session.scalar(select(func.count()).select_from(model))


def test_transition_writes_status_audit_and_notification(db: SQLAlchemy) -> None:
    application = make_application(status=S.DRAFT)
    client = application.created_by

    result = transition(application, S.SUBMITTED, actor=Actor.CLIENT, actor_user=client)
    db.session.commit()

    assert result.changed is True
    assert result.source is S.DRAFT
    assert application.status is S.SUBMITTED
    event = db.session.scalars(select(AuditEvent)).one()
    assert (event.from_status, event.to_status, event.actor) == ("draft", "submitted", "client")
    assert event.actor_user_id == client.id
    assert event.application_id == application.id
    notification = db.session.scalars(select(Notification)).one()
    assert notification.user_id == client.id
    assert notification.application_id == application.id
    assert notification.title
    assert notification.body
    assert notification.is_read is False


def test_repeat_into_current_status_is_idempotent(db: SQLAlchemy) -> None:
    application = make_application(status=S.SUBMITTED)

    result = transition(application, S.SUBMITTED, actor=Actor.CLIENT)

    assert result.changed is False
    assert application.status is S.SUBMITTED
    assert _count(db, AuditEvent) == 0
    assert _count(db, Notification) == 0


def test_invalid_transition_raises_and_writes_nothing(db: SQLAlchemy) -> None:
    application = make_application(status=S.DRAFT)

    with pytest.raises(InvalidTransition):
        transition(application, S.ISSUED, actor=Actor.SYSTEM)

    assert application.status is S.DRAFT
    assert _count(db, AuditEvent) == 0
    assert _count(db, Notification) == 0


def test_wrong_actor_is_rejected(db: SQLAlchemy) -> None:
    application = make_application(status=S.SUBMITTED)

    with pytest.raises(InvalidTransition):
        transition(application, S.CHECKING, actor=Actor.CLIENT)

    assert application.status is S.SUBMITTED


def test_analyst_comment_is_required_and_stored(db: SQLAlchemy) -> None:
    application = make_application(status=S.MANUAL_REVIEW)
    analyst = make_analyst()

    with pytest.raises(CommentRequired):
        transition(application, S.REJECTED, actor=Actor.ANALYST, actor_user=analyst, comment=" ")
    transition(
        application,
        S.REJECTED,
        actor=Actor.ANALYST,
        actor_user=analyst,
        comment="Высокая долговая нагрузка",
    )
    db.session.commit()

    event = db.session.scalars(select(AuditEvent)).one()
    assert event.comment == "Высокая долговая нагрузка"
    assert event.actor_user_id == analyst.id
    assert application.status is S.REJECTED


def test_reason_and_custom_notification_body_are_stored(db: SQLAlchemy) -> None:
    application = make_application(status=S.CHECKING)

    transition(
        application,
        S.MANUAL_REVIEW,
        actor=Actor.SYSTEM,
        reason="bki_unavailable",
        notification_body="Бюро кредитных историй не ответило, заявку проверит аналитик.",
    )
    db.session.commit()

    assert db.session.scalars(select(AuditEvent)).one().reason == "bki_unavailable"
    notification = db.session.scalars(select(Notification)).one()
    assert notification.body == "Бюро кредитных историй не ответило, заявку проверит аналитик."


def test_status_cannot_be_assigned_directly(db: SQLAlchemy) -> None:
    application = make_application()

    with pytest.raises(AttributeError):
        application.status = S.ISSUED  # type: ignore[misc]


def test_status_is_queryable(db: SQLAlchemy) -> None:
    make_application(status=S.MANUAL_REVIEW)
    make_application(status=S.DRAFT)

    found = db.session.scalars(
        select(Application).where(Application.status == S.MANUAL_REVIEW.value)
    ).all()

    assert [a.status for a in found] == [S.MANUAL_REVIEW]


def test_rollback_discards_status_audit_and_notification(db: SQLAlchemy) -> None:
    application = make_application(status=S.DRAFT)
    application_id = application.id
    db.session.commit()

    transition(application, S.SUBMITTED, actor=Actor.CLIENT)
    db.session.rollback()

    assert db.session.get(Application, application_id).status is S.DRAFT
    assert _count(db, AuditEvent) == 0
    assert _count(db, Notification) == 0


def test_happy_path_records_every_transition(db: SQLAlchemy) -> None:
    application = make_application(status=S.DRAFT)
    analyst = make_analyst()
    path = [
        (S.SUBMITTED, Actor.CLIENT),
        (S.CHECKING, Actor.SYSTEM),
        (S.MANUAL_REVIEW, Actor.SYSTEM),
        (S.OFFER, Actor.ANALYST),
        (S.ACCEPTED, Actor.CLIENT),
        (S.SIGNED, Actor.CLIENT),
        (S.ISSUED, Actor.SYSTEM),
    ]

    for target, actor in path:
        is_analyst = actor is Actor.ANALYST
        transition(
            application,
            target,
            actor=actor,
            actor_user=analyst if is_analyst else None,
            comment="Обороты подтверждены" if is_analyst else None,
        )
    db.session.commit()

    events = db.session.scalars(select(AuditEvent).order_by(AuditEvent.id)).all()
    assert [(e.from_status, e.to_status) for e in events] == [
        ("draft", "submitted"),
        ("submitted", "checking"),
        ("checking", "manual_review"),
        ("manual_review", "offer"),
        ("offer", "accepted"),
        ("accepted", "signed"),
        ("signed", "issued"),
    ]
    assert _count(db, Notification) == len(path)


def test_every_status_has_a_notification_text(app: Flask) -> None:
    from app.services.notifications import STATUS_MESSAGES

    assert set(STATUS_MESSAGES) == set(Status) - {S.DRAFT}
    for title, body in STATUS_MESSAGES.values():
        assert title
        assert "{id}" in body
