"""Генератор синтетических компаний для проверки на своих данных.

    python seed/generate.py --n 50 --seed 42 [--out seed/generated_companies.json]
    docker compose run --rm app flask seed --generate 50 --gen-seed 42   # сразу в БД

Формат совпадает с seed/demo_companies.json. Все данные вымышленные: Faker ru_RU для ФИО,
названия компаний — случайные сочетания слов, ИНН и ОГРН с несуществующим кодом региона 00.
Для этих ИНН моки отвечают детерминированно по хешу, поэтому исходы получаются разными.
"""

import argparse
import json
import random
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from faker import Faker

TODAY = date(2026, 10, 1)
OKVEDS = [
    ("10.71", "Производство хлеба и мучных кондитерских изделий недлительного хранения"),
    ("25.62", "Обработка металлических изделий механическая"),
    ("46.90", "Торговля оптовая неспециализированная"),
    ("47.11", "Торговля розничная преимущественно пищевыми продуктами"),
    ("49.41", "Деятельность автомобильного грузового транспорта"),
    ("56.10", "Деятельность ресторанов и услуги по доставке продуктов питания"),
    ("62.01", "Разработка компьютерного программного обеспечения"),
    ("41.20", "Строительство жилых и нежилых зданий"),
]
REGIONS = [
    "Тверская область",
    "Нижегородская область",
    "Свердловская область",
    "Краснодарский край",
    "Новосибирская область",
    "Республика Татарстан",
    "Самарская область",
    "Пермский край",
]
MONTHS = [f"{year}-{month:02d}" for year, month in [(2025, 10), (2025, 11), (2025, 12)]] + [
    f"2026-{month:02d}" for month in range(1, 10)
]


def _inn(rng: random.Random, kind: str) -> str:
    """ИНН с корректными контрольными цифрами и кодом региона 00."""
    if kind == "llc":
        digits = [0, 0] + [rng.randint(0, 9) for _ in range(7)]
        weights = [2, 4, 10, 3, 5, 9, 4, 6, 8]
        digits.append(sum(d * w for d, w in zip(digits, weights, strict=True)) % 11 % 10)
    else:
        digits = [0, 0] + [rng.randint(0, 9) for _ in range(8)]
        w11 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
        digits.append(sum(d * w for d, w in zip(digits, w11, strict=True)) % 11 % 10)
        w12 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
        digits.append(sum(d * w for d, w in zip(digits, w12, strict=True)) % 11 % 10)
    return "".join(map(str, digits))


def _ogrn(rng: random.Random, kind: str, registered: date) -> str:
    year = f"{registered.year % 100:02d}"
    if kind == "llc":
        body = "1" + year + "00" + "".join(str(rng.randint(0, 9)) for _ in range(7))
        return body + str(int(body) % 11 % 10)
    body = "3" + year + "00" + "".join(str(rng.randint(0, 9)) for _ in range(9))
    return body + str(int(body) % 13 % 10)


def _turnover(rng: random.Random) -> list[dict[str, Any]]:
    base = rng.choice([400_000, 800_000, 1_500_000, 2_500_000, 4_000_000, 7_000_000])
    volatility = rng.choice([0.03, 0.08, 0.15, 0.3, 0.45])
    return [
        {"month": month, "amount": int(base * max(0.2, rng.gauss(1, volatility))) // 1000 * 1000}
        for month in MONTHS
    ]


def generate_companies(n: int, seed: int) -> list[dict[str, Any]]:
    fake = Faker("ru_RU")
    fake.seed_instance(seed)
    rng = random.Random(seed)
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    while len(items) < n:
        kind = "ip" if rng.random() < 0.3 else "llc"
        inn = _inn(rng, kind)
        if inn in seen:
            continue
        seen.add(inn)
        person = fake.name()
        words = [w.capitalize() for w in fake.words(nb=2)]
        name = f"ИП {person}" if kind == "ip" else f"ООО «{'-'.join(words)}»"
        registered = TODAY - timedelta(days=rng.randint(120, 15 * 365))
        okved, okved_name = rng.choice(OKVEDS)
        index = len(items) + 1
        items.append(
            {
                "login": f"gen-{seed}-{index:03d}",
                "display_name": person,
                "demo_hint": f"Сгенерированный профиль (seed {seed})",
                "company": {
                    "name": name,
                    "kind": kind,
                    "inn": inn,
                    "ogrn": _ogrn(rng, kind, registered),
                    "okved": okved,
                    "okved_name": okved_name,
                    "registered_at": registered.isoformat(),
                    "region": rng.choice(REGIONS),
                    "director_name": person,
                    "monthly_turnover": _turnover(rng),
                },
            }
        )
    return items


def main() -> None:
    parser = argparse.ArgumentParser(description="Синтетические компании для кредитного кабинета")
    parser.add_argument("--n", type=int, default=50, help="сколько компаний сгенерировать")
    parser.add_argument(
        "--seed", type=int, default=42, help="seed: одинаковый seed — одинаковые данные"
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).with_name("generated_companies.json"),
        help="куда записать JSON",
    )
    args = parser.parse_args()
    items = generate_companies(args.n, args.seed)
    args.out.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"generated {len(items)} companies -> {args.out}")


if __name__ == "__main__":
    main()
