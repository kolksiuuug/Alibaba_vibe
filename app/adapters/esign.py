"""Электронная подпись (мок): подпись документа кодом из интерфейса. Симуляция."""

from app.adapters.base import JsonDict
from app.adapters.http import JsonHttpClient


class HttpEsignAdapter:
    def __init__(self, http: JsonHttpClient) -> None:
        self._http = http

    def sign(self, *, application_id: int, document_hash: str, signer: str) -> JsonDict:
        payload = {
            "application_id": application_id,
            "document_hash": document_hash,
            "signer": signer,
        }
        return self._http.request("POST", "/esign/sign", json=payload)
