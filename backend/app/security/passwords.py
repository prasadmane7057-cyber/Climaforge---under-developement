"""Argon2id password hashing and verification service."""

from typing import Any

from argon2 import PasswordHasher, Type
from argon2.exceptions import (
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)

from app.security.exceptions import InvalidPasswordError


class PasswordService:
    """Service providing Argon2id password hashing and constant-time verification.

    Conforms to RFC 9106 recommended parameters:
    - Type: Argon2id (hybrid data-dependent / data-independent memory access)
    - Memory cost: 65,536 KiB (64 MiB)
    - Time cost: 3 iterations
    - Parallelism: 4 lanes
    - Hash length: 32 bytes
    - Salt length: 16 bytes
    """

    def __init__(
        self,
        time_cost: int = 3,
        memory_cost: int = 65536,
        parallelism: int = 4,
        hash_len: int = 32,
        salt_len: int = 16,
    ) -> None:
        self._hasher = PasswordHasher(
            time_cost=time_cost,
            memory_cost=memory_cost,
            parallelism=parallelism,
            hash_len=hash_len,
            salt_len=salt_len,
            type=Type.ID,
        )

    def hash_password(self, password: str) -> str:
        """Hash a plaintext password with Argon2id and a cryptographically random salt.

        Never logs or stores the input password.
        """
        if not isinstance(password, str) or not password:
            raise InvalidPasswordError("Password must be a non-empty string")
        return self._hasher.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plaintext password against an Argon2 hash.

        Safely catches mismatch or malformed hash exceptions without leaking details.
        """
        if not isinstance(plain_password, str) or not plain_password:
            return False
        if not isinstance(hashed_password, str) or not hashed_password:
            return False

        try:
            return self._hasher.verify(hashed_password, plain_password)
        except VerifyMismatchError:
            return False
        except (InvalidHashError, VerificationError):
            return False
        except Exception:
            # Shield against unexpected corruption
            return False

    def needs_rehash(self, hashed_password: str) -> bool:
        """Check whether the hash was produced with older or weaker hasher parameters."""
        if not isinstance(hashed_password, str) or not hashed_password:
            return True
        try:
            return self._hasher.check_needs_rehash(hashed_password)
        except Exception:
            return True


# Default service instance
password_service = PasswordService()

