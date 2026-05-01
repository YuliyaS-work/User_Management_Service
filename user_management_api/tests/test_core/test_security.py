import uuid
from datetime import datetime, timedelta, timezone

import pytest
from unittest.mock import patch, AsyncMock

from jose import jwt, JWTError

from src.user_management_api.core.config import Settings, settings
from src.user_management_api.core.security import get_password_hash, verify_password, get_token_hash, \
    create_access_token, create_reset_password_token, create_refresh_token, validate_access_token, \
    validate_refresh_token, validate_reset_password_token
from src.user_management_api.exceptions.auth import AuthenticationException
from src.user_management_api.schemas.auth import PayLoadAccessToken, PayLoadRefreshToken, PayLoadResetPasswordToken


def test_get_password_hash_returns_string():
    hash_obj = get_password_hash("password")
    assert isinstance(hash_obj, str) # returns str value
    assert len(hash_obj) > 0 # not returns empty string


def test_verify_password_success():
    with patch("src.user_management_api.core.security.pwd.verify") as mock_verify:
        mock_verify.return_value = True

        assert verify_password("raw_password", "hashed_password") is True
        mock_verify.assert_called_once_with("raw_password", "hashed_password")


def test_verify_password_fail():
    with patch("src.user_management_api.core.security.pwd.verify") as mock_verify:
        mock_verify.return_value = False

        assert verify_password("raw_password", "hashed_password") is False
        mock_verify.assert_called_once_with("raw_password", "hashed_password")


def test_get_token_hash_returns_string():
    hash_obj = get_token_hash("token")
    assert isinstance(hash_obj, str)  # returns str value
    assert len(hash_obj) > 0  # not returns empty string


@pytest.fixture
def jwt_settings(monkeypatch):
    monkeypatch.setattr(settings,"secret_key", "secret")
    monkeypatch.setattr(settings,"algorithm", "HS256")

@pytest.fixture
def payload_tokens_access_refresh():
    return {"sub": str(uuid.uuid4())}

@pytest.fixture
def payload_token_reset_password():
    return "name@example.com"



@pytest.fixture
def decode_tokens(jwt_settings):
    def _decode_tokens(token):
        decoded_token = jwt.decode(token, key=settings.secret_key, algorithms=[settings.algorithm])
        return decoded_token
    return _decode_tokens


def test_create_access_token_returns_string(payload_tokens_access_refresh):
    token = create_access_token(payload_tokens_access_refresh)
    assert isinstance(token, str)
    assert len(token) > 0


def test_create_access_token_decodable(payload_tokens_access_refresh, decode_tokens, jwt_settings):
    token = create_access_token(payload_tokens_access_refresh)
    decoded_token = decode_tokens(token)
    assert isinstance(decoded_token, dict)


def test_create_access_token_body(payload_tokens_access_refresh, decode_tokens, jwt_settings, freezer_time):
    token = create_access_token(payload_tokens_access_refresh)
    decoded_token = decode_tokens(token)
    assert isinstance(decoded_token["sub"], str)
    expected_date = int((datetime(2026,4,28,12,0,0, tzinfo=timezone.utc)+timedelta(minutes=10)).timestamp())
    assert decoded_token["exp"] == expected_date
    assert decoded_token["type"] == "access"
    assert isinstance(decoded_token["jti"], str)


def test_create_access_token_unique_jti(payload_tokens_access_refresh, decode_tokens, jwt_settings, freezer_time):
    token1 = create_access_token(payload_tokens_access_refresh)
    decoded_token1 = decode_tokens(token1)
    token2 = create_access_token(payload_tokens_access_refresh)
    decoded_token2 = decode_tokens(token2)
    assert decoded_token1["jti"] != decoded_token2["jti"]


def test_create_refresh_token_returns_tuple(payload_tokens_access_refresh):
    token = create_refresh_token(payload_tokens_access_refresh)
    assert isinstance(token, tuple)
    assert len(token) > 0


def test_create_refresh_token_decodable(payload_tokens_access_refresh, decode_tokens, jwt_settings):
    token = create_refresh_token(payload_tokens_access_refresh)
    decoded_token = decode_tokens(token[0])
    assert isinstance(decoded_token, dict)

def test_create_refresh_token_body(payload_tokens_access_refresh, decode_tokens, jwt_settings, freezer_time):
    token = create_refresh_token(payload_tokens_access_refresh)
    decoded_token = decode_tokens(token[0])
    assert isinstance(decoded_token["sub"], str)
    expected_date = int((datetime(2026,4,28,12,0,0, tzinfo=timezone.utc)+timedelta(days=30)).timestamp())
    assert decoded_token["exp"] == expected_date
    assert decoded_token["type"] == "refresh"
    assert isinstance(decoded_token["jti"], str)


def test_create_refresh_token_unique_jti(payload_tokens_access_refresh, decode_tokens, jwt_settings, freezer_time):
    token1 = create_refresh_token(payload_tokens_access_refresh)
    decoded_token1 = decode_tokens(token1[0])
    token2 = create_refresh_token(payload_tokens_access_refresh)
    decoded_token2 = decode_tokens(token2[0])
    assert decoded_token1["jti"] != decoded_token2["jti"]


def test_create_reset_password_token_returns_string(payload_token_reset_password):
    token = create_reset_password_token(payload_token_reset_password)
    assert isinstance(token, str)
    assert len(token) > 0

