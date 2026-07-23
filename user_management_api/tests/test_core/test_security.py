import uuid
from datetime import datetime, timedelta, timezone

import pytest
from unittest.mock import patch

from jose import jwt, JWTError

from src.user_management_api.core.config import settings
from src.user_management_api.core.security import get_password_hash, verify_password, get_token_hash, \
    create_access_token, create_reset_password_token, create_refresh_token, validate_access_token, \
    validate_refresh_token, validate_reset_password_token, decode_token
from src.user_management_api.exceptions.auth import AuthenticationException
from src.user_management_api.schemas import auth
from src.user_management_api.schemas.auth import PayLoadAccessToken, PayLoadRefreshToken, PayLoadResetPasswordToken

# Fixtures

@pytest.fixture
def jwt_settings(monkeypatch):
    """
    Override JWT settings to test creating and decoding tokens.
    """
    monkeypatch.setattr(settings,"secret_key", "secret")
    monkeypatch.setattr(settings,"algorithm", "HS256")


@pytest.fixture
def decode_tokens(jwt_settings):
    """
    Decode JWT tokens using patched test settings.
    """
    def _decode_tokens(token):
        decoded_token = jwt.decode(token, key=settings.secret_key, algorithms=[settings.algorithm])
        return decoded_token
    return _decode_tokens


@pytest.fixture
def payload_tokens_access_refresh():
    """
    Common part of payload for generating access and refresh tokens.
    """
    return {"sub": str(uuid.uuid4())}


@pytest.fixture
def payload_token_reset_password():
    """
    Payload part for generating reset password tokens.
    """
    return "name@example.com"


# Hashing tests

def test_get_password_hash_returns_string():
    """
    get_password_hash() should return a non-empty string.
    """
    # Act
    hash_obj = get_password_hash("password")

    # Assert
    assert isinstance(hash_obj, str)
    assert len(hash_obj) > 0


@patch("src.user_management_api.core.security.pwd.verify")
def test_verify_password_success(mock_verify):
    """
    verify_password() should return True when pwd.verify returns True.
    """
    # Act
    mock_verify.return_value = True

    # Assert
    assert verify_password("raw_password", "hashed_password") is True
    mock_verify.assert_called_once_with("raw_password", "hashed_password")


@patch("src.user_management_api.core.security.pwd.verify")
def test_verify_password_fail(mock_verify):
    """
    verify_password() should return False.
    """
    # Act
    mock_verify.return_value = False

    # Assert
    assert verify_password("raw_password", "hashed_password") is False
    mock_verify.assert_called_once_with("raw_password", "hashed_password")


def test_get_token_hash_returns_string():
    """
    get_token_hash() should return a non-empty string.
    """
    # Act
    hash_obj = get_token_hash("token")

    # Assert
    assert isinstance(hash_obj, str)
    assert len(hash_obj) > 0


# Access token tests

def test_create_access_token_returns_string(payload_tokens_access_refresh):
    """
    create_access_token() should return a non-empty string.
    """
    # Act
    token = create_access_token(payload_tokens_access_refresh)

    # Assert
    assert isinstance(token, str)
    assert len(token) > 0


def test_create_access_token_decodable(
        payload_tokens_access_refresh,
        decode_tokens,
        jwt_settings
):
    """
    Access token should be decodable into a dict.
    """
    # Act
    token = create_access_token(payload_tokens_access_refresh)
    decoded_token = decode_tokens(token)

    # Assert
    assert isinstance(decoded_token, dict)


def test_create_access_token_body(
        payload_tokens_access_refresh,
        decode_tokens,
        jwt_settings,
        freezer_time
):
    """
    Access token should contain correct fields: sub, exp, type, jti.
    """
    # Arrange
    expected_date = int((datetime(2026,4,28,12,0,0, tzinfo=timezone.utc)+timedelta(minutes=10)).timestamp())

    # Act
    token = create_access_token(payload_tokens_access_refresh)
    decoded_token = decode_tokens(token)

    # Assert
    assert isinstance(decoded_token["sub"], str)
    assert decoded_token["exp"] == expected_date
    assert decoded_token["type"] == "access"
    assert isinstance(decoded_token["jti"], str)


def test_create_access_token_unique_jti(
        payload_tokens_access_refresh,
        decode_tokens,
        jwt_settings,
        freezer_time
):
    """
    Each access token should have a unique jti.
    """
    # Act
    token1 = create_access_token(payload_tokens_access_refresh)
    decoded_token1 = decode_tokens(token1)
    token2 = create_access_token(payload_tokens_access_refresh)
    decoded_token2 = decode_tokens(token2)

    # Assert
    assert decoded_token1["jti"] != decoded_token2["jti"]


# Refresh token tests

