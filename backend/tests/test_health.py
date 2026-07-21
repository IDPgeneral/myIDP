from unittest.mock import patch

import httpx

from app.db.models import HealthCheck, Product
from app.services.health import HealthCheckService


def create_check(db):
    product = Product(name="MILU", slug="milu", owner="owner", status="unknown")
    db.add(product)
    db.flush()
    check = HealthCheck(product_id=product.id, name="backend", url="https://health.example.com/status", method="GET", expected_status=200, timeout_seconds=2, active=True)
    db.add(check)
    db.commit()
    db.refresh(check)
    return check


@patch("app.services.health.validate_health_url", return_value=None)
@patch("app.services.health.httpx.request")
def test_health_success(request_mock, _, db):
    request_mock.return_value = httpx.Response(200, request=httpx.Request("GET", "https://health.example.com/status"))
    result = HealthCheckService(db).run(create_check(db))
    assert result.status == "healthy"
    assert result.http_status == 200


@patch("app.services.health.validate_health_url", return_value=None)
@patch("app.services.health.httpx.request", side_effect=httpx.ReadTimeout("timeout"))
def test_health_timeout(_, __, db):
    result = HealthCheckService(db).run(create_check(db))
    assert result.status == "down"
    assert "tempo limite" in result.message.lower()
