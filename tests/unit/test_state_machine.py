"""Машина состояний заявки: спецификация переходов из CLAUDE.md, раздел 7."""

import itertools

import pytest

from app.domain.errors import CommentRequired, InvalidTransition
from app.domain.state_machine import Actor, allowed_targets, check_transition, is_terminal
from app.domain.statuses import Status

S = Status

# Разрешённые переходы и кто их выполняет — дословно из раздела 7
SPEC: dict[tuple[Status, Status], Actor] = {
    (S.DRAFT, S.SUBMITTED): Actor.CLIENT,
    (S.DRAFT, S.CANCELLED): Actor.CLIENT,
    (S.SUBMITTED, S.CHECKING): Actor.SYSTEM,
    (S.CHECKING, S.INFO_REQUESTED): Actor.SYSTEM,
    (S.CHECKING, S.MANUAL_REVIEW): Actor.SYSTEM,
    (S.CHECKING, S.OFFER): Actor.SYSTEM,
    (S.CHECKING, S.REJECTED): Actor.SYSTEM,
    (S.INFO_REQUESTED, S.CHECKING): Actor.CLIENT,
    (S.INFO_REQUESTED, S.CANCELLED): Actor.CLIENT,
    (S.MANUAL_REVIEW, S.OFFER): Actor.ANALYST,
    (S.MANUAL_REVIEW, S.REJECTED): Actor.ANALYST,
    (S.MANUAL_REVIEW, S.INFO_REQUESTED): Actor.ANALYST,
    (S.OFFER, S.ACCEPTED): Actor.CLIENT,
    (S.OFFER, S.DECLINED): Actor.CLIENT,
    (S.ACCEPTED, S.SIGNED): Actor.CLIENT,
    (S.SIGNED, S.ISSUED): Actor.SYSTEM,
}
FORBIDDEN = [
    (source, target)
    for source, target in itertools.product(Status, Status)
    if source != target and (source, target) not in SPEC
]
TERMINAL = {S.ISSUED, S.REJECTED, S.DECLINED, S.CANCELLED}
COMMENT = "Обороты подтверждены выпиской"


def _pair_id(pair: tuple[Status, Status]) -> str:
    return f"{pair[0].value}->{pair[1].value}"


def test_status_codes_match_spec() -> None:
    assert [status.value for status in Status] == [
        "draft",
        "submitted",
        "checking",
        "info_requested",
        "manual_review",
        "offer",
        "accepted",
        "signed",
        "issued",
        "rejected",
        "declined",
        "cancelled",
    ]


@pytest.mark.parametrize(("pair", "actor"), SPEC.items(), ids=[_pair_id(p) for p in SPEC])
def test_allowed_transition(pair: tuple[Status, Status], actor: Actor) -> None:
    source, target = pair
    rule = check_transition(source, target, actor, comment=COMMENT)
    assert (rule.source, rule.target, rule.actor) == (source, target, actor)


@pytest.mark.parametrize(("pair", "actor"), SPEC.items(), ids=[_pair_id(p) for p in SPEC])
def test_allowed_pair_rejects_other_actors(pair: tuple[Status, Status], actor: Actor) -> None:
    for other in Actor:
        if other is not actor:
            with pytest.raises(InvalidTransition):
                check_transition(*pair, other, comment=COMMENT)


@pytest.mark.parametrize("pair", FORBIDDEN, ids=[_pair_id(p) for p in FORBIDDEN])
def test_forbidden_transition_raises(pair: tuple[Status, Status]) -> None:
    for actor in Actor:
        with pytest.raises(InvalidTransition):
            check_transition(*pair, actor, comment=COMMENT)


@pytest.mark.parametrize("target", [S.OFFER, S.REJECTED, S.INFO_REQUESTED])
@pytest.mark.parametrize("comment", [None, "", "   "])
def test_analyst_decision_requires_comment(target: Status, comment: str | None) -> None:
    with pytest.raises(CommentRequired):
        check_transition(S.MANUAL_REVIEW, target, Actor.ANALYST, comment=comment)


def test_client_and_system_transitions_do_not_require_comment() -> None:
    check_transition(S.DRAFT, S.SUBMITTED, Actor.CLIENT)
    check_transition(S.CHECKING, S.OFFER, Actor.SYSTEM)


def test_terminal_statuses_have_no_exits() -> None:
    for status in Status:
        assert is_terminal(status) == (status in TERMINAL)
        if status in TERMINAL:
            assert allowed_targets(status) == set()


def test_allowed_targets_by_actor() -> None:
    assert allowed_targets(S.CHECKING, Actor.SYSTEM) == {
        S.INFO_REQUESTED,
        S.MANUAL_REVIEW,
        S.OFFER,
        S.REJECTED,
    }
    assert allowed_targets(S.CHECKING, Actor.CLIENT) == set()
    assert allowed_targets(S.DRAFT) == {S.SUBMITTED, S.CANCELLED}


def test_invalid_transition_maps_to_http_409() -> None:
    with pytest.raises(InvalidTransition) as error:
        check_transition(S.ISSUED, S.DRAFT, Actor.CLIENT)
    assert error.value.status == 409
    assert error.value.code == "invalid_transition"
    assert "issued" in error.value.message


def test_missing_comment_maps_to_http_422() -> None:
    with pytest.raises(CommentRequired) as error:
        check_transition(S.MANUAL_REVIEW, S.OFFER, Actor.ANALYST)
    assert error.value.status == 422
    assert error.value.code == "comment_required"
