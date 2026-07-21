from __future__ import annotations

import ipaddress
import socket
import time
from urllib.parse import urlparse

import httpx
from sqlalchemy.orm import Session

from app.core.logging import sanitized_error
from app.db.models import HealthCheck, HealthCheckResult


class UnsafeHealthUrl(ValueError):
    pass


def validate_health_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise UnsafeHealthUrl("URL de health check inválida.")
    hostname = parsed.hostname.lower()
    if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(".local"):
        raise UnsafeHealthUrl("Host local não permitido para health check.")
    try:
        addresses = {info[4][0] for info in socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == "https" else 80))}
    except socket.gaierror as exc:
        raise UnsafeHealthUrl("Não foi possível resolver o host do health check.") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise UnsafeHealthUrl("Endereço privado ou reservado não permitido no health check.")


class HealthCheckService:
    def __init__(self, db: Session):
        self.db = db

    def run(self, check: HealthCheck) -> HealthCheckResult:
        started = time.perf_counter()
        http_status: int | None = None
        response_time_ms: int | None = None
        try:
            validate_health_url(check.url)
            response = httpx.request(
                check.method,
                check.url,
                timeout=httpx.Timeout(check.timeout_seconds),
                follow_redirects=False,
                headers={"User-Agent": "internal-developer-portal-health/1.0"},
            )
            http_status = response.status_code
            response_time_ms = int((time.perf_counter() - started) * 1000)
            if response.status_code == check.expected_status:
                result_status = "healthy"
                message = f"{response.status_code} OK"
            elif 200 <= response.status_code < 500:
                result_status = "degraded"
                message = f"Status HTTP inesperado: {response.status_code}"
            else:
                result_status = "down"
                message = f"Serviço respondeu com HTTP {response.status_code}"
        except httpx.TimeoutException:
            response_time_ms = int((time.perf_counter() - started) * 1000)
            result_status = "down"
            message = "Health check excedeu o tempo limite."
        except (httpx.RequestError, UnsafeHealthUrl) as exc:
            response_time_ms = int((time.perf_counter() - started) * 1000)
            result_status = "down" if isinstance(exc, httpx.RequestError) else "unknown"
            message = sanitized_error(exc)

        result = HealthCheckResult(
            health_check_id=check.id,
            status=result_status,
            http_status=http_status,
            response_time_ms=response_time_ms,
            message=message,
        )
        self.db.add(result)
        self.db.commit()
        self.db.refresh(result)
        return result
