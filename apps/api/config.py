from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

env_file = Path(__file__).parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(env_file) if env_file.exists() else None,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    DATABASE_URL: str = "postgresql://user:password@localhost/aether"
    SECRET_KEY: str = "change-me-in-production"
    ENV: str = "development"
    DEBUG: bool = True
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    AUTO_INIT_DB: bool = False
    USERS_FILE: str | None = None
    RATE_LIMIT_BACKEND: str = "memory"
    REDIS_URL: str | None = None
    ADMIN_BOOTSTRAP_PASSWORD: str | None = None
    DEMO_MODE: bool = False
    DEMO_VIEWER_USERNAME: str = "viewer"
    DEMO_VIEWER_PASSWORD: str = "viewer123"
    DEMO_PORTAL_SUBMIT_ENABLED: bool = False
    DEMO_RESET_DATA_ON_START: bool = False

    # Phase 8: email (outbound + inbound config; creds external, no defaults for secrets)
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM: str = "aether@ops.local"
    SMTP_USE_TLS: bool = True
    # Inbound email (for ticket creation; IMAP or webhook receiver stub)
    IMAP_HOST: str | None = None
    IMAP_USER: str | None = None
    IMAP_PASSWORD: str | None = None
    IMAP_MAILBOX: str = "INBOX"

    # WS / realtime (future scale with redis)
    WS_ENABLED: bool = True

    # Webhooks (signing etc)
    WEBHOOK_TIMEOUT_SEC: int = 10
    # Service tokens for OSS integrations (comma sep, zero cost)
    SERVICE_TOKENS: str = ""

    @property
    def is_production(self) -> bool:
        return self.ENV == "production"


settings = Settings()


def validate_production_settings() -> None:
    if not settings.is_production:
        return

    if settings.SECRET_KEY == "change-me-in-production":
        raise RuntimeError("SECRET_KEY must be set to a deployment-specific value in production")

    if settings.DEBUG:
        raise RuntimeError("DEBUG must be false in production")

    if settings.DEMO_MODE and not settings.ADMIN_BOOTSTRAP_PASSWORD:
        raise RuntimeError("ADMIN_BOOTSTRAP_PASSWORD must be set for production demo mode")

    allowed_origins = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",")]
    if "*" in allowed_origins:
        raise RuntimeError("ALLOWED_ORIGINS cannot include '*' in production when credentials are enabled")
