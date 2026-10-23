"""Единственная точка смены статуса заявки.

Переход в той же транзакции пишет AuditEvent и Notification клиенту. Коммит делает
вызывающий сервис, поэтому смену статуса можно объединить с другими изменениями
(например, с постановкой задачи в очередь конвейера).
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from app.domain.state_machine import Actor, check_transition
from app.domain.statuses import Status
from app.extensions import db
from app.models import Application, AuditEvent, User
from app.services.notifications import status_notification

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class TransitionResult:
    application: Application
    source: Status
    changed: bool


def transition(
    application: Application,
    target: Status,
    *,
    actor: Actor,
    actor_user: User | None = None,
    reason: str | None = None,
    comment: str | None = None,
    notification_body: str | None = None,
) -> TransitionResult:
    """Перевести заявку в target или поднять InvalidTransition / CommentRequired.

    Повтор перехода в текущий статус идемпотентен: ничего не пишет и возвращает
    changed=False.
    """
    # Блокируем строку заявки до конца транзакции: параллельные переходы не гонятся
    db.session.flush()
    db.session.refresh(application, with_for_update=True)

    source = application.status
    if source is target:
        return TransitionResult(application, source, changed=False)

    check_transition(source, target, actor, comment=comment)

    application._status = target.value
    application.status_changed_at = datetime.now(UTC)
    db.session.add(
        AuditEvent(
            application_id=application.id,
            from_status=source.value,
            to_status=target.value,
            actor=actor.value,
            actor_user_id=actor_user.id if actor_user else None,
            reason=reason,
            comment=comment.strip() if comment else None,
        )
    )
    db.session.add(status_notification(application, target, notification_body))
    db.session.flush()

    log.info(
        "application status changed",
        extra={
            "application_id": application.id,
            "from_status": source.value,
            "to_status": target.value,
            "actor": actor.value,
            "reason": reason,
        },
    )
    return TransitionResult(application, source, changed=True)
