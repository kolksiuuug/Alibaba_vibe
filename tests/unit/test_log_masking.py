import json
import logging

from app.log import FIO_MASK, JsonFormatter, mask_pii


def test_masks_inn_ogrn_and_phone() -> None:
    masked = mask_pii("ИНН 0044385397, ОГРНИП 320005509044282, тел. +7 (916) 123-45-67")
    assert "0044385397" not in masked
    assert "00******97" in masked
    assert "320005509044282" not in masked
    assert "916" not in masked
    assert masked.endswith("+7*******67")


def test_masks_full_name_and_initials() -> None:
    masked = mask_pii("Директор Ершов Глеб Аркадьевич, контакт Лаврова М. О.")
    assert "Ершов" not in masked
    assert "Лаврова" not in masked
    assert masked.count(FIO_MASK) == 2


def test_keeps_regular_text() -> None:
    text = "Заявка 42 переведена в статус checking"
    assert mask_pii(text) == text


def test_formatter_hides_sensitive_extra_fields() -> None:
    record = logging.makeLogRecord(
        {"msg": "login", "levelname": "INFO", "inn": "0044385397", "path": "/x/0044385397"}
    )
    payload = json.loads(JsonFormatter().format(record))
    assert payload["inn"] == "***"
    assert "0044385397" not in payload["path"]
    assert payload["msg"] == "login"
