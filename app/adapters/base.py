"""Интерфейсы адаптеров к внешним системам и общая ошибка недоступности.

В проверяемой версии все реализации ходят только в контейнер mocks (CLAUDE.md, раздел 1.3).
"""

from dataclasses import dataclass
from typing import Any, Protocol

JsonDict = dict[str, Any]


class AdapterError(Exception):
    """Внешняя система недоступна или ответила ошибкой после всех ретраев."""

    def __init__(self, source: str, message: str) -> None:
        super().__init__(f"{source}: {message}")
        self.source = source
        self.message = message


class BkiAdapter(Protocol):
    def get_report(self, inn: str) -> JsonDict: ...


class EgrulAdapter(Protocol):
    def get_company(self, inn: str) -> JsonDict: ...


class FnsAdapter(Protocol):
    def get_transparent_business(self, inn: str) -> JsonDict: ...


class AbsAdapter(Protocol):
    def create_disbursement(
        self, *, idempotency_key: str, application_id: int, inn: str, amount: int
    ) -> JsonDict: ...


class EsignAdapter(Protocol):
    def sign(self, *, application_id: int, document_hash: str, signer: str) -> JsonDict: ...


@dataclass(frozen=True)
class Adapters:
    bki: BkiAdapter
    egrul: EgrulAdapter
    fns: FnsAdapter
    abs: AbsAdapter
    esign: EsignAdapter
