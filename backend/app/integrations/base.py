from __future__ import annotations

from typing import Any

import httpx

from app.core.logging import sanitize_payload


class ExternalProviderError(RuntimeError):
    def __init__(self, message: str, *, category: str = "provider_unavailable", status_code: int | None = None):
        super().__init__(message)
        self.category = category
        self.status_code = status_code


def classify_http_error(response: httpx.Response, provider: str) -> ExternalProviderError:
    if response.status_code in {401, 403}:
        return ExternalProviderError(f"O IDP não conseguiu autenticar na conta {provider}.", category="authentication_error", status_code=response.status_code)
    if response.status_code == 404:
        return ExternalProviderError(f"Recurso não encontrado no {provider}.", category="not_found", status_code=404)
    if response.status_code == 429:
        return ExternalProviderError(f"Limite de requisições do {provider} excedido.", category="provider_unavailable", status_code=429)
    if response.status_code >= 500:
        return ExternalProviderError(f"O provedor {provider} está temporariamente indisponível.", category="provider_unavailable", status_code=response.status_code)
    return ExternalProviderError(f"Falha ao consultar {provider}.", category="error", status_code=response.status_code)


def safe_json(response: httpx.Response) -> dict[str, Any] | list[Any]:
    try:
        payload = response.json()
    except ValueError:
        return {"message": "Resposta não JSON recebida do provedor."}
    return sanitize_payload(payload)