def test_create_reset_password_token_decodable(payload_token_reset_password, decode_tokens, jwt_settings):
    token = create_reset_password_token(payload_token_reset_password)
    decoded_token = decode_tokens(token)
    assert isinstance(decoded_token, dict)


def test_create_reset_password_token_body(payload_token_reset_password, decode_tokens, jwt_settings, freezer_time):
    token = create_reset_password_token(payload_token_reset_password)
    decoded_token = decode_tokens(token)
    assert isinstance(decoded_token["sub"], str)
    expected_date = int((datetime(2026,4,28,12,0,0, tzinfo=timezone.utc)+timedelta(minutes=10)).timestamp())
    assert decoded_token["exp"] == expected_date
    assert decoded_token["type"] == "reset_password"
    assert isinstance(decoded_token["jti"], str)


def test_create_reset_password_token_unique_jti(payload_token_reset_password, decode_tokens, jwt_settings, freezer_time):
    token1 = create_reset_password_token(payload_token_reset_password)
    decoded_token1 = decode_tokens(token1)
    token2 = create_reset_password_token(payload_token_reset_password)
    decoded_token2 = decode_tokens(token2)
    assert decoded_token1["jti"] != decoded_token2["jti"]


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
def test_decode_token_check_token_payload(monkeypatch, jwt_settings, payload, schema):
    from src.user_management_api.core.security import decode_token
    from src.user_management_api.schemas import auth

    def fake_token_decode(token, key,  algorithms):
        return payload

    monkeypatch.setattr("src.user_management_api.core.security.jwt.decode", fake_token_decode)

    result = decode_token("fake_token")

    expected_schema = getattr(auth, schema)

    assert isinstance(result, expected_schema)

    for key, value in payload.items():
        assert getattr(result, key) == value


def test_decode_token_empy_payload(monkeypatch, jwt_settings):
    from src.user_management_api.core.security import decode_token

    def fake_token_decode(token, key,  algorithms):
        payload = {}
        return payload

    monkeypatch.setattr("src.user_management_api.core.security.jwt.decode", fake_token_decode)

    with pytest.raises(AuthenticationException):
        decode_token("empty_token")


def test_decode_token_jwterror(monkeypatch, jwt_settings):
    from src.user_management_api.core.security import decode_token

    def fake_token_decode(token, key,  algorithms):
        raise JWTError

    monkeypatch.setattr("src.user_management_api.core.security.jwt.decode", fake_token_decode)

    with pytest.raises(AuthenticationException) as e:
        decode_token("bad_token")

    assert e.value.detail == "Token invalid"


def test_decode_token_unknown_type_token(monkeypatch, jwt_settings):
    from src.user_management_api.core.security import decode_token

    def fake_token_decode(token, key,  algorithms):
        payload = {"sub": "123",
                "exp": int((datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc) + timedelta(days=30)).timestamp()),
                "type": "unknown",
                "jti": "12345678123456781234567812345678",}
        return payload

    monkeypatch.setattr("src.user_management_api.core.security.jwt.decode", fake_token_decode)

    with pytest.raises(AuthenticationException) as e:
        decode_token("unknown_token")

    assert e.value.detail == "Unknown token type"


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
    with pytest.raises(AuthenticationException) as e:
        validate_access_token(payload)

    assert e.value.detail == "Token is over"



def test_access_token_payload_not_expire():
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
    with pytest.raises(Exception):
        PayLoadAccessToken(
            sub=None,
            exp=int((datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc) + timedelta(minutes=10)).timestamp()),
            type="access",
            jti="12345678123456781234567812345678",
            group_id=1,
            roles=["USER"]
        )


@pytest.fixture
def mock_redis():
    mock = AsyncMock()

    with patch("src.user_management_api.core.security.r", mock):
        yield mock


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
async def test_validate_refresh_token_success(payload, freezer_time, mock_redis):
    mock_redis.get.side_effect = ["saved_hash", None]

    user_id, jti = await validate_refresh_token(payload, "saved_hash")
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
async def test_validate_refresh_token_type(payload, freezer_time, mock_redis):
    mock_redis.get.side_effect = ["saved_hash", None]

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
async def test_validate_refresh_token_expire(payload, freezer_time, mock_redis):
    mock_redis.get.side_effect = ["saved_hash", None]

    with pytest.raises(AuthenticationException) as e:
        await validate_refresh_token(payload, "saved_hash")

    assert e.value.detail == "Token is over"



def test_refresh_token_payload_not_expire():
    with pytest.raises(Exception):
        PayLoadRefreshToken(
            sub="123",
            exp=None,
            type="refresh",
            jti="12345678123456781234567812345678"
        )


def test_refresh_token_payload_not_sub():
    with pytest.raises(Exception):
        PayLoadRefreshToken(
            sub=None,
            exp=int((datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc) + timedelta(minutes=10)).timestamp()),
            type="refresh",
            jti="12345678123456781234567812345678"
        )

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
    with pytest.raises(AuthenticationException) as e:
        validate_reset_password_token(payload)

    assert e.value.detail == "Token is over"



def test_reset_password_token_payload_not_expire():
    with pytest.raises(Exception):
        PayLoadResetPasswordToken(
            sub="123",
            exp=None,
            type="reset_password",
            jti="12345678123456781234567812345678"
        )


def test_reset_password_token_payload_not_sub():
    with pytest.raises(Exception):
        PayLoadResetPasswordToken(
            sub=None,
            exp=int((datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc) + timedelta(minutes=10)).timestamp()),
            type="reset_password",
            jti="12345678123456781234567812345678"
        )