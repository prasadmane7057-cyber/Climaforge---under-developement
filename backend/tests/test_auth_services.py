"""Comprehensive unit and integration tests for M16A.3 Authentication Core Services."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import time
import uuid

import jwt
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.base import Base
from app.db.session import create_db_engine, get_session_factory
from app.models.token import RefreshToken
from app.models.user import User
from app.security import (
    InvalidPasswordError,
    InvalidRefreshTokenError,
    InvalidTokenError,
    JWTService,
    PasswordService,
    RefreshTokenService,
    TokenExpiredError,
    TokenExpiredRefreshError,
    TokenPayload,
    TokenReusedError,
    TokenRevokedError,
    generate_raw_token,
    hash_refresh_token,
)


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    """Fixture providing isolated, synthetic test settings."""
    db_file = tmp_path / f"auth_test_{uuid.uuid4().hex}.db"
    return Settings(
        _env_file=None,
        auth_mode="strict",
        jwt_signing_key="k" * 32,
        jwt_algorithm="HS256",
        jwt_issuer="climaforge-test-issuer",
        jwt_audience="climaforge-test-audience",
        access_token_minutes=10,
        refresh_token_days=5,
        refresh_token_pepper="p" * 32,
        database_url=f"sqlite:///{db_file.as_posix()}",
    )


@pytest.fixture
def test_db_session(test_settings: Settings):
    """Fixture providing an isolated transactional database session."""
    engine = create_db_engine(test_settings.database_url)
    Base.metadata.create_all(bind=engine)
    session_factory = get_session_factory(engine)

    with session_factory() as session:
        yield session

    engine.dispose()


@pytest.fixture
def sample_user(test_db_session: Session) -> User:
    """Fixture providing a persisted test user."""
    user = User(
        email=f"operator-{uuid.uuid4().hex[:6]}@climaforge.test",
        hashed_password="hashed_pw_placeholder",
        role="operator",
    )
    test_db_session.add(user)
    test_db_session.commit()
    test_db_session.refresh(user)
    return user


# ============================================================================
# 1. PASSWORD SERVICE TESTS
# ============================================================================

class TestPasswordService:
    """Tests for Argon2id password hashing and verification."""

    def test_correct_password_verification(self):
        service = PasswordService()
        hashed = service.hash_password("SuperSecretPassword123!")

        assert hashed.startswith("$argon2id$")
        assert service.verify_password("SuperSecretPassword123!", hashed) is True

    def test_incorrect_password_verification(self):
        service = PasswordService()
        hashed = service.hash_password("SuperSecretPassword123!")

        assert service.verify_password("WrongPassword!", hashed) is False

    def test_password_hash_uniqueness_with_salt(self):
        service = PasswordService()
        password = "IdenticalPasswordUsedTwice"
        hash1 = service.hash_password(password)
        hash2 = service.hash_password(password)

        assert hash1 != hash2
        assert service.verify_password(password, hash1) is True
        assert service.verify_password(password, hash2) is True

    def test_malformed_hash_safe_handling(self):
        service = PasswordService()

        # Malformed strings should safely return False without uncaught exceptions
        assert service.verify_password("password", "not-a-valid-argon2-hash") is False
        assert service.verify_password("password", "$argon2id$v=19$m=65536$corrupted") is False
        assert service.verify_password("password", "") is False

    def test_empty_password_rejection(self):
        service = PasswordService()

        with pytest.raises(InvalidPasswordError):
            service.hash_password("")

        with pytest.raises(InvalidPasswordError):
            service.hash_password(None)  # type: ignore

        assert service.verify_password("", "$argon2id$somehash") is False

    def test_needs_rehash_detection(self):
        service = PasswordService()
        hashed = service.hash_password("password")

        # Current hash should not need rehash
        assert service.needs_rehash(hashed) is False
        assert service.needs_rehash("corrupted") is True


# ============================================================================
# 2. JWT ACCESS TOKEN SERVICE TESTS
# ============================================================================

class TestJWTService:
    """Tests for JWT access token creation and cryptographic verification."""

    def test_valid_token_roundtrip(self, test_settings: Settings):
        jwt_svc = JWTService(test_settings)
        user_id = str(uuid.uuid4())
        email = "analyst@climaforge.test"
        role = "operator"

        token = jwt_svc.create_access_token(user_id=user_id, email=email, role=role)
        payload = jwt_svc.verify_access_token(token)

        assert isinstance(payload, TokenPayload)
        assert payload.sub == user_id
        assert payload.email == email
        assert payload.role == role
        assert payload.iss == test_settings.jwt_issuer
        assert payload.aud == test_settings.jwt_audience
        assert payload.jti is not None
        assert payload.exp > payload.iat

    def test_expired_token_rejection(self, test_settings: Settings):
        jwt_svc = JWTService(test_settings)
        # Create token with negative expiration lifetime
        expired_token = jwt_svc.create_access_token(
            user_id="user-123",
            email="expired@climaforge.test",
            role="operator",
            expires_delta=timedelta(seconds=-10),
        )

        with pytest.raises(TokenExpiredError, match="Access token has expired"):
            jwt_svc.verify_access_token(expired_token)

    def test_invalid_signature_rejection(self, test_settings: Settings):
        jwt_svc = JWTService(test_settings)
        token = jwt_svc.create_access_token(user_id="user-123", email="user@test.org", role="admin")

        # Create another service with a different signing key
        other_settings = Settings(
            _env_file=None,
            jwt_signing_key="z" * 32,
            jwt_algorithm="HS256",
            jwt_issuer=test_settings.jwt_issuer,
            jwt_audience=test_settings.jwt_audience,
            refresh_token_pepper="p" * 32,
            database_url=test_settings.database_url,
        )
        attacker_svc = JWTService(other_settings)

        with pytest.raises(InvalidTokenError, match="Invalid token or claims"):
            attacker_svc.verify_access_token(token)

    def test_wrong_issuer_rejection(self, test_settings: Settings):
        # Craft token with wrong issuer
        payload = {
            "sub": "user-123",
            "email": "user@test.org",
            "role": "operator",
            "iss": "untrusted-issuer",
            "aud": test_settings.jwt_audience,
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=10)).timestamp()),
            "jti": str(uuid.uuid4()),
        }
        token = jwt.encode(payload, test_settings.jwt_signing_key, algorithm=test_settings.jwt_algorithm)

        jwt_svc = JWTService(test_settings)
        with pytest.raises(InvalidTokenError, match="Invalid token or claims"):
            jwt_svc.verify_access_token(token)

    def test_wrong_audience_rejection(self, test_settings: Settings):
        # Craft token with wrong audience
        payload = {
            "sub": "user-123",
            "email": "user@test.org",
            "role": "operator",
            "iss": test_settings.jwt_issuer,
            "aud": "wrong-audience",
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=10)).timestamp()),
            "jti": str(uuid.uuid4()),
        }
        token = jwt.encode(payload, test_settings.jwt_signing_key, algorithm=test_settings.jwt_algorithm)

        jwt_svc = JWTService(test_settings)
        with pytest.raises(InvalidTokenError, match="Invalid token or claims"):
            jwt_svc.verify_access_token(token)

    def test_missing_required_claim_rejection(self, test_settings: Settings):
        # Payload omitting 'jti'
        payload = {
            "sub": "user-123",
            "iss": test_settings.jwt_issuer,
            "aud": test_settings.jwt_audience,
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=10)).timestamp()),
        }
        token = jwt.encode(payload, test_settings.jwt_signing_key, algorithm=test_settings.jwt_algorithm)

        jwt_svc = JWTService(test_settings)
        with pytest.raises(InvalidTokenError, match="Invalid token or claims"):
            jwt_svc.verify_access_token(token)

    def test_malformed_token_format_rejection(self, test_settings: Settings):
        jwt_svc = JWTService(test_settings)

        with pytest.raises(InvalidTokenError):
            jwt_svc.verify_access_token("this.is.not.a.valid.jwt")

        with pytest.raises(InvalidTokenError):
            jwt_svc.verify_access_token("")

    def test_untrusted_none_algorithm_rejection(self, test_settings: Settings):
        # Attempt 'none' algorithm bypass
        payload = {
            "sub": "user-123",
            "iss": test_settings.jwt_issuer,
            "aud": test_settings.jwt_audience,
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=10)).timestamp()),
            "jti": str(uuid.uuid4()),
        }
        token = jwt.encode(payload, key="", algorithm="none")

        jwt_svc = JWTService(test_settings)
        with pytest.raises(InvalidTokenError):
            jwt_svc.verify_access_token(token)

    def test_extra_claims_preservation(self, test_settings: Settings):
        jwt_svc = JWTService(test_settings)
        token = jwt_svc.create_access_token(
            user_id="user-123",
            email="user@test.org",
            role="analyst",
            extra_claims={"department": "hydrology", "sub": "attacker-override"},
        )
        payload = jwt_svc.verify_access_token(token)
        # Protected claim must NOT be overridden by extra_claims
        assert payload.sub == "user-123"
        # Custom claims preserved
        assert payload.extra_claims.get("department") == "hydrology"

    def test_empty_or_whitespace_claims_rejected(self, test_settings: Settings):
        # Empty subject claim must be rejected
        payload_empty_sub = {
            "sub": "   ",
            "iss": test_settings.jwt_issuer,
            "aud": test_settings.jwt_audience,
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=10)).timestamp()),
            "jti": str(uuid.uuid4()),
        }
        token_empty_sub = jwt.encode(
            payload_empty_sub, test_settings.jwt_signing_key, algorithm=test_settings.jwt_algorithm
        )
        jwt_svc = JWTService(test_settings)
        with pytest.raises(InvalidTokenError, match="Subject claim .* must be a non-empty string"):
            jwt_svc.verify_access_token(token_empty_sub)

        # Empty jti claim must be rejected
        payload_empty_jti = {
            "sub": "valid-user",
            "iss": test_settings.jwt_issuer,
            "aud": test_settings.jwt_audience,
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=10)).timestamp()),
            "jti": "",
        }
        token_empty_jti = jwt.encode(
            payload_empty_jti, test_settings.jwt_signing_key, algorithm=test_settings.jwt_algorithm
        )
        with pytest.raises(InvalidTokenError, match="Token ID claim .* must be a non-empty string"):
            jwt_svc.verify_access_token(token_empty_jti)


# ============================================================================
# 3. REFRESH TOKEN GENERATION, ROTATION, AND REVOCATION TESTS
# ============================================================================

class TestRefreshTokenService:
    """Tests for keyed HMAC digest, atomic rotation, replay detection, and revocation."""

    def test_secure_generation_and_entropy(self):
        token1 = generate_raw_token()
        token2 = generate_raw_token()

        assert token1 != token2
        assert len(token1) >= 40  # 32 urlsafe bytes produce ~43 characters

    def test_hash_determinism_and_keyed_pepper(self):
        pepper1 = "pepper_one_" * 4
        pepper2 = "pepper_two_" * 4
        token = generate_raw_token()

        # Same token + same pepper = same hash
        hash1 = hash_refresh_token(token, pepper1)
        hash2 = hash_refresh_token(token, pepper1)
        assert hash1 == hash2

        # Same token + different pepper = different hash
        hash_diff_pepper = hash_refresh_token(token, pepper2)
        assert hash1 != hash_diff_pepper

        # Different token + same pepper = different hash
        hash_diff_token = hash_refresh_token(generate_raw_token(), pepper1)
        assert hash1 != hash_diff_token

    def test_insufficient_pepper_rejection(self):
        with pytest.raises(ValueError, match="pepper is missing or shorter than 32 bytes"):
            hash_refresh_token("valid_token", "short_pepper")

    def test_create_refresh_token_stores_only_hash(
        self, test_settings: Settings, test_db_session: Session, sample_user: User
    ):
        service = RefreshTokenService(test_settings)
        raw_token, record = service.create_refresh_token(test_db_session, sample_user.id)
        test_db_session.commit()

        # Raw token must NOT equal the database hash
        assert raw_token != record.token_hash
        assert record.revoked is False
        assert record.family_id is not None
        assert record.user_id == sample_user.id

        # Verify query by hash finds the record
        computed_hash = hash_refresh_token(raw_token, test_settings.refresh_token_pepper)
        queried = test_db_session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == computed_hash)
        ).scalar_one()

        assert queried.id == record.id

    def test_rotate_refresh_token_success(
        self, test_settings: Settings, test_db_session: Session, sample_user: User
    ):
        service = RefreshTokenService(test_settings)
        raw_token_1, record_1 = service.create_refresh_token(test_db_session, sample_user.id)
        test_db_session.commit()

        # Rotate token
        raw_token_2, record_2 = service.rotate_refresh_token(test_db_session, raw_token_1)

        # 1. New token must have a new raw value and record ID
        assert raw_token_2 != raw_token_1
        assert record_2.id != record_1.id

        # 2. Both tokens must share the same session family_id
        assert record_2.family_id == record_1.family_id

        # 3. Old token must now be marked revoked
        test_db_session.refresh(record_1)
        assert record_1.revoked is True
        assert record_1.revoked_at is not None

        # 4. New token is active
        assert record_2.revoked is False

    def test_rotate_refresh_token_cross_session_naive_sqlite(
        self, test_settings: Settings, sample_user: User
    ):
        """Ensure SQLite timezone-naive datetime returned from DB does not fail datetime comparison."""
        engine = create_db_engine(test_settings.database_url)
        session_factory = get_session_factory(engine)

        # Issue in session 1
        with session_factory() as s1:
            service = RefreshTokenService(test_settings)
            raw_token, _ = service.create_refresh_token(s1, sample_user.id)
            s1.commit()

        # Rotate in session 2 (database row loaded anew as naive datetime)
        with session_factory() as s2:
            service = RefreshTokenService(test_settings)
            new_raw, new_rec = service.rotate_refresh_token(s2, raw_token)
            assert new_raw is not None
            assert new_rec.revoked is False

        engine.dispose()

    def test_unknown_refresh_token_rejection(
        self, test_settings: Settings, test_db_session: Session
    ):
        service = RefreshTokenService(test_settings)
        with pytest.raises(InvalidRefreshTokenError, match="not found or invalid"):
            service.rotate_refresh_token(test_db_session, "non_existent_raw_token")

    def test_expired_refresh_token_rejection(
        self, test_settings: Settings, test_db_session: Session, sample_user: User
    ):
        service = RefreshTokenService(test_settings)
        raw_token, record = service.create_refresh_token(test_db_session, sample_user.id)

        # Manually expire the token in the past
        record.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        test_db_session.commit()

        with pytest.raises(TokenExpiredRefreshError, match="Refresh token has expired"):
            service.rotate_refresh_token(test_db_session, raw_token)

        # Check it is marked revoked
        test_db_session.refresh(record)
        assert record.revoked is True

    def test_revoked_token_rejection(
        self, test_settings: Settings, test_db_session: Session, sample_user: User
    ):
        """Verify that an explicitly revoked token is rejected and triggers token-family reuse protection."""
        service = RefreshTokenService(test_settings)
        raw_token, record = service.create_refresh_token(test_db_session, sample_user.id)
        test_db_session.commit()

        # Explicitly revoke
        revoked = service.revoke_refresh_token(test_db_session, raw_token)
        assert revoked is True

        # Attempting to rotate revoked token must be rejected with TokenReusedError
        with pytest.raises(TokenReusedError, match="reuse detected; entire token family has been revoked"):
            service.rotate_refresh_token(test_db_session, raw_token)

    def test_validate_refresh_token_lifecycle(
        self, test_settings: Settings, test_db_session: Session, sample_user: User
    ):
        """Verify validate_refresh_token behavior for active, expired, revoked, and unknown tokens."""
        service = RefreshTokenService(test_settings)

        # 1. Unknown token
        with pytest.raises(InvalidRefreshTokenError, match="not found or invalid"):
            service.validate_refresh_token(test_db_session, "non_existent_token_value")

        # 2. Valid active token
        raw_token, rec = service.create_refresh_token(test_db_session, sample_user.id)
        test_db_session.commit()
        validated = service.validate_refresh_token(test_db_session, raw_token)
        assert validated.id == rec.id
        assert validated.revoked is False

        # 3. Revoked token
        service.revoke_refresh_token(test_db_session, raw_token)
        with pytest.raises(TokenRevokedError, match="Refresh token has been revoked"):
            service.validate_refresh_token(test_db_session, raw_token)

        # 4. Expired token
        raw_exp, rec_exp = service.create_refresh_token(test_db_session, sample_user.id)
        rec_exp.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        test_db_session.commit()

        with pytest.raises(TokenExpiredRefreshError, match="Refresh token has expired"):
            service.validate_refresh_token(test_db_session, raw_exp)

    def test_replay_detection_revokes_entire_token_family(
        self, test_settings: Settings, test_db_session: Session, sample_user: User
    ):
        service = RefreshTokenService(test_settings)

        # 1. Issue T1
        raw_t1, rec_t1 = service.create_refresh_token(test_db_session, sample_user.id)
        test_db_session.commit()

        # 2. Legitimate user rotates T1 -> T2
        raw_t2, rec_t2 = service.rotate_refresh_token(test_db_session, raw_t1)

        # 3. Legitimate user rotates T2 -> T3
        raw_t3, rec_t3 = service.rotate_refresh_token(test_db_session, raw_t2)

        test_db_session.refresh(rec_t3)
        assert rec_t3.revoked is False

        # 4. Attacker attempts to replay already-rotated token T1!
        with pytest.raises(TokenReusedError, match="reuse detected; entire token family has been revoked"):
            service.rotate_refresh_token(test_db_session, raw_t1)

        # 5. Verify the entire token family was revoked (including the active T3)
        test_db_session.refresh(rec_t1)
        test_db_session.refresh(rec_t2)
        test_db_session.refresh(rec_t3)

        assert rec_t1.revoked is True
        assert rec_t2.revoked is True
        assert rec_t3.revoked is True  # Active descendant revoked due to replay detection

        # Attempting to use T3 now also fails because it was revoked
        with pytest.raises(TokenReusedError):
            service.rotate_refresh_token(test_db_session, raw_t3)

    def test_replay_detection_does_not_affect_other_sessions(
        self, test_settings: Settings, test_db_session: Session, sample_user: User
    ):
        """Confirm replay detection revokes ONLY the compromised family, preserving separate user sessions."""
        service = RefreshTokenService(test_settings)

        # Session A (e.g. Work laptop)
        raw_a1, rec_a1 = service.create_refresh_token(test_db_session, sample_user.id)
        test_db_session.commit()
        raw_a2, rec_a2 = service.rotate_refresh_token(test_db_session, raw_a1)

        # Session B (e.g. Phone)
        raw_b1, rec_b1 = service.create_refresh_token(test_db_session, sample_user.id)
        test_db_session.commit()
        raw_b2, rec_b2 = service.rotate_refresh_token(test_db_session, raw_b1)

        # Replay old token raw_a1 from Session A
        with pytest.raises(TokenReusedError):
            service.rotate_refresh_token(test_db_session, raw_a1)

        # Session A should be revoked
        test_db_session.refresh(rec_a2)
        assert rec_a2.revoked is True

        # Session B must remain completely intact and active
        test_db_session.refresh(rec_b2)
        assert rec_b2.revoked is False

        # Session B can still rotate normally
        raw_b3, rec_b3 = service.rotate_refresh_token(test_db_session, raw_b2)
        assert raw_b3 is not None
        assert rec_b3.revoked is False

    def test_caller_rollback_after_replay_preserves_revocation(
        self, test_settings: Settings, sample_user: User
    ):
        """Confirm that if a caller catches TokenReusedError and rolls back, DB family revocation is NOT rolled back."""
        engine = create_db_engine(test_settings.database_url)
        session_factory = get_session_factory(engine)

        with session_factory() as session:
            service = RefreshTokenService(test_settings)
            raw_t1, rec_t1 = service.create_refresh_token(session, sample_user.id)
            session.commit()

            raw_t2, rec_t2 = service.rotate_refresh_token(session, raw_t1)
            t2_id = rec_t2.id

            # Attacker replays raw_t1
            try:
                service.rotate_refresh_token(session, raw_t1)
            except TokenReusedError:
                # Simulating external caller doing a rollback on caught exception
                session.rollback()

        # Open completely fresh session to inspect disk state
        with session_factory() as session:
            persisted_t2 = session.get(RefreshToken, t2_id)
            assert persisted_t2 is not None
            # Revocation must remain persistent in the database!
            assert persisted_t2.revoked is True

        engine.dispose()

    def test_session_revocation_cannot_be_bypassed_by_rotation(
        self, test_settings: Settings, test_db_session: Session, sample_user: User
    ):
        """Verify that once a session is revoked, no token in that family can be rotated."""
        service = RefreshTokenService(test_settings)
        raw_token, record = service.create_refresh_token(test_db_session, sample_user.id)
        test_db_session.commit()

        # Revoke entire session
        count = service.revoke_session(test_db_session, record.family_id)
        assert count == 1

        # Attempt to rotate should fail with TokenReusedError
        with pytest.raises(TokenReusedError):
            service.rotate_refresh_token(test_db_session, raw_token)

    def test_revoke_session_validation(self, test_settings: Settings, test_db_session: Session):
        service = RefreshTokenService(test_settings)
        with pytest.raises(ValueError, match="family_id must be a non-empty string"):
            service.revoke_session(test_db_session, "")

        with pytest.raises(ValueError, match="family_id must be a non-empty string"):
            service.revoke_session(test_db_session, "   ")

    def test_revoke_all_user_tokens_validation(self, test_settings: Settings, test_db_session: Session):
        service = RefreshTokenService(test_settings)
        with pytest.raises(ValueError, match="user_id must be a non-empty string"):
            service.revoke_all_user_tokens(test_db_session, "")

        with pytest.raises(ValueError, match="user_id must be a non-empty string"):
            service.revoke_all_user_tokens(test_db_session, "   ")

    def test_concurrent_rotation_protection(
        self, test_settings: Settings, test_db_session: Session, sample_user: User
    ):
        service = RefreshTokenService(test_settings)
        raw_token, _ = service.create_refresh_token(test_db_session, sample_user.id)
        test_db_session.commit()

        # First request succeeds
        new_token_1, rec_1 = service.rotate_refresh_token(test_db_session, raw_token)
        assert new_token_1 is not None

        # Concurrent / duplicate request attempting to rotate the exact same token
        with pytest.raises(TokenReusedError):
            service.rotate_refresh_token(test_db_session, raw_token)

        # Confirm replacement token rec_1 was revoked due to reuse conflict
        test_db_session.refresh(rec_1)
        assert rec_1.revoked is True

    def test_single_token_revocation(
        self, test_settings: Settings, test_db_session: Session, sample_user: User
    ):
        service = RefreshTokenService(test_settings)
        raw_token, record = service.create_refresh_token(test_db_session, sample_user.id)
        test_db_session.commit()

        success = service.revoke_refresh_token(test_db_session, raw_token)
        assert success is True

        test_db_session.refresh(record)
        assert record.revoked is True

        # Idempotent second revocation returns False
        success2 = service.revoke_refresh_token(test_db_session, raw_token)
        assert success2 is False

    def test_session_family_revocation(
        self, test_settings: Settings, test_db_session: Session, sample_user: User
    ):
        service = RefreshTokenService(test_settings)

        # Create two tokens in family A
        _, rec_a1 = service.create_refresh_token(test_db_session, sample_user.id)
        _, rec_a2 = service.create_refresh_token(
            test_db_session, sample_user.id, family_id=rec_a1.family_id
        )

        # Create one token in independent family B (e.g., another device)
        _, rec_b = service.create_refresh_token(test_db_session, sample_user.id)
        test_db_session.commit()

        # Revoke session family A (e.g. User logs out on device A)
        revoked_count = service.revoke_session(test_db_session, rec_a1.family_id)
        assert revoked_count == 2

        test_db_session.refresh(rec_a1)
        test_db_session.refresh(rec_a2)
        test_db_session.refresh(rec_b)

        assert rec_a1.revoked is True
        assert rec_a2.revoked is True
        assert rec_b.revoked is False  # Device B session remains untouched

    def test_user_wide_revocation(
        self, test_settings: Settings, test_db_session: Session, sample_user: User
    ):
        service = RefreshTokenService(test_settings)

        # Create multiple sessions for sample_user
        service.create_refresh_token(test_db_session, sample_user.id)
        service.create_refresh_token(test_db_session, sample_user.id)

        # Create session for a different user
        other_user = User(
            email="other@climaforge.test",
            hashed_password="pw",
            role="operator",
        )
        test_db_session.add(other_user)
        test_db_session.commit()
        _, other_rec = service.create_refresh_token(test_db_session, other_user.id)
        test_db_session.commit()

        # User-wide revocation (e.g. Password reset or admin security action)
        count = service.revoke_all_user_tokens(test_db_session, sample_user.id)
        assert count == 2

        # Other user's tokens must remain unaffected
        test_db_session.refresh(other_rec)
        assert other_rec.revoked is False
