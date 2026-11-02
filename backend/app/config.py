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

    # CORS origins allowed for frontend requests
    cors_origins: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # Advisory AI Layer configuration (strictly advisory, never authoritative)
    nugen_enabled: bool = False
    nugen_mock_mode: bool = True
    nugen_api_key: str = ""

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
