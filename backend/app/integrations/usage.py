from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Literal

MetricStatus = Literal["ok", "warning", "critical", "unknown"]


def metric_status(value: float | None, limit: float | None) -> MetricStatus:
    if value is None or limit is None or limit <= 0:
        return "unknown"
    percentage = value / limit * 100
    if percentage >= 90:
        return "critical"
    if percentage >= 75:
        return "warning"
    return "ok"


def usage_metric(
    key: str,
    label: str,
    *,
    value: float | None,
    limit: float | None,
    unit: str,
    scope: str = "resource",
    period: str = "current",
    source: str = "provider_api",
    description: str | None = None,
) -> dict[str, Any]:
    percentage = round(value / limit * 100, 1) if value is not None and limit is not None and limit > 0 else None
    return {
        "key": key,
        "label": label,
        "value": value,
        "limit": limit,
        "unit": unit,
        "percentage": percentage,
        "status": metric_status(value, limit),
        "scope": scope,
        "period": period,
        "source": source,
        "description": description,
    }


def overall_usage_status(metrics: Iterable[dict[str, Any]]) -> MetricStatus:
    statuses = {str(metric.get("status")) for metric in metrics}
    if "critical" in statuses:
        return "critical"
    if "warning" in statuses:
        return "warning"
    if "ok" in statuses:
        return "ok"
    return "unknown"


def series_value(payload: dict[str, Any] | list[Any], *, aggregation: Literal["latest", "max", "sum"] = "max") -> tuple[float | None, str]:
    series = payload if isinstance(payload, list) else payload.get("data", [])
    if not isinstance(series, list):
        return None, ""
    values: list[tuple[str, float]] = []
    unit = ""
    for item in series:
        if not isinstance(item, dict):
            continue
        unit = str(item.get("unit") or unit)
        points = item.get("values", [])
        if not isinstance(points, list):
            continue
        for point in points:
            if not isinstance(point, dict):
                continue
            raw = point.get("value")
            if isinstance(raw, int | float) and not isinstance(raw, bool):
                values.append((str(point.get("timestamp") or ""), float(raw)))
    if not values:
        return None, unit
    if aggregation == "sum":
        return sum(value for _, value in values), unit
    if aggregation == "latest":
        return max(values, key=lambda item: item[0])[1], unit
    return max(value for _, value in values), unit


def find_number(payload: Any, candidate_keys: Iterable[str]) -> float | None:
    candidates = {key.lower() for key in candidate_keys}
    if isinstance(payload, dict):
        for key, value in payload.items():
            if str(key).lower() in candidates:
                if isinstance(value, int | float) and not isinstance(value, bool):
                    return float(value)
                if isinstance(value, str):
                    try:
                        return float(value)
                    except ValueError:
                        pass
        for value in payload.values():
            result = find_number(value, candidates)
            if result is not None:
                return result
    elif isinstance(payload, list):
        for value in payload:
            result = find_number(value, candidates)
            if result is not None:
                return result
    return None
