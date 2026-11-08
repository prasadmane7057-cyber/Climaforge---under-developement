"""Authentication Pydantic schemas for CLIMAFORGE M16A.4."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, field_validator


class LoginRequest(BaseModel):
    """Credentials submitted to the login endpoint.

    Passwords are never logged, stored in plaintext, or echoed in responses.
    """

    email: Annotated[str, Field(min_length=1, max_length=320)]
    password: Annotated[str, Field(min_length=1, max_length=1024)]

    @field_validator("email", mode="before")
    @classmethod
    def normalise_email(cls, v: str) -> str:
        """Lowercase and strip whitespace to prevent duplicate lookups."""
        if isinstance(v, str):
            return v.strip().lower()
        return v


class TokenResponse(BaseModel):
    """Access-token response returned from login and refresh endpoints.

    Refresh tokens are NEVER included in this payload — they are set
    exclusively via HttpOnly cookies.
    """

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Remaining token lifetime in seconds")


class CurrentUserResponse(BaseModel):
    """Public profile of the authenticated user.

    Internal fields (hashed_password, is_superuser, refresh_tokens) are
    intentionally excluded.
    """

    id: str
    email: str
    full_name: str | None
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ErrorResponse(BaseModel):
    """Generic error envelope returned for auth failures."""

    detail: str

