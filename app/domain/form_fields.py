"""Поля анкеты, которые продукт может требовать дополнительно, и их подписи для клиента."""

COLLATERAL_FIELDS = ("collateral_description", "collateral_value")
GUARANTEE_FIELDS = ("guarantor_full_name", "guarantor_inn")

FIELD_LABELS = {
    "collateral_description": "описание залога (что это, марка, год выпуска)",
    "collateral_value": "оценочная стоимость залога, ₽",
    "equipment_supplier": "поставщик оборудования",
    "guarantor_full_name": "ФИО поручителя",
    "guarantor_inn": "ИНН поручителя",
}
