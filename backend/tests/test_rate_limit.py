from app.core.rate_limit import InMemoryRateLimiter


def test_rate_limiter_blocks_after_limit():
    limiter = InMemoryRateLimiter(2)
    assert limiter.allow("client") is True
    assert limiter.allow("client") is True
    assert limiter.allow("client") is False


def test_rate_limiter_isolated_per_client():
    limiter = InMemoryRateLimiter(1)
    assert limiter.allow("client-a") is True
    assert limiter.allow("client-b") is True
