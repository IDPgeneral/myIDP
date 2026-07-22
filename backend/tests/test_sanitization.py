from app.core.logging import sanitize_payload


def test_external_response_is_sanitized():
    payload = {"token": "abc", "nested": {"Authorization": "Bearer secret", "safe": "ok"}, "connection_string": "postgresql://u:p@db/x"}
    sanitized = sanitize_payload(payload)
    assert sanitized["token"] == "[REDACTED]"
    assert sanitized["nested"]["Authorization"] == "[REDACTED]"
    assert sanitized["nested"]["safe"] == "ok"
    assert sanitized["connection_string"] == "[REDACTED]"


def test_log_text_secrets_are_sanitized():
    payload = {
        "message": "API_KEY=abc123 PASSWORD: hunter2 rnd_abcdefghijklmnop eyJabcdefghijk.abcdefghijkl.abcdefghijkl",
    }
    sanitized = sanitize_payload(payload)
    assert sanitized["message"] == "API_KEY=[REDACTED] PASSWORD: [REDACTED] [REDACTED_TOKEN] [REDACTED_JWT]"


def test_pem_blocks_are_sanitized():
    value = "before\n-----BEGIN PRIVATE KEY-----\nsecret\n-----END PRIVATE KEY-----\nafter"
    assert sanitize_payload(value) == "before\n[REDACTED_PEM]\nafter"
