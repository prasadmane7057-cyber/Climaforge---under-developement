"""Cryptographic refresh token generation, hashing, atomic rotation, and revocation service."""

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets
from typing import Tuple
import uuid

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.config import Settings, settings as global_settings
from app.models.token import RefreshToken
from app.security.exceptions import (
    InvalidRefreshTokenError,
    RefreshTokenError,
    TokenExpiredRefreshError,
    TokenReusedError,
    TokenRevokedError,
)


def generate_raw_token() -> str:
    """Generate a high-entropy, cryptographically random opaque token (256 bits)."""
    return secrets.token_urlsafe(32)


def hash_refresh_token(raw_token: str, pepper: str) -> str:
    """Compute a deterministic, keyed HMAC-SHA256 digest of a raw refresh token using pepper."""
    if not raw_token or not isinstance(raw_token, str):
        raise InvalidRefreshTokenError("Raw refresh token must be a non-empty string")
    if not pepper or len(pepper.encode("utf-8")) < 32:
        raise ValueError("Refresh token pepper is missing or shorter than 32 bytes")

    return hmac.new(
        pepper.encode("utf-8"),
        raw_token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


class RefreshTokenService:
    """Service managing refresh token generation, secure storage, rotation, and revocation."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or global_settings

    @property
    def pepper(self) -> str:
        pepper_val = self._settings.refresh_token_pepper
        if not pepper_val or len(pepper_val.encode("utf-8")) < 32:
            raise ValueError("Refresh token pepper is missing or shorter than 32 bytes")
        return pepper_val

    @property
    def expiry_days(self) -> int:
        return self._settings.refresh_token_days

    def create_refresh_token(
        self,
        session: Session,
        user_id: str,
        family_id: str | None = None,
    ) -> Tuple[str, RefreshToken]:
        """Issue a new refresh token for a user.

        Returns a tuple of (raw_token, token_record). Only the hash is persisted.
        """
        if not user_id or not str(user_id).strip():
            raise ValueError("user_id must be a non-empty string")

        raw_token = generate_raw_token()
        token_hash = hash_refresh_token(raw_token, self.pepper)

        token_family = family_id or str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=self.expiry_days)

        token_record = RefreshToken(
            id=str(uuid.uuid4()),
            user_id=str(user_id),
            family_id=token_family,
            token_hash=token_hash,
            expires_at=expires_at,
            created_at=now,
            revoked=False,
            revoked_at=None,
        )

        session.add(token_record)
        session.flush()

        return raw_token, token_record

    def rotate_refresh_token(
        self,
        session: Session,
        raw_token: str,
    ) -> Tuple[str, RefreshToken]:
        """Atomically rotate a refresh token, issuing a replacement and revoking the prior token.

        Replay Detection:
        If a token that was already revoked is replayed, the entire token family/session
        is immediately revoked to protect against session hijacking.

        Concurrency Protection:
        Atomic state transition prevents concurrent requests from double-rotating the same token.
        """
        token_hash = hash_refresh_token(raw_token, self.pepper)

        try:
            # 1. Fetch current token state
            token = session.execute(
                select(RefreshToken).where(RefreshToken.token_hash == token_hash)
            ).scalar_one_or_none()

            if token is None:
                raise InvalidRefreshTokenError("Refresh token not found or invalid")

            now = datetime.now(timezone.utc)

            # 2. Check for replay attack (reuse of an already revoked token)
            if token.revoked:
                # Compromised session: Revoke all remaining active tokens in this family
                session.execute(
                    update(RefreshToken)
                    .where(
                        RefreshToken.family_id == token.family_id,
                        RefreshToken.revoked.is_(False),
                    )
                    .values(revoked=True, revoked_at=now)
                )
                session.commit()
                raise TokenReusedError(
                    "Refresh token reuse detected; entire token family has been revoked"
                )

            # 3. Check for expired token
            if token.expires_at < now:
                token.revoked = True
                token.revoked_at = now
                session.commit()
                raise TokenExpiredRefreshError("Refresh token has expired")

            # 4. Atomic rotation check: conditional update ensures no other thread consumed it
            result = session.execute(
                update(RefreshToken)
                .where(
                    RefreshToken.id == token.id,
                    RefreshToken.revoked.is_(False),
                )
                .values(revoked=True, revoked_at=now)
            )

            if result.rowcount == 0:
                # Race condition: another concurrent request already rotated this token
                session.execute(
                    update(RefreshToken)
                    .where(
                        RefreshToken.family_id == token.family_id,
                        RefreshToken.revoked.is_(False),
                    )
                    .values(revoked=True, revoked_at=now)
                )
                session.commit()
                raise TokenReusedError("Concurrent rotation conflict; token already consumed")

            # 5. Issue new token in the same session family
            new_raw_token, new_token = self.create_refresh_token(
                session=session,
                user_id=token.user_id,
                family_id=token.family_id,
            )

            session.commit()
            return new_raw_token, new_token

        except (
            InvalidRefreshTokenError,
            TokenReusedError,
            TokenExpiredRefreshError,
            TokenRevokedError,
        ):
            # Re-raise known domain exceptions directly
            raise
        except Exception as exc:
            session.rollback()
            raise RefreshTokenError("Failed to rotate refresh token transactionally") from exc

    def revoke_refresh_token(self, session: Session, raw_token: str) -> bool:
        """Revoke a single refresh token by its raw representation."""
        token_hash = hash_refresh_token(raw_token, self.pepper)
        now = datetime.now(timezone.utc)

        result = session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked.is_(False),
            )
            .values(revoked=True, revoked_at=now)
        )
        session.commit()
        return result.rowcount > 0

    def revoke_session(self, session: Session, family_id: str) -> int:
        """Revoke all tokens associated with a session family (e.g., logout from device)."""
        now = datetime.now(timezone.utc)
        result = session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.family_id == family_id,
                RefreshToken.revoked.is_(False),
            )
            .values(revoked=True, revoked_at=now)
        )
        session.commit()
        return int(result.rowcount)

    def revoke_all_user_tokens(self, session: Session, user_id: str) -> int:
        """Revoke all active refresh tokens for a user (e.g., global logout or password reset)."""
        now = datetime.now(timezone.utc)
        result = session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked.is_(False),
            )
            .values(revoked=True, revoked_at=now)
        )
        session.commit()
        return int(result.rowcount)


# Default service instance
refresh_token_service = RefreshTokenService()

