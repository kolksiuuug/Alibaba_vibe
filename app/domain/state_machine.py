"""Единственный источник разрешённых переходов статуса заявки (CLAUDE.md, раздел 7)."""

from dataclasses import dataclass
from enum import StrEnum

from app.domain.errors import CommentRequired, InvalidTransition
from app.domain.statuses import TERMINAL_STATUSES, Status


class Actor(StrEnum):
    CLIENT = "client"
    ANALYST = "analyst"
    SYSTEM = "system"


@dataclass(frozen=True)
class Transition:
    source: Status
    target: Status
    actor: Actor
    requires_comment: bool = False


S = Status
TRANSITIONS: tuple[Transition, ...] = (
    Transition(S.DRAFT, S.SUBMITTED, Actor.CLIENT),
    Transition(S.DRAFT, S.CANCELLED, Actor.CLIENT),
    Transition(S.SUBMITTED, S.CHECKING, Actor.SYSTEM),
    Transition(S.CHECKING, S.INFO_REQUESTED, Actor.SYSTEM),
    Transition(S.CHECKING, S.MANUAL_REVIEW, Actor.SYSTEM),
    Transition(S.CHECKING, S.OFFER, Actor.SYSTEM),
    Transition(S.CHECKING, S.REJECTED, Actor.SYSTEM),
    # Клиент ответил на дозапрос — заявка снова уходит на проверку
    Transition(S.INFO_REQUESTED, S.CHECKING, Actor.CLIENT),
    Transition(S.INFO_REQUESTED, S.CANCELLED, Actor.CLIENT),
    Transition(S.MANUAL_REVIEW, S.OFFER, Actor.ANALYST, requires_comment=True),
    Transition(S.MANUAL_REVIEW, S.REJECTED, Actor.ANALYST, requires_comment=True),
    Transition(S.MANUAL_REVIEW, S.INFO_REQUESTED, Actor.ANALYST, requires_comment=True),
    Transition(S.OFFER, S.ACCEPTED, Actor.CLIENT),
    Transition(S.OFFER, S.DECLINED, Actor.CLIENT),
    # Подпись кодом в интерфейсе (симуляция ЭП)
    Transition(S.ACCEPTED, S.SIGNED, Actor.CLIENT),
    # Выдача через мок АБС, задача воркера
    Transition(S.SIGNED, S.ISSUED, Actor.SYSTEM),
)

_BY_PAIR = {(rule.source, rule.target): rule for rule in TRANSITIONS}


def is_terminal(status: Status) -> bool:
    return status in TERMINAL_STATUSES


def allowed_targets(source: Status, actor: Actor | None = None) -> set[Status]:
    return {
        rule.target
        for rule in TRANSITIONS
        if rule.source is source and (actor is None or rule.actor is actor)
    }


def check_transition(
    source: Status,
    target: Status,
    actor: Actor,
    *,
    comment: str | None = None,
) -> Transition:
    """Вернуть правило перехода или поднять доменную ошибку (409 / 422)."""
    rule = _BY_PAIR.get((source, target))
    if rule is None or rule.actor is not actor:
        raise InvalidTransition(
            f"Переход {source.value} -> {target.value} недоступен для {actor.value}"
        )
    if rule.requires_comment and not (comment and comment.strip()):
        raise CommentRequired("Для решения по заявке нужен комментарий")
    return rule
