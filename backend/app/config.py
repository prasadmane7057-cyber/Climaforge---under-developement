"""Application configuration module using pydantic-settings."""

from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration settings for the CLIMAFORGE backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
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


settings = Settings()
