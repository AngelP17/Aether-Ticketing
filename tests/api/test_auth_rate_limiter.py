import fakeredis

from apps.api.services.auth_service import (
    LOGIN_RATE_LIMIT_ATTEMPTS,
    RedisLoginRateLimiter,
)


def test_redis_limiter_records_failures_and_limits() -> None:
    client = fakeredis.FakeRedis(decode_responses=True)
    limiter = RedisLoginRateLimiter(client)

    assert not limiter.is_limited("admin", "127.0.0.1")

    for _ in range(LOGIN_RATE_LIMIT_ATTEMPTS - 1):
        limiter.record_failure("admin", "127.0.0.1")
        assert not limiter.is_limited("admin", "127.0.0.1")

    limiter.record_failure("admin", "127.0.0.1")
    assert limiter.is_limited("admin", "127.0.0.1")


def test_redis_limiter_separates_clients() -> None:
    client = fakeredis.FakeRedis(decode_responses=True)
    limiter = RedisLoginRateLimiter(client)

    for _ in range(LOGIN_RATE_LIMIT_ATTEMPTS):
        limiter.record_failure("admin", "10.0.0.1")

    assert limiter.is_limited("admin", "10.0.0.1")
    assert not limiter.is_limited("admin", "10.0.0.2")
    assert not limiter.is_limited("admin", "10.0.0.3")


def test_redis_limiter_reset_clears_counter() -> None:
    client = fakeredis.FakeRedis(decode_responses=True)
    limiter = RedisLoginRateLimiter(client)

    for _ in range(LOGIN_RATE_LIMIT_ATTEMPTS):
        limiter.record_failure("admin", "10.0.0.1")

    assert limiter.is_limited("admin", "10.0.0.1")

    limiter.reset("admin", "10.0.0.1")

    assert not limiter.is_limited("admin", "10.0.0.1")


def test_redis_limiter_normalizes_username_case() -> None:
    client = fakeredis.FakeRedis(decode_responses=True)
    limiter = RedisLoginRateLimiter(client)

    for _ in range(LOGIN_RATE_LIMIT_ATTEMPTS):
        limiter.record_failure("Admin", "10.0.0.1")

    assert limiter.is_limited("admin", "10.0.0.1")
    assert limiter.is_limited("ADMIN", "10.0.0.1")


def test_redis_limiter_clear_removes_all_keys() -> None:
    client = fakeredis.FakeRedis(decode_responses=True)
    limiter = RedisLoginRateLimiter(client)

    limiter.record_failure("admin", "10.0.0.1")
    limiter.record_failure("viewer", "10.0.0.2")
    limiter.clear()

    assert not limiter.is_limited("admin", "10.0.0.1")
    assert not limiter.is_limited("viewer", "10.0.0.2")


def test_build_limiter_returns_redis_when_configured(monkeypatch) -> None:
    from apps.api.services import auth_service

    fake = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(auth_service.settings, "RATE_LIMIT_BACKEND", "redis")
    monkeypatch.setattr(auth_service.settings, "REDIS_URL", "redis://localhost:6379/0")

    def fake_from_url(url: str, decode_responses: bool = True):
        assert url == "redis://localhost:6379/0"
        return fake

    monkeypatch.setattr(auth_service.redis, "Redis", type("R", (), {"from_url": staticmethod(fake_from_url)}))

    limiter = auth_service.build_login_rate_limiter()

    assert isinstance(limiter, RedisLoginRateLimiter)


def test_build_limiter_falls_back_when_redis_unreachable(monkeypatch) -> None:
    from apps.api.services import auth_service

    monkeypatch.setattr(auth_service.settings, "RATE_LIMIT_BACKEND", "redis")
    monkeypatch.setattr(auth_service.settings, "REDIS_URL", "redis://localhost:6379/0")

    class BrokenRedis:
        def ping(self) -> None:
            raise auth_service.redis.ConnectionError("nope")

    def fake_from_url(url: str, decode_responses: bool = True):
        return BrokenRedis()

    monkeypatch.setattr(auth_service.redis, "Redis", type("R", (), {"from_url": staticmethod(fake_from_url)}))

    limiter = auth_service.build_login_rate_limiter()

    assert isinstance(limiter, auth_service.InMemoryLoginRateLimiter)


def test_build_limiter_falls_back_when_redis_url_missing(monkeypatch) -> None:
    from apps.api.services import auth_service

    monkeypatch.setattr(auth_service.settings, "RATE_LIMIT_BACKEND", "redis")
    monkeypatch.setattr(auth_service.settings, "REDIS_URL", None)

    limiter = auth_service.build_login_rate_limiter()

    assert isinstance(limiter, auth_service.InMemoryLoginRateLimiter)
