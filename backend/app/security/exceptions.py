"""Security and authentication exception hierarchy."""


class SecurityError(Exception):
    """Base exception for all security and authentication failures."""


class PasswordError(SecurityError):
    """Base exception for password hashing or verification errors."""


class InvalidPasswordError(PasswordError):
    """Raised when password validation or formatting fails."""


class JWTError(SecurityError):
    """Base exception for JWT access token encoding/decoding errors."""


class TokenExpiredError(JWTError):
    """Raised when a JWT access token has passed its expiration time."""


class InvalidTokenError(JWTError):
    """Raised when a JWT access token is invalid, malformed, or has invalid claims."""


class RefreshTokenError(SecurityError):
    """Base exception for refresh token operations."""


class InvalidRefreshTokenError(RefreshTokenError):
    """Raised when a refresh token is unknown, not found, or malformed."""


class TokenExpiredRefreshError(RefreshTokenError):
    """Raised when a refresh token has expired."""


class TokenRevokedError(RefreshTokenError):
    """Raised when an operation is attempted on an already revoked refresh token."""


class TokenReusedError(RefreshTokenError):
    """Raised when a previously rotated/revoked refresh token is re-submitted (replay attack)."""

