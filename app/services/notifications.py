"""Уведомления в продукте: тексты по статусам заявки и центр уведомлений.

Email, SMS и мессенджеры не используются: уведомления видны только в интерфейсе.
"""

from sqlalchemy import func, select

from app.domain.errors import AccessDenied, NotFound
from app.domain.statuses import Status
from app.extensions import db
from app.models import Application, Notification, User

S = Status
NOTIFICATIONS_LIMIT = 100

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


def list_for_user(user: User) -> tuple[list[Notification], int]:
    items = list(
        db.session.scalars(
            select(Notification)
            .where(Notification.user_id == user.id)
            .order_by(Notification.id.desc())
            .limit(NOTIFICATIONS_LIMIT)
        )
    )
    unread = db.session.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user.id, Notification.is_read.is_(False))
    )
    return items, int(unread or 0)


def mark_read(user: User, notification_id: int) -> Notification:
    notification = db.session.get(Notification, notification_id)
    if notification is None:
        raise NotFound("Уведомление не найдено")
    if notification.user_id != user.id:
        raise AccessDenied("Это уведомление другого пользователя")
    notification.is_read = True
    db.session.commit()
    return notification