def test_create_refresh_token_returns_tuple(payload_tokens_access_refresh):
    """
    create_refresh_token() should return a tuple (token, jti_hash).
    """
    # Act
    token = create_refresh_token(payload_tokens_access_refresh)

    # Assert
    assert isinstance(token, tuple)
    assert len(token) > 0


def test_create_refresh_token_decodable(
        payload_tokens_access_refresh,
        decode_tokens,
        jwt_settings
):
    """
    Refresh token should be decodable into a dict.
    """
    # Act
    token = create_refresh_token(payload_tokens_access_refresh)
    decoded_token = decode_tokens(token[0])

    # Assert
    assert isinstance(decoded_token, dict)


def test_create_refresh_token_body(
        payload_tokens_access_refresh,
        decode_tokens,
        jwt_settings,
        freezer_time
):
    """
    Refresh token should contain correct fields: sub, exp, type, jti.
    """
    # Arrange
    expected_date = int((datetime(2026,4,28,12,0,0, tzinfo=timezone.utc)+timedelta(days=30)).timestamp())

    # Act
    token = create_refresh_token(payload_tokens_access_refresh)
    decoded_token = decode_tokens(token[0])

    # Assert
    assert isinstance(decoded_token["sub"], str)
    assert decoded_token["exp"] == expected_date
    assert decoded_token["type"] == "refresh"
    assert isinstance(decoded_token["jti"], str)


def test_create_refresh_token_unique_jti(
        payload_tokens_access_refresh,
        decode_tokens,
        jwt_settings,
        freezer_time
):
    """
    Each refresh token should have a unique jti.
    """
    # Act
    token1 = create_refresh_token(payload_tokens_access_refresh)
    decoded_token1 = decode_tokens(token1[0])
    token2 = create_refresh_token(payload_tokens_access_refresh)
    decoded_token2 = decode_tokens(token2[0])

    # Assert
    assert decoded_token1["jti"] != decoded_token2["jti"]


# Reset password token tests

def test_create_reset_password_token_returns_string(payload_token_reset_password):
    """
    create_reset_password_token() should return a non-empty string.
    """
    # Act
    token = create_reset_password_token(payload_token_reset_password)

    # Assert
    assert isinstance(token, str)
    assert len(token) > 0

def test_create_reset_password_token_decodable(
        payload_token_reset_password,
        decode_tokens,
        jwt_settings
):
    """
    Reset password token should be decodable into a dict.
    """
    # Act
    token = create_reset_password_token(payload_token_reset_password)
    decoded_token = decode_tokens(token)

    # Assert
    assert isinstance(decoded_token, dict)


def test_create_reset_password_token_body(
        payload_token_reset_password,
        decode_tokens,
        jwt_settings,
        freezer_time
):
    """
    Reset password token should contain correct fields: sub, exp, type, jti.
    """
    # Arrange
    expected_date = int((datetime(2026,4,28,12,0,0, tzinfo=timezone.utc)+timedelta(minutes=10)).timestamp())

    # Act
    token = create_reset_password_token(payload_token_reset_password)
    decoded_token = decode_tokens(token)

    # Assert
    assert isinstance(decoded_token["sub"], str)
    assert decoded_token["exp"] == expected_date
    assert decoded_token["type"] == "reset_password"
    assert isinstance(decoded_token["jti"], str)


def test_create_reset_password_token_unique_jti(
        payload_token_reset_password,
        decode_tokens,
        jwt_settings,
        freezer_time
):
    """
    Each reset password token should have a unique jti.
    """
    # Act
    token1 = create_reset_password_token(payload_token_reset_password)
    decoded_token1 = decode_tokens(token1)
    token2 = create_reset_password_token(payload_token_reset_password)
    decoded_token2 = decode_tokens(token2)

    # Assert
    assert decoded_token1["jti"] != decoded_token2["jti"]


# decode token tests

@pytest.mark.parametrize(
    "payload, schema",
    [
        (
            {
        "sub": "123",
        "exp": int((datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc) + timedelta(minutes=10)).timestamp()),
        "type": "access",
        "jti": "12345678123456781234567812345678",
        "group_id": 1,
        "roles": ["USER"]
            },
            "PayLoadAccessToken"
        ),
        (
            {
                "sub": "123",
                "exp": int((datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc) + timedelta(days=30)).timestamp()),
                "type": "refresh",
                "jti": "12345678123456781234567812345678",
            },
            "PayLoadRefreshToken"
        ),
        (
            {
                "sub": "user@example.com",
                "exp": int((datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc) + timedelta(minutes=10)).timestamp()),
                "type": "reset_password",
                "jti": "12345678123456781234567812345678",
            },
            "PayLoadResetPasswordToken"
        )
    ]
)
def test_decode_token_check_token_payload(
        monkeypatch,
        jwt_settings,
        payload,
        schema
):
    """
    decode_token() should return correct schema instance based on token type.
    """
    # Arrange
    def fake_token_decode(token, key,  algorithms):
        return payload
    monkeypatch.setattr("src.user_management_api.core.security.jwt.decode", fake_token_decode)

    # Act
    result = decode_token("fake_token")
    expected_schema = getattr(auth, schema)

    # Assert
    assert isinstance(result, expected_schema)
    for key, value in payload.items():
        assert getattr(result, key) == value


