"""Подбор продуктов, предварительные условия и калькулятор платежей."""

from decimal import Decimal
from typing import Any

from sqlalchemy import select

from app.domain.errors import ValidationFailed
from app.domain.form_fields import field_label
from app.domain.loan_math import annuity_payment, payment_schedule
from app.extensions import db
from app.models import Product
from app.scoring.decision_engine import required_product_fields
from app.scoring.metrics import money
from app.scoring.types import ProductTerms

MAX_RECOMMENDATIONS = 3


def base_rate(product: Product, key_rate: Decimal) -> Decimal:
    """Ставка «от»: ключевая + спред продукта, без надбавки за риск."""
    return (Decimal(key_rate) + Decimal(str(product.rate_spread))).quantize(Decimal("0.01"))


def product_view(product: Product, key_rate: Decimal) -> dict[str, Any]:
    return {
        "code": product.code,
        "name": product.name,
        "description": product.description,
        "purposes": product.purposes,
        "min_amount": product.min_amount,
        "max_amount": product.max_amount,
        "min_term_months": product.min_term_months,
        "max_term_months": product.max_term_months,
        "rate_spread": product.rate_spread,
        "base_rate": base_rate(product, key_rate),
        "requires_collateral": product.requires_collateral,
        "requires_guarantee": product.requires_guarantee,
        "required_fields": [
            {"code": code, "label": field_label(code)}
            for code in required_product_fields(ProductTerms.from_model(product))
        ],
    }


def active_products() -> list[Product]:
    return list(
        db.session.scalars(
            select(Product).where(Product.is_active.is_(True)).order_by(Product.rate_spread)
        )
    )


def get_product(code: str) -> Product:
    product = db.session.scalars(
        select(Product).where(Product.code == code, Product.is_active.is_(True))
    ).first()
    if product is None:
        raise ValidationFailed(
            "Такого продукта нет", errors={"product_code": ["Выберите продукт из списка"]}
        )
    return product


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(value, high))


def recommend(
    purpose: str, amount: int, term_months: int, *, key_rate: Decimal
) -> list[dict[str, Any]]:
    """1–3 продукта под цель, сумму и срок с предварительной ставкой и платежом."""
    products = active_products()
    pool = [p for p in products if purpose in p.purposes] or products
    results = []
    for product in pool:
        fit_amount = _clamp(amount, product.min_amount, product.max_amount)
        fit_term = _clamp(term_months, product.min_term_months, product.max_term_months)
        notes = []
        if fit_amount != amount:
            notes.append(
                f"Сумма по продукту — от {money(product.min_amount)} "
                f"до {money(product.max_amount)} ₽, показан расчёт на {money(fit_amount)} ₽."
            )
        if fit_term != term_months:
            notes.append(
                f"Срок по продукту — от {product.min_term_months} до {product.max_term_months} "
                f"мес., показан расчёт на {fit_term} мес."
            )
        if product.requires_collateral:
            notes.append("Нужен залог: подойдёт приобретаемое оборудование.")
        if product.requires_guarantee:
            notes.append("Нужно поручительство собственника бизнеса.")
        rate = base_rate(product, key_rate)
        results.append(
            {
                "product": product_view(product, key_rate),
                "amount": fit_amount,
                "term_months": fit_term,
                "rate": rate,
                "monthly_payment": annuity_payment(fit_amount, fit_term, rate),
                "fits": fit_amount == amount and fit_term == term_months,
                "notes": notes,
            }
        )
    results.sort(key=lambda item: (not item["fits"], item["rate"]))
    return results[:MAX_RECOMMENDATIONS]


def calculate_for(
    amount: int,
    term_months: int,
    *,
    key_rate: Decimal,
    annual_rate: float | None = None,
    product_code: str | None = None,
) -> dict[str, Any]:
    """Калькулятор: явная ставка или ставка «от» выбранного продукта."""
    if annual_rate is not None:
        rate = Decimal(str(annual_rate))
    elif product_code:
        rate = base_rate(get_product(product_code), key_rate)
    else:
        raise ValidationFailed(
            "Укажите ставку или продукт", errors={"annual_rate": ["Нужна ставка или product_code"]}
        )
    return calculate(amount, term_months, rate)


def calculate(amount: int, term_months: int, annual_rate: Decimal) -> dict[str, Any]:
    schedule = payment_schedule(amount, term_months, annual_rate)
    total = sum((row.payment for row in schedule), Decimal(0))
    return {
        "amount": amount,
        "term_months": term_months,
        "annual_rate": annual_rate,
        "monthly_payment": schedule[0].payment,
        "total_payment": total,
        "overpayment": total - amount,
        "schedule": schedule,
    }
