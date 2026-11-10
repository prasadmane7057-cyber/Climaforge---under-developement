"""Application configuration module using pydantic-settings."""

from typing import List, Literal, Union

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


class Settings(BaseSettings):
    """Configuration settings for the CLIMAFORGE backend."""

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "CLIMAFORGE Backend"
    version: str = "0.1.0"
    environment: str = "development"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug_field(cls, v: object) -> bool:
        if isinstance(v, str):
            lower = v.strip().lower()
            if lower in {"1", "true", "yes", "on", "enable", "enabled", "debug"}:
                return True
            if lower in {"0", "false", "no", "off", "disable", "disabled", "release", "prod", "production"}:
                return False
        return bool(v)

    # CORS origins allowed for frontend requests
    cors_origins: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # Advisory AI Layer & Nugen AI Conversational Assistant
    nugen_enabled: bool = False
    nugen_mock_mode: bool = True
    nugen_provider: str = "mock"
    nugen_api_key: str = ""
    nugen_api_url: str = "https://api.nugen.in/api/v3/inference/chat/completions"
    nugen_endpoint: str = "https://api.nugen.in/api/v3/inference/chat/completions"
    nugen_model: str = "Qwen/Qwen2.5-0.5B-Instruct"
    nugen_max_tokens: int = 500
    nugen_temperature: float = 0.1
    nugen_stream: bool = True
    nugen_timeout_seconds: float = 25.0
    chatbot_provider: str = "none"
    chatbot_api_key: str = ""
    chatbot_endpoint: str = ""
    chatbot_model: str = ""
    chatbot_timeout_seconds: float = 25.0

    # Real-Time Environmental Intelligence & IMD Configuration
    open_meteo_base_url: str = "https://api.open-meteo.com/v1"
    open_meteo_timeout_seconds: float = 10.0
    weather_cache_ttl_seconds: int = 600
    imd_enabled: bool = False
    imd_api_base_url: str = "https://api.imd.gov.in/public"
    imd_api_key: str = ""
    imd_timeout_seconds: float = 10.0

    auth_mode: Literal["strict"] = "strict"
    jwt_signing_key: str | None = None
    jwt_algorithm: Literal["HS256"] = "HS256"
    jwt_issuer: str | None = None
    jwt_audience: str | None = None
    access_token_minutes: int = Field(default=15, gt=0)
    refresh_token_days: int = Field(default=7, gt=0)
    refresh_token_pepper: str | None = None
    database_url: str | None = None

    @field_validator("cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return [str(item) for item in v]
        return ["http://localhost:5173", "http://127.0.0.1:5173"]

    @property
    def effective_nugen_url(self) -> str:
        return self.nugen_api_url or self.nugen_endpoint or "https://api.nugen.in/api/v3/inference/chat/completions"

    @property
    def is_nugen_configured(self) -> bool:
        key = (self.nugen_api_key or self.chatbot_api_key or "").strip()
        return bool(
            self.nugen_enabled
            and not self.nugen_mock_mode
            and key
            and not key.lower().startswith("replace")
            and not key.lower().startswith("your")
        )

    def validate_auth_configuration(self) -> None:
        """Validate all settings required before strict authentication can run."""
        required_values = {
            "JWT_SIGNING_KEY": self.jwt_signing_key,
            "JWT_ISSUER": self.jwt_issuer,
            "JWT_AUDIENCE": self.jwt_audience,
            "REFRESH_TOKEN_PEPPER": self.refresh_token_pepper,
            "DATABASE_URL": self.database_url,
        }
        missing = [
            name for name, value in required_values.items()
            if value is None or not value.strip()
        ]
        if missing:
            raise ValueError(
                f"Strict authentication requires configuration: {', '.join(missing)}"
            )

        assert self.jwt_signing_key is not None
        assert self.refresh_token_pepper is not None
        for name, value in (
            ("JWT_SIGNING_KEY", self.jwt_signing_key),
            ("REFRESH_TOKEN_PEPPER", self.refresh_token_pepper),
        ):
            if (
                len(value.encode("utf-8")) < 32
                or value != value.strip()
                or value.lower().startswith(("replace-", "change-me", "your-"))
            ):
                raise ValueError(
                    f"{name} must be a non-placeholder value of at least 32 bytes "
                    "with no surrounding whitespace"
                )

        if self.jwt_signing_key == self.refresh_token_pepper:
            raise ValueError(
                "JWT_SIGNING_KEY and REFRESH_TOKEN_PEPPER must be different values"
            )

        for name, value in (
            ("JWT_ISSUER", self.jwt_issuer),
            ("JWT_AUDIENCE", self.jwt_audience),
        ):
            if value is None or value != value.strip():
                raise ValueError(f"{name} must not contain surrounding whitespace")

        if self.access_token_minutes <= 0:
            raise ValueError("ACCESS_TOKEN_MINUTES must be greater than zero")
        if self.refresh_token_days <= 0:
            raise ValueError("REFRESH_TOKEN_DAYS must be greater than zero")

        try:
            database_url = make_url(self.database_url or "")
        except ArgumentError as error:
            raise ValueError("DATABASE_URL must be a valid SQLAlchemy URL") from error

        if database_url.drivername not in {"sqlite", "postgresql+psycopg"}:
            raise ValueError(
                "DATABASE_URL must use sqlite or postgresql+psycopg"
            )


settings = Settings()