def test_decode_token_empy_payload(monkeypatch, jwt_settings):
    """
    decode_token() should raise AuthenticationException for empty payload.
    """
    # Arrange
    def fake_token_decode(token, key,  algorithms):
        payload = {}
        return payload
    monkeypatch.setattr("src.user_management_api.core.security.jwt.decode", fake_token_decode)

    # Act/Assert
    with pytest.raises(AuthenticationException):
        decode_token("empty_token")


def test_decode_token_jwterror(monkeypatch, jwt_settings):
    """
    decode_token() should raise AuthenticationException when JWTError occurs.
    """
    # Arrange
    def fake_token_decode(token, key,  algorithms):
        raise JWTError
    monkeypatch.setattr("src.user_management_api.core.security.jwt.decode", fake_token_decode)

    # Act/ Assert
    with pytest.raises(AuthenticationException) as e:
        decode_token("bad_token")

    assert e.value.detail == "Token invalid"


def test_decode_token_unknown_type_token(monkeypatch, jwt_settings):
    """
    decode_token() should raise AuthenticationException for unknown token type.
    """
    # Arrange
    def fake_token_decode(token, key,  algorithms):
        payload = {"sub": "123",
                "exp": int((datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc) + timedelta(days=30)).timestamp()),
                "type": "unknown",
                "jti": "12345678123456781234567812345678",}
        return payload

    monkeypatch.setattr("src.user_management_api.core.security.jwt.decode", fake_token_decode)

    # Act/Assert
    with pytest.raises(AuthenticationException) as e:
        decode_token("unknown_token")

    assert e.value.detail == "Unknown token type"


# validate access token tests

@pytest.mark.parametrize(
    "payload",
    [
        PayLoadAccessToken(
            sub="123",
            exp=int((datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc) + timedelta(minutes=10)).timestamp()),
            type="access",
            jti="12345678123456781234567812345678",
            group_id=1,
            roles=["USER"]
        )
    ]
)
def test_validate_access_token_success(payload, freezer_time):
    """
    validate_access_token() should return True for valid access token.
    """
    # Act/Assert
    assert validate_access_token(payload) is True


@pytest.mark.parametrize(
    "payload",
    [
        PayLoadRefreshToken(
            sub="123",
            exp=int((datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc) + timedelta(days=30)).timestamp()),
            type="refresh",
            jti="12345678123456781234567812345678",
        )
    ]
)
def test_validate_access_token_type(payload, freezer_time):
    """
    validate_access_token() should reject non-access tokens.
    """
    # Act/Assert
    with pytest.raises(AuthenticationException) as e:
        validate_access_token(payload)

    assert e.value.detail == "Invalid token type"


@pytest.mark.parametrize(
    "payload",
    [
        PayLoadAccessToken(
            sub="123",
            exp=int((datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc) - timedelta(minutes=10)).timestamp()),
            type="access",
            jti="12345678123456781234567812345678",
            group_id=1,
            roles=["USER"]
        )
    ]
)
def test_validate_access_token_expire(payload, freezer_time):
    """
    validate_access_token() should reject expired access tokens.
    """
    # Act/Assert
    with pytest.raises(AuthenticationException) as e:
        validate_access_token(payload)

    assert e.value.detail == "Token is over"



def test_access_token_payload_not_expire():
    """
    PayLoadAccessToken should raise an exception when 'exp' is missing.
    """
    # Act/Assert
    with pytest.raises(Exception):
        PayLoadAccessToken(
            sub="123",
            exp=None,
            type="access",
            jti="12345678123456781234567812345678",
            group_id=1,
            roles=["USER"]
        )


def test_access_token_payload_not_sub():
    """
    PayLoadAccessToken should raise an exception when 'sub' is missing.
    """
    # Act/Assert
    with pytest.raises(Exception):
        PayLoadAccessToken(
            sub=None,
            exp=int((datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc) + timedelta(minutes=10)).timestamp()),
            type="access",
            jti="12345678123456781234567812345678",
            group_id=1,
            roles=["USER"]
        )


