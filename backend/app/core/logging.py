from __future__ import annotations

import json
import logging
import re
import uuid
from collections.abc import Callable
from contextvars import ContextVar
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")

SENSITIVE_KEY_PATTERN = re.compile(
    r"(authorization|token|secret|password|private[_-]?key|api[_-]?key|connection[_-]?string|cookie)",
    re.IGNORECASE,
)


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s correlation_id=%(correlation_id)s %(message)s",
    )
    old_factory = logging.getLogRecordFactory()

    def factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
        record = old_factory(*args, **kwargs)
        record.correlation_id = correlation_id_var.get() or "-"
        return record

    logging.setLogRecordFactory(factory)


def sanitize_payload(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            if SENSITIVE_KEY_PATTERN.search(str(key)):
                sanitized[str(key)] = "[REDACTED]"
            else:
                sanitized[str(key)] = sanitize_payload(item)
        return sanitized
    if isinstance(value, list):
        return [sanitize_payload(item) for item in value]
    if isinstance(value, tuple):
        return tuple(sanitize_payload(item) for item in value)
    if isinstance(value, str):
        value = re.sub(
            r"-----BEGIN [A-Z0-9 ]*(?:PRIVATE KEY|CERTIFICATE)-----.*?-----END [A-Z0-9 ]*(?:PRIVATE KEY|CERTIFICATE)-----",
            "[REDACTED_PEM]",
            value,
            flags=re.I | re.S,
        )
        value = re.sub(r"Bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer [REDACTED]", value, flags=re.I)
        value = re.sub(r"(postgres(?:ql)?://)[^@\s]+@", r"\1[REDACTED]@", value, flags=re.I)
        value = re.sub(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b", "[REDACTED_JWT]", value)
        value = re.sub(r"\b(?:rnd|gh[opsu]|github_pat)_[A-Za-z0-9_\-]{12,}\b", "[REDACTED_TOKEN]", value, flags=re.I)
        value = re.sub(
            r"(?i)\b(api[_-]?key|access[_-]?token|auth[_-]?token|secret|password|private[_-]?key|database[_-]?url)\b(\s*[:=]\s*)([^\s,;]+)",
            r"\1\2[REDACTED]",
            value,
        )
    return value


def sanitized_error(exc: Exception) -> str:
    text = str(exc).strip() or exc.__class__.__name__
    return str(sanitize_payload(text))[:500]


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Any]) -> Response:
        incoming = request.headers.get("x-correlation-id", "").strip()
        correlation_id = incoming[:100] if incoming else str(uuid.uuid4())
        token = correlation_id_var.set(correlation_id)
        try:
            response = await call_next(request)
            response.headers["x-correlation-id"] = correlation_id
            return response
        finally:
            correlation_id_var.reset(token)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            {
                "timestamp": self.formatTime(record),
                "level": record.levelname,
                "logger": record.name,
                "message": sanitize_payload(record.getMessage()),
                "correlation_id": getattr(record, "correlation_id", "-"),
            },
            ensure_ascii=False,
        )
