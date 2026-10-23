"""Уведомления в продукте: тексты по статусам заявки. Email и SMS не используются."""

from app.domain.statuses import Status
from app.models import Application, Notification

S = Status

# Заголовок и текст уведомления клиенту при переходе в статус; {id} — номер заявки
STATUS_MESSAGES: dict[Status, tuple[str, str]] = {
    S.SUBMITTED: (
        "Заявка отправлена",
        "Заявка №{id} получена. Сейчас начнётся автоматическая проверка.",
    ),
    S.CHECKING: (
        "Идёт проверка",
        "Проверяем данные компании, налоги и кредитную историю по заявке №{id}. "
        "Обычно это занимает меньше минуты.",
    ),
    S.INFO_REQUESTED: (
        "Нужна информация",
        "По заявке №{id} банку не хватает данных. Откройте заявку и ответьте на запрос.",
    ),
    S.MANUAL_REVIEW: (
        "Заявку смотрит аналитик",
        "Заявка №{id} передана кредитному аналитику. Сообщим, когда будет решение.",
    ),
    S.OFFER: (
        "Готово предложение",
        "По заявке №{id} готово предложение. Посмотрите условия и примите решение.",
    ),
    S.ACCEPTED: (
        "Предложение принято",
        "Осталось подписать договор по заявке №{id} кодом в кабинете.",
    ),
    S.SIGNED: (
        "Договор подписан",
        "Договор по заявке №{id} подписан. Готовим выдачу денег.",
    ),
    S.ISSUED: (
        "Кредит выдан",
        "Деньги по заявке №{id} зачислены на расчётный счёт (симуляция).",
    ),
    S.REJECTED: (
        "Отказ по заявке",
        "К сожалению, банк не может выдать кредит по заявке №{id}. Причины — в карточке заявки.",
    ),
    S.DECLINED: (
        "Предложение отклонено",
        "Вы отказались от предложения по заявке №{id}. Можно подать новую заявку.",
    ),
    S.CANCELLED: (
        "Заявка отменена",
        "Заявка №{id} отменена. Новую заявку можно подать в любой момент.",
    ),
}


def status_notification(
    application: Application, target: Status, body: str | None = None
) -> Notification:
    title, template = STATUS_MESSAGES[target]
    return Notification(
        user_id=application.created_by_id,
        application_id=application.id,
        kind="status_changed",
        title=title,
        body=body or template.format(id=application.id),
    )
