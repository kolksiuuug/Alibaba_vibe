"""Поля анкеты и цели кредита с подписями для клиента."""

# Цели кредита: код -> подпись
PURPOSES = {
    "working_capital": "пополнение оборотных средств",
    "equipment": "покупка оборудования или техники",
    "cash_gap": "кассовый разрыв",
    "expansion": "развитие бизнеса",
}

# Общие поля, без которых заявку нельзя отправить
BASE_REQUIRED_FIELDS = ("contact_name", "purpose_description")
COLLATERAL_FIELDS = ("collateral_description", "collateral_value")
GUARANTEE_FIELDS = ("guarantor_full_name", "guarantor_inn")
NUMERIC_FIELDS = frozenset({"collateral_value"})

FIELD_LABELS = {
    "contact_name": "контактное лицо по заявке",
    "purpose_description": "на что пойдут деньги",
    "collateral_description": "описание залога (что это, марка, год выпуска)",
    "collateral_value": "оценочная стоимость залога, ₽",
    "equipment_supplier": "поставщик оборудования",
    "guarantor_full_name": "ФИО поручителя",
    "guarantor_inn": "ИНН поручителя",
    "comment": "комментарий",
}
ALLOWED_FORM_FIELDS = frozenset(FIELD_LABELS)


def field_label(code: str) -> str:
    return FIELD_LABELS.get(code, code)
