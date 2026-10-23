"""Статусы заявки. Коды одинаковые в БД, API, UI и документации; русские подписи — только в UI."""

from enum import StrEnum


class Status(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    CHECKING = "checking"
    INFO_REQUESTED = "info_requested"
    MANUAL_REVIEW = "manual_review"
    OFFER = "offer"
    ACCEPTED = "accepted"
    SIGNED = "signed"
    ISSUED = "issued"
    REJECTED = "rejected"
    DECLINED = "declined"
    CANCELLED = "cancelled"


TERMINAL_STATUSES = frozenset({Status.ISSUED, Status.REJECTED, Status.DECLINED, Status.CANCELLED})
