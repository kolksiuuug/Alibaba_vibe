"""Моки внешних систем: БКИ, ЕГРЮЛ/ЕГРИП, ФНС «Прозрачный бизнес», ЭП, АБС.

Все ответы синтетические. Реальные внешние системы не вызываются.
"""

from flask import Flask

app = Flask(__name__)
app.json.ensure_ascii = False  # type: ignore[attr-defined]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
