import pytest

from apps.backend.core.config import ConfigurationError, load_settings

PRODUCTION_ENV = {
    "APP_ENV": "production",
    "DATABASE_URL": "postgres://user:secret@db.internal:5432/skillbridge",
    "JWT_SECRET": "x" * 48,
    "ALLOWED_ORIGINS": "https://app.example.com",
    "BACKEND_URL": "https://api.example.com",
    "PORT": "6000",
}


def test_production_settings_are_normalised():
    settings = load_settings(PRODUCTION_ENV)
    assert settings.database_url == "postgresql+psycopg://user:secret@db.internal:5432/skillbridge"
    assert settings.database_backend == "postgresql"
    assert settings.allowed_origins == ("https://app.example.com",)
    assert settings.port == 6000 and settings.production and settings.jwt_secret_configured
    assert settings.public_url == "https://api.example.com"


def test_development_defaults():
    local = load_settings({})
    assert local.environment == "development" and local.database_backend == "sqlite"
    assert local.jwt_secret is None and local.public_url is None and not local.production


@pytest.mark.parametrize("environment", [
    {**PRODUCTION_ENV, "DATABASE_URL": "sqlite:///./skillbridge.db"},
    {**PRODUCTION_ENV, "JWT_SECRET": "change-this-secret-in-production"},
    {**PRODUCTION_ENV, "JWT_SECRET": "too-short"},
    {**PRODUCTION_ENV, "ALLOWED_ORIGINS": "http://app.example.com"},
    {**PRODUCTION_ENV, "ALLOWED_ORIGINS": "https://app.example.com/api"},
    {**PRODUCTION_ENV, "BACKEND_URL": "api.example.com"},
    {**PRODUCTION_ENV, "BACKEND_URL": "http://api.example.com"},
    {"DATABASE_URL": "mysql://user@host/db"},
    {"ACCESS_TOKEN_MINUTES": "0"},
    {"PORT": "70000"},
    {"APP_ENV": "staging"},
    {"LOG_LEVEL": "LOUD"},
])
def test_invalid_configuration_is_rejected(environment):
    with pytest.raises(ConfigurationError):
        load_settings(environment)
