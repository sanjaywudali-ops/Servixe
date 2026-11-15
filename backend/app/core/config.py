from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "development"  # development | staging | production | test
    app_name: str = "Servixe API"
    api_prefix: str = "/api/v1"

    database_url: str = "postgresql+psycopg://servixe:servixe@localhost:5432/servixe"
    redis_url: str = "redis://localhost:6379/0"

    # Secrets: load from a managed secret store in staging/production. Never commit them.
    secret_key: str = "change-me-in-env"
    payment_webhook_secret: str = "change-me-payment-webhook"
    whatsapp_webhook_secret: str = "change-me-whatsapp-webhook"
    whatsapp_verify_token: str = "change-me"

    # Sessions
    session_cookie_name: str = "sx_session"
    cookie_secure: bool = False  # True in staging/production (HTTPS only)
    cookie_samesite: str = "lax"
    session_ttl_hours_default: int = 24 * 7
    session_ttl_hours_staff: int = 8
    session_idle_minutes_default: int = 60 * 24
    session_idle_minutes_staff: int = 120
    max_failed_logins: int = 5
    lockout_minutes: int = 15
    require_email_verification: bool = False

    # CORS / frontend
    frontend_url: str = "http://localhost:3000"
    cors_origins: list[str] = ["http://localhost:3000"]

    # Storage (private S3). storage_backend=local is for development/tests only.
    storage_backend: str = "local"  # local | s3
    local_storage_dir: str = "./.storage"
    s3_bucket: str = "servixe-private"
    s3_region: str = "ap-south-1"
    s3_endpoint_url: str | None = None
    signed_url_ttl_seconds: int = 120
    upload_max_bytes: int = 8 * 1024 * 1024
    evidence_retention_days: int = 365
    allowed_upload_types: list[str] = ["image/jpeg", "image/png", "image/webp", "application/pdf"]

    # Integrations (all behind service modules so vendors can be swapped)
    email_backend: str = "console"  # console | ses
    email_from: str = "Servixe <no-reply@servixe.example>"
    ses_region: str = "ap-south-1"
    whatsapp_backend: str = "console"  # console | cloud_api
    whatsapp_phone_number_id: str = ""
    whatsapp_access_token: str = ""
    payment_gateway: str = "stub"  # stub | <your gateway adapter>
    turnstile_secret: str = ""  # empty => captcha check skipped (dev only)
    maps_api_key: str = ""

    # Async
    celery_eager: bool = True  # run notification tasks inline (dev/tests). False in production.
    rate_limit_enabled: bool = True

    sentry_dsn: str = ""

    # Support contact shown in notifications / emergency copy
    emergency_notice: str = (
        "Servixe is a non-emergency coordination service. In an emergency, "
        "contact your local emergency services immediately (India: 112)."
    )

    @property
    def is_production(self) -> bool:
        return self.env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
