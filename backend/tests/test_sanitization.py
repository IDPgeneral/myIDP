from app.core.logging import sanitize_payload


def test_external_response_is_sanitized():
    payload = {"token": "abc", "nested": {"Authorization": "Bearer secret", "safe": "ok"}, "connection_string": "postgresql://u:p@db/x"}
    sanitized = sanitize_payload(payload)
    assert sanitized["token"] == "[REDACTED]"
    assert sanitized["nested"]["Authorization"] == "[REDACTED]"
    assert sanitized["nested"]["safe"] == "ok"
    assert sanitized["connection_string"] == "[REDACTED]"