# validate refresh token tests

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        PayLoadRefreshToken(
            sub="123",
            exp=int((datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc) + timedelta(days=30)).timestamp()),
            type="refresh",
            jti="12345678123456781234567812345678"
        )
    ]
)
@patch("src.user_management_api.core.security.r")
async def test_validate_refresh_token_success(
        mock_redis,
        payload,
        freezer_time
):
    """
    validate_refresh_token() should return (user_id, jti) for valid refresh token.
    """
    # Arrange
    mock_redis.get.side_effect = ["saved_hash", None]

    # Act
    user_id, jti = await validate_refresh_token(payload, "saved_hash")

    # Assert
    assert user_id == "123"
    assert jti == "12345678123456781234567812345678"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        PayLoadAccessToken(
            sub="123",
            exp=int((datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc) + timedelta(minutes=10)).timestamp()),
            type="access",
            jti="12345678123456781234567812345678",
            group_id=1,
            roles=["USER"]
        )
    ]
)
@patch("src.user_management_api.core.security.r")
async def test_validate_refresh_token_type(
        mock_redis,
        payload,
        freezer_time
):
    """
    validate_refresh_token() should reject non-refresh tokens.
    """
    # Arrange
    mock_redis.get.side_effect = ["saved_hash", None]

    # Act/Assert
    with pytest.raises(AuthenticationException) as e:
        await validate_refresh_token(payload, "saved_hash")

    assert e.value.detail == "Invalid token type"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        PayLoadRefreshToken(
            sub="123",
            exp=int((datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc) - timedelta(days=30)).timestamp()),
            type="refresh",
            jti="12345678123456781234567812345678"
        )
    ]
)
@patch("src.user_management_api.core.security.r")
async def test_validate_refresh_token_expire(
        mock_redis,
        payload,
        freezer_time
):
    """
    validate_refresh_token() should reject expired refresh tokens.
    """
    # Arrange
    mock_redis.get.side_effect = ["saved_hash", None]

    # Act/Assert
    with pytest.raises(AuthenticationException) as e:
        await validate_refresh_token(payload, "saved_hash")

    assert e.value.detail == "Token is over"



def test_refresh_token_payload_not_expire():
    """
    PayLoadRefreshToken should raise an exception when 'exp' is missing.
    """
    with pytest.raises(Exception):
        PayLoadRefreshToken(
            sub="123",
            exp=None,
            type="refresh",
            jti="12345678123456781234567812345678"
        )


def test_refresh_token_payload_not_sub():
    """
    PayLoadRefreshToken should raise an exception when 'sub' is missing.
    """
    # Arrange/Act/Assert
    with pytest.raises(Exception):
        PayLoadRefreshToken(
            sub=None,
            exp=int((datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc) + timedelta(minutes=10)).timestamp()),
            type="refresh",
            jti="12345678123456781234567812345678"
        )


# validate reset password token tests

@pytest.mark.parametrize(
    "payload",
    [
        PayLoadResetPasswordToken(
            sub="user@example.com",
            exp=int((datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc) + timedelta(minutes=10)).timestamp()),
            type="reset_password",
            jti="12345678123456781234567812345678"
        )
    ]
)
def test_validate_reset_password_token_success(payload, freezer_time):
    """
    validate_reset_password_token() should return True for a valid reset password token.
    """
    # Act/Assert
    assert validate_reset_password_token(payload) is True


@pytest.mark.parametrize(
    "payload",
    [
        PayLoadRefreshToken(
            sub="123",
            exp=int((datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc) + timedelta(days=30)).timestamp()),
            type="refresh",
            jti="12345678123456781234567812345678",
        )
    ]
)
def test_validate_reset_password_token_type(payload, freezer_time):
    """
    validate_reset_password_token() should reject non-reset-password tokens.
    """
    # Act/Assert
    with pytest.raises(AuthenticationException) as e:
        validate_reset_password_token(payload)

    assert e.value.detail == "Invalid token type"


@pytest.mark.parametrize(
    "payload",
    [
        PayLoadResetPasswordToken(
            sub="123",
            exp=int((datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc) - timedelta(minutes=10)).timestamp()),
            type="reset_password",
            jti="12345678123456781234567812345678"
        )
    ]
)
def test_validate_reset_password_token_expire(payload, freezer_time):
    """
    validate_reset_password_token() should reject expired reset-password tokens.
    """
    # Act/Assert
    with pytest.raises(AuthenticationException) as e:
        validate_reset_password_token(payload)

    assert e.value.detail == "Token is over"



def test_reset_password_token_payload_not_expire():
    """
    PayLoadResetPasswordToken should raise an exception when 'exp' is missing.
    """
    # Act/Assert
    with pytest.raises(Exception):
        PayLoadResetPasswordToken(
            sub="123",
            exp=None,
            type="reset_password",
            jti="12345678123456781234567812345678"
        )


def test_reset_password_token_payload_not_sub():
    """
    PayLoadResetPasswordToken should raise an exception when 'sub' is missing.
    """
    # Act/Assert
    with pytest.raises(Exception):
        PayLoadResetPasswordToken(
            sub=None,
            exp=int((datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc) + timedelta(minutes=10)).timestamp()),
            type="reset_password",
            jti="12345678123456781234567812345678"
        )