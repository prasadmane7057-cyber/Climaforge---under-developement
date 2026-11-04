"""Tests for strict authentication configuration validation."""

import pytest

from app.config import Settings


def valid_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "auth_mode": "strict",
        "jwt_signing_key": "a" * 32,
        "jwt_algorithm": "HS256",
        "jwt_issuer": "climaforge-test",
        "jwt_audience": "climaforge-api-test",
        "access_token_minutes": 15,
        "refresh_token_days": 7,
        "refresh_token_pepper": "b" * 32,
        "database_url": "sqlite:///./test.db",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_valid_strict_auth_configuration():
    settings = valid_settings()

    settings.validate_auth_configuration()

    assert settings.auth_mode == "strict"
    assert settings.access_token_minutes == 15
    assert settings.refresh_token_days == 7


def test_missing_secrets_fail_strict_configuration():
    settings = Settings(_env_file=None)

    with pytest.raises(ValueError, match="JWT_SIGNING_KEY"):
        settings.validate_auth_configuration()


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"jwt_signing_key": "short"}, "JWT_SIGNING_KEY"),
        ({"refresh_token_pepper": "replace-with-a-placeholder-value-that-is-long-enough"}, "REFRESH_TOKEN_PEPPER"),
        ({"refresh_token_pepper": "a" * 32}, "must be different values"),
        ({"access_token_minutes": 0}, "greater than 0"),
        ({"refresh_token_days": -1}, "greater than 0"),
        ({"jwt_issuer": " "}, "JWT_ISSUER"),
        ({"database_url": "not a database URL"}, "DATABASE_URL"),
        ({"database_url": "mysql://user:pass@localhost/db"}, "must use sqlite"),
        ({"auth_mode": "demo"}, "auth_mode"),
    ],
)
def test_invalid_auth_configuration_fails(overrides: dict[str, object], message: str):
    with pytest.raises(ValueError, match=message):
        settings = valid_settings(**overrides)
        settings.validate_auth_configuration()


@pytest.mark.asyncio
async def test_strict_configuration_failure_aborts_application_startup(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main, "settings", Settings(_env_file=None))

    with pytest.raises(ValueError, match="Strict authentication requires configuration"):
        async with main.app.router.lifespan_context(main.app):
            pytest.fail("Application lifespan started without strict auth configuration")
