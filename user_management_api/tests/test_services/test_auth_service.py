import json
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

import pytest
from sqlalchemy import BinaryExpression, BooleanClauseList

from src.user_management_api.exceptions.auth import AuthenticationException, ConflictException, APIException
from src.user_management_api.exceptions.user import ResourceNotFound
from src.user_management_api.schemas.auth import UserLogin, ForgetPasswordRequest, ResetPasswordRequest
from src.user_management_api.services.auth import get_current_user, create_and_store_tokens, verify_refresh_token, \
    register_user, login_user, logout_user, renew_tokens, reset_password, save_password
from tests.conftest import fake_background_tasks, FakeRequest


# Tests for get_current_user()

@patch("src.user_management_api.services.auth.validate_access_token")
@patch("src.user_management_api.services.auth.decode_token")
@patch("src.user_management_api.services.auth.get_access_token_from_cookie")
def test_get_current_user_success(
        mock_get_access_token_from_cookie,
        mock_decode_token,
        mock_validate_access_token,
        get_fake_request
):
    """
    get_current_user() should return user info when access token is valid.
    """
    # Arrange
    mock_get_access_token_from_cookie.return_value = "fake_token"

    mock_decode_token.return_value = type("Payload", (), {
        "sub": "123",
        "exp": int((datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc) + timedelta(minutes=10)).timestamp()),
        "type": "access",
        "jti": "12345678123456781234567812345678",
        "group_id": 1,
        "roles": ["USER"]
    })()
    mock_validate_access_token.return_value = None

    # Act
    user = get_current_user(get_fake_request)

    # Assert
    assert user.user_id == "123"
    assert user.group_id == 1
    assert user.roles == ["USER"]

    mock_get_access_token_from_cookie.assert_called_once_with(get_fake_request)
    mock_decode_token.assert_called_once_with("fake_token")
    mock_validate_access_token.assert_called_once_with(mock_decode_token.return_value)


# Tests for create_and_store_tokens()

@pytest.mark.asyncio
@patch("src.user_management_api.services.auth.save_refresh_token_to_redis")
@patch("src.user_management_api.services.auth.create_refresh_token")
@patch("src.user_management_api.services.auth.create_access_token")
@patch("src.user_management_api.services.auth.UserDAO.find_one_or_none_with_related_data")
async def test_create_and_store_tokens_success(
        mock_find_user,
        mock_create_access_token,
        mock_create_refresh_token,
        mock_save_refresh_token_to_redis,
        mock_db,
        mock_user
):
    """
    create_and_store_tokens() should generate tokens and store refresh token in Redis.
    """
    # Arrange
    user_id = "123"
    mock_find_user.return_value = mock_user
    mock_create_access_token.return_value = "fake_access_token"
    mock_create_refresh_token.return_value = ("fake_refresh_token", "fake_jti")
    mock_save_refresh_token_to_redis.return_value = None

    # Act
    access_token, refresh_token = await create_and_store_tokens(user_id, mock_db)

    # Assert
    assert access_token == "fake_access_token"
    assert refresh_token == "fake_refresh_token"

    args, kwargs = mock_find_user.call_args
    assert args[0] is mock_db
    assert isinstance(args[1], BinaryExpression)

    mock_create_refresh_token.assert_called_once_with({"sub": user_id})
    mock_save_refresh_token_to_redis.assert_called_once_with("fake_refresh_token", "fake_jti", user_id)


@pytest.mark.asyncio
@patch("src.user_management_api.services.auth.UserDAO.find_one_or_none_with_related_data")
async def test_create_and_store_tokens_user_not_found(
        mock_find_user,
        mock_db
):
    """
    create_and_store_tokens() should raise ResourceNotFound when user does not exist.
    """
    # Arrange
    mock_find_user.return_value = None

    # Act
    with pytest.raises(ResourceNotFound) as e:
        await create_and_store_tokens("123", mock_db)

    # Assert
    assert e.value.detail == "User is not found"
    mock_find_user.assert_called_once()


# Tests for verify_refresh_token()

@pytest.mark.asyncio
@patch("src.user_management_api.services.auth.validate_refresh_token")
@patch("src.user_management_api.services.auth.get_token_hash")
@patch("src.user_management_api.services.auth.decode_token")
@patch("src.user_management_api.services.auth.get_refresh_token_from_cookie")
async def test_verify_refresh_token_success(
        mock_get_refresh_token_from_cookie,
        mock_decode_token,
        mock_get_token_hash,
        mock_validate_refresh_token,
        get_fake_request
):
    """
    verify_refresh_token() should return user_id and jti when refresh token is valid.
    """
    # Arrange
    mock_get_refresh_token_from_cookie.return_value = "fake_token"
    mock_decode_token.return_value = type("Payload", (), {
        "sub": "123",
        "exp": int((datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc) + timedelta(minutes=10)).timestamp()),
        "type": "refresh",
        "jti": "12345678123456781234567812345678"
    })()
    mock_get_token_hash.return_value = "fake_hash_token"
    mock_validate_refresh_token.return_value = ("123", "12345678123456781234567812345678")

    # Act
    user_id, jti = await verify_refresh_token(get_fake_request)

    # Assert
    assert user_id == "123"
    assert jti == "12345678123456781234567812345678"
    assert (user_id, jti) == ("123", "12345678123456781234567812345678")

    mock_get_refresh_token_from_cookie.assert_called_once_with(get_fake_request)
    mock_decode_token.assert_called_once_with("fake_token")
    mock_validate_refresh_token.assert_called_once_with(mock_decode_token.return_value, mock_get_token_hash.return_value)


@pytest.mark.asyncio
@patch("src.user_management_api.services.auth.validate_refresh_token")
@patch("src.user_management_api.services.auth.get_token_hash")
@patch("src.user_management_api.services.auth.decode_token")
@patch("src.user_management_api.services.auth.get_refresh_token_from_cookie")
async def test_verify_refresh_token_fail(
        mock_get_refresh_token_from_cookie,
        mock_decode_token,
        mock_get_token_hash,
        mock_validate_refresh_token,
        get_fake_request
):
    """
    verify_refresh_token() should raise AuthenticationException for invalid refresh token.
    """
    # Arrange
    mock_get_refresh_token_from_cookie.return_value = "fake_token"
    mock_decode_token.return_value = {"sub": "123"}
    mock_get_token_hash.return_value = "fake_hash_token"
    mock_validate_refresh_token.side_effect = AuthenticationException

    # Act
    with pytest.raises(AuthenticationException) as e:
        await verify_refresh_token(get_fake_request)

    # Assert
    mock_validate_refresh_token.assert_called_once()


# Tests for register_user()

@pytest.mark.asyncio
@patch("src.user_management_api.services.auth.send_tokens_to_user")
@patch("src.user_management_api.services.auth.create_and_store_tokens")
@patch("src.user_management_api.services.auth.UserDAO.add")
@patch("src.user_management_api.services.auth.get_password_hash")
@patch("src.user_management_api.services.auth.UserDAO.find_one_or_none")
async def test_register_user_success(
        mock_find_user,
        mock_get_password_hash,
        mock_add_user,
        mock_create_and_store_tokens,
        mock_send_token_to_user,
        mock_db,
        fake_response,
        user_register_data
):
    """
    register_user() should create a new user and return access/refresh tokens.
    """
    # Arrange
    mock_find_user.return_value = None
    mock_get_password_hash.return_value = "fake_password_hash"
    mock_user = MagicMock()
    mock_user.id = "123"
    mock_add_user.return_value = mock_user
    mock_create_and_store_tokens.return_value = ("fake_access_token", "fake_refresh_token")
    mock_send_token_to_user.return_value = None

    # Act
    result = await register_user(fake_response, user_register_data, mock_db)

    # Assert
    assert mock_find_user.call_count == 3
    calls = mock_find_user.call_args_list

    for call in calls:
        args, kwargs = call
        assert args[0] is mock_db
        assert isinstance(args[1], BinaryExpression)

    mock_get_password_hash.assert_called_once_with(user_register_data.password)
    mock_add_user.assert_called_once()
    add_args, add_kwargs = mock_add_user.call_args

    assert add_args[0] is mock_db
    assert add_kwargs["name"] == user_register_data.name
    assert add_kwargs["surname"] == user_register_data.surname
    assert add_kwargs["username"] == user_register_data.username
    assert add_kwargs["email"] == user_register_data.email
    assert add_kwargs["password"] == "fake_password_hash"
    assert add_kwargs["phone_number"] == user_register_data.phone_number

    mock_create_and_store_tokens.assert_called_once_with(
        "123",
        mock_db
    )
    mock_send_token_to_user.assert_called_once_with(
        fake_response,
        "fake_access_token",
        "fake_refresh_token"
    )
    assert result.access_token == "fake_access_token"
    assert result.refresh_token == "fake_refresh_token"



@pytest.mark.asyncio
@patch("src.user_management_api.services.auth.UserDAO.find_one_or_none")
async def test_register_user_username_conflict(
        mock_find_user,
        mock_db,
        fake_response,
        user_register_data
):
    """
    register_user() should raise ConflictException when username already exists.
    """
    # Arrange
    mock_find_user.side_effect = [True, None, None]

    # Act
    with pytest.raises(ConflictException) as e:
        await register_user(fake_response, user_register_data, mock_db)

    # Assert
    assert e.value.detail == "Username already exists"
    mock_find_user.assert_called_once()


@pytest.mark.asyncio
@patch("src.user_management_api.services.auth.UserDAO.find_one_or_none")
async def test_register_user_email_conflict(
        mock_find_user,
        mock_db,
        fake_response,
        user_register_data
):
    """
    register_user() should raise ConflictException when email already exists.
    """
    # Arrange
    mock_find_user.side_effect = [None, True, None]

    # Act
    with pytest.raises(ConflictException) as e:
        await register_user(fake_response, user_register_data, mock_db)

    # Assert
    assert e.value.detail == "Email already exists"
    assert mock_find_user.call_count == 2


@pytest.mark.asyncio
@patch("src.user_management_api.services.auth.UserDAO.find_one_or_none")
async def test_register_user_username_conflict(
        mock_find_user,
        mock_db,
        fake_response,
        user_register_data
):
    """
    register_user() should raise ConflictException when phone number already exists.
    """
    # Arrange
    mock_find_user.side_effect = [None, None, True]

    # Act
    with pytest.raises(ConflictException) as e:
        await register_user(fake_response, user_register_data, mock_db)

    # Assert
    assert e.value.detail == "Phone number already exists"
    assert mock_find_user.call_count == 3


# Tests for login_user()

@pytest.mark.asyncio
@patch("src.user_management_api.services.auth.send_tokens_to_user")
@patch("src.user_management_api.services.auth.create_and_store_tokens")
@patch("src.user_management_api.services.auth.verify_password")
@patch("src.user_management_api.services.auth.UserDAO.find_one_or_none")
async def test_login_user_success_username(
        mock_find_user,
        mock_verify_password,
        mock_create_and_store_tokens,
        mock_send_tokens_to_user,
        mock_db,
        fake_response,
        fake_request
):
    """
    login_user() should authenticate user by username and return tokens.
    """
    # Arrange
    mock_user = MagicMock()
    mock_user.id = "123"
    mock_user.username = "username"
    mock_user.password = "fake_password_hash"
    mock_find_user.return_value = mock_user
    mock_verify_password.return_value = True
    mock_create_and_store_tokens.return_value = ("fake_access_token", "fake_refresh_token")
    user_data = UserLogin(login="username", password="Password1!")

    # Act
    result = await login_user(fake_request, fake_response, user_data, mock_db)

    # Assert
    assert result.access_token == "fake_access_token"
    assert result.refresh_token == "fake_refresh_token"

    mock_find_user.assert_called_once()
    args, kwargs = mock_find_user.call_args
    assert args[0] is mock_db
    assert isinstance(args[1], (BinaryExpression, BooleanClauseList))

    mock_verify_password.assert_called_once_with("Password1!", "fake_password_hash")
    mock_create_and_store_tokens.assert_called_once_with("123", mock_db)
    mock_send_tokens_to_user.assert_called_once_with(fake_response, "fake_access_token", "fake_refresh_token")



@pytest.mark.asyncio
@patch("src.user_management_api.services.auth.send_tokens_to_user")
@patch("src.user_management_api.services.auth.create_and_store_tokens")
@patch("src.user_management_api.services.auth.verify_password")
@patch("src.user_management_api.services.auth.UserDAO.find_one_or_none")
@patch("src.user_management_api.services.auth.phonenumbers.is_valid_number")
@patch("src.user_management_api.services.auth.phonenumbers.parse")
async def test_login_user_success_phonenumber(
        mock_parse,
        mock_is_valid,
        mock_find_user,
        mock_verify_password,
        mock_create_and_store_tokens,
        mock_send_tokens_to_user,
        mock_db,
        fake_response,
        fake_request
):
    """
    login_user() should authenticate user by phone number and return tokens.
    """
    # Arrange
    mock_phone_obj = MagicMock()
    mock_phone_obj.italian_leading_zero = False
    mock_phone_obj.numbers_of_leading_zeros = 0
    mock_parse.return_value = mock_phone_obj
    mock_is_valid.return_value = True

    mock_user = MagicMock()
    mock_user.id = "123"
    mock_user.password = "fake_password_hash"
    mock_find_user.return_value = mock_user

    mock_verify_password.return_value = True
    mock_create_and_store_tokens.return_value = ("fake_access_token", "fake_refresh_token")

    user_data = UserLogin(login="+375291111111", password="Password1!")

    # Act
    result = await login_user(fake_request, fake_response, user_data, mock_db)

    # Assert
    assert result.access_token == "fake_access_token"
    assert result.refresh_token == "fake_refresh_token"

    mock_parse.assert_called_once()
    mock_is_valid.assert_called_once()
    mock_find_user.assert_called_once()


@pytest.mark.asyncio
@patch("src.user_management_api.services.auth.create_and_store_tokens")
@patch("src.user_management_api.services.auth.verify_password")
@patch("src.user_management_api.services.auth.UserDAO.find_one_or_none")
async def test_login_user_success_email(
        mock_find_user,
        mock_verify_password,
        mock_create_and_store_tokens,
        mock_db,
        fake_response,
        fake_request
):
    """
    login_user() should authenticate user by email and return tokens.
    """
    # Arrange
    mock_user = MagicMock()
    mock_user.id = "123"
    mock_user.password = "fake_password_hash"
    mock_find_user.return_value = mock_user

    mock_verify_password.return_value = True
    mock_create_and_store_tokens.return_value = ("fake_access_token", "fake_refresh_token")

    user_data = UserLogin(login="user@example.com", password="Password1!")

    # Act
    result = await login_user(fake_request, fake_response, user_data, mock_db)

    # Assert
    assert result.access_token == "fake_access_token"
    assert result.refresh_token == "fake_refresh_token"

    mock_find_user.assert_called_once()



@pytest.mark.asyncio
@patch("src.user_management_api.services.auth.UserDAO.find_one_or_none")
async def test_login_user_not_found(
        mock_find_user,
        mock_db,
        fake_response,
        fake_request
):
    """
    login_user() should raise AuthenticationException when user is not found.
    """
    mock_find_user.return_value = None

    user_data = UserLogin(login="unknown", password="Password1!")

    # Act
    with pytest.raises(AuthenticationException) as e:
        await login_user(fake_request, fake_response, user_data, mock_db)

    # Assert
    assert e.value.detail == "User's not found."

    mock_find_user.assert_called_once()


@pytest.mark.asyncio
@patch("src.user_management_api.services.auth.verify_password")
@patch("src.user_management_api.services.auth.UserDAO.find_one_or_none")
async def test_login_user_wrong_password(
        mock_find_user,
        mock_verify_password,
        mock_db,
        fake_response,
        fake_request
):
    """
    login_user() should raise AuthenticationException when password is incorrect.
    """
    # Arrange
    mock_user = MagicMock()
    mock_user.username = "username"
    mock_user.password = "fake_password_hash"
    mock_find_user.return_value = mock_user

    mock_verify_password.return_value = False

    user_data = UserLogin(login="username", password="wrong_password")

    # Act
    with pytest.raises(AuthenticationException):
        await login_user(fake_request, fake_response, user_data, mock_db)

    # Assert
    mock_verify_password.assert_called_once_with("wrong_password", "fake_password_hash")


@pytest.mark.asyncio
@patch("src.user_management_api.services.auth.UserDAO.find_one_or_none")
async def test_login_user_wrong_phonenumber(
        mock_find_user,
        mock_db,
        fake_response,
        fake_request
):
    """
    login_user() should raise AuthenticationException when phone number is invalid.
    """
    # Arrange
    mock_find_user.return_value = None
    user_data = UserLogin(login="wrong_phonenumber", password="Password1!")

    # Act
    with pytest.raises(AuthenticationException) as e:
        await login_user(fake_request, fake_response, user_data, mock_db)

    # Assert
    assert e.value.detail == "User's not found."

    mock_find_user.assert_called_once()


@pytest.mark.asyncio
@patch("src.user_management_api.services.auth.UserDAO.find_one_or_none")
async def test_login_user_wrong_email(
        mock_find_user,
        mock_db,
        fake_response,
        fake_request
):
    """
    login_user() should raise AuthenticationException when email is invalid.
    """
    # Arrange
    mock_find_user.return_value = None
    user_data = UserLogin(login="wrong_email", password="Password1!")

    # Act
    with pytest.raises(AuthenticationException) as e:
        await login_user(fake_request, fake_response, user_data, mock_db)

    # Assert
    assert e.value.detail == "User's not found."

    mock_find_user.assert_called_once()


# Tests for logout_user()

@pytest.mark.asyncio
@patch("src.user_management_api.services.auth.delete_tokens_from_cookies")
@patch("src.user_management_api.services.auth.delete_refresh_token_from_redis")
@patch("src.user_management_api.services.auth.verify_refresh_token")
async def test_logout_user_success(
        mock_verify_refresh_token,
        mock_delete_refresh_token,
        mock_delete_tokens_from_cookies,
        fake_response,
        fake_request
):
    """
    logout_user() should delete refresh token and cookies successfully.
    """
    # Arrange
    mock_verify_refresh_token.return_value = ("123", "fake_jti")

    # Act
    result = await logout_user(fake_response, fake_request)

    # Assert
    assert result == {"message": "User logged out"}

    mock_verify_refresh_token.assert_called_once_with(fake_request)
    mock_delete_refresh_token.assert_called_once_with("123", "fake_jti")
    mock_delete_tokens_from_cookies.assert_called_once_with(fake_response)


@pytest.mark.asyncio
@patch("src.user_management_api.services.auth.delete_tokens_from_cookies")
@patch("src.user_management_api.services.auth.delete_refresh_token_from_redis")
@patch("src.user_management_api.services.auth.verify_refresh_token")
async def test_logout_user_fail(
        mock_verify_refresh_token,
        mock_delete_refresh_token_from_redis,
        mock_delete_tokens_from_cookies,
        fake_response,
        fake_request
):
    """
    logout_user() should raise AuthenticationException when refresh token is invalid.
    """
    # Arrange
    mock_verify_refresh_token.side_effect = AuthenticationException

    # Act
    with pytest.raises(AuthenticationException):
        await logout_user(fake_response, fake_request)

    # Assert
    mock_verify_refresh_token.assert_called_once_with(fake_request)
    mock_delete_refresh_token_from_redis.assert_not_called()
    mock_delete_tokens_from_cookies.assert_called_once_with(fake_response)


#  Tests for renew_tokens()

@pytest.mark.asyncio
@patch("src.user_management_api.services.auth.send_tokens_to_user")
@patch("src.user_management_api.services.auth.create_and_store_tokens")
@patch("src.user_management_api.services.auth.delete_refresh_token_from_redis")
@patch("src.user_management_api.services.auth.verify_refresh_token")
async def test_renew_tokens_success(
        mock_verify_refresh_token,
        mock_delete_refresh_token_from_redis,
        mock_create_and_store_tokens,
        mock_send_tokens_to_user,
        fake_response,
        fake_request,
        mock_db
):
    """
    renew_tokens() should issue new tokens and revoke old refresh token.
    """
    # Arrange
    mock_verify_refresh_token.return_value = ("123", "jti")
    mock_create_and_store_tokens.return_value = ("fake_access_token", "fake_refresh_token")

    # Act
    result = await renew_tokens(fake_request, fake_response, mock_db)

    # Assert
    assert result.access_token == "fake_access_token"
    assert result.refresh_token == "fake_refresh_token"

    mock_verify_refresh_token.assert_called_once_with(fake_request)
    mock_create_and_store_tokens.assert_called_once_with("123", mock_db)
    mock_delete_refresh_token_from_redis.assert_called_once_with("123", "jti")
    mock_send_tokens_to_user.assert_called_once_with(fake_response, "fake_access_token", "fake_refresh_token")


@pytest.mark.asyncio
@patch("src.user_management_api.services.auth.create_and_store_tokens")
@patch("src.user_management_api.services.auth.delete_tokens_from_cookies")
@patch("src.user_management_api.services.auth.verify_refresh_token")
async def test_renew_tokens_fail(
        mock_verify_refresh_token,
        mock_delete_tokens_from_cookies,
        mock_create_and_store_tokens,
        fake_response,
        fake_request,
        mock_db
):
    """
    renew_tokens() should raise APIException when refresh token validation fails.
    """
    # Arrange
    mock_verify_refresh_token.side_effect = APIException()

    # Act
    with pytest.raises(APIException):
        await renew_tokens(fake_request, fake_response, mock_db)

    # Assert
    mock_verify_refresh_token.assert_called_once_with(fake_request)
    mock_delete_tokens_from_cookies.assert_called_once_with(fake_response)
    mock_create_and_store_tokens.assert_not_called()


@pytest.mark.asyncio
@patch("src.user_management_api.services.auth.delete_tokens_from_cookies")
@patch("src.user_management_api.services.auth.create_and_store_tokens")
@patch("src.user_management_api.services.auth.delete_refresh_token_from_redis")
@patch("src.user_management_api.services.auth.verify_refresh_token")
async def test_renew_tokens_delete_refresh_token_fails(
        mock_verify_refresh_token,
        mock_delete_refresh_token_from_redis,
        mock_create_and_store_tokens,
        mock_delete_tokens_from_cookies,
        fake_response,
        fake_request,
        mock_db
):
    """
    renew_tokens() should raise APIException when old refresh token cannot be deleted.
    """
    # Arrange
    mock_verify_refresh_token.return_value = ("123", "jti")
    mock_delete_refresh_token_from_redis.side_effect = APIException()

    # Act
    with pytest.raises(APIException):
        await renew_tokens(fake_request, fake_response, mock_db)

    # Assert
    mock_verify_refresh_token.assert_called_once_with(fake_request)
    mock_delete_tokens_from_cookies.assert_called_once_with(fake_response)
    mock_create_and_store_tokens.assert_not_called()


@pytest.mark.asyncio
@patch("src.user_management_api.services.auth.delete_tokens_from_cookies")
@patch("src.user_management_api.services.auth.send_tokens_to_user")
@patch("src.user_management_api.services.auth.create_and_store_tokens")
@patch("src.user_management_api.services.auth.delete_refresh_token_from_redis")
@patch("src.user_management_api.services.auth.verify_refresh_token")
async def test_renew_tokens_sent_token_to_user_fail(
        mock_verify_refresh_token,
        mock_delete_refresh_token_from_redis,
        mock_create_and_store_tokens,
        mock_send_tokens_to_user,
        mock_delete_tokens_from_cookies,
        fake_response,
        fake_request,
        mock_db
):
    """
    renew_tokens() should raise APIException when sending tokens to user fails.
    """
    # Arrange
    mock_verify_refresh_token.return_value = ("123", "jti")
    mock_delete_refresh_token_from_redis.return_value = None
    mock_create_and_store_tokens.return_value = ("fake_access_token", "fake_refresh_token")
    mock_send_tokens_to_user.side_effect = APIException()

    # Act
    with pytest.raises(APIException):
        await renew_tokens(fake_request, fake_response, mock_db)

    # Assert
    mock_verify_refresh_token.assert_called_once_with(fake_request)
    mock_create_and_store_tokens.assert_called_once_with("123", mock_db)
    mock_delete_refresh_token_from_redis.assert_called_once_with("123", "jti")
    mock_send_tokens_to_user.assert_called_once_with(fake_response, "fake_access_token", "fake_refresh_token")
    mock_delete_tokens_from_cookies.assert_called_once_with(fake_response)


@pytest.mark.asyncio
@patch("src.user_management_api.services.auth.delete_tokens_from_cookies")
@patch("src.user_management_api.services.auth.create_and_store_tokens")
@patch("src.user_management_api.services.auth.delete_refresh_token_from_redis")
@patch("src.user_management_api.services.auth.verify_refresh_token")
async def test_renew_tokens_create_tokens_fail(
        mock_verify_refresh_token,
        mock_delete_refresh_token_from_redis,
        mock_create_and_store_tokens,
        mock_delete_tokens_from_cookies,
        fake_response,
        fake_request,
        mock_db
):
    """
    renew_tokens() should raise APIException when new tokens cannot be created.
    """
    # Arrange
    mock_verify_refresh_token.return_value = ("123", "jti")
    mock_delete_refresh_token_from_redis.return_value = None
    mock_create_and_store_tokens.side_effect = APIException()

    # Act
    with pytest.raises(APIException):
        await renew_tokens(fake_request, fake_response, mock_db)

    # Assert
    mock_verify_refresh_token.assert_called_once_with(fake_request)
    mock_delete_refresh_token_from_redis.assert_called_once_with("123", "jti")
    mock_create_and_store_tokens.assert_called_once_with("123", mock_db)
    mock_delete_tokens_from_cookies.assert_called_once_with(fake_response)


# Tests for reset_password()

@pytest.mark.asyncio
@patch("src.user_management_api.services.auth.publish_message")
@patch("src.user_management_api.services.auth.create_reset_password_token")
async def test_reset_password_success(
        mock_create_reset_password_token,
        mock_publish_message,
        fake_background_tasks,
        freezer_time
):
    """
    reset_password() should generate reset token and publish message to RabbitMQ.
    """
    # Arrange
    mock_create_reset_password_token.return_value = "fake_token"
    request = FakeRequest(cookies=None)
    reset_link = "http://testserver/reset-password?token=fake_token"
    data = ForgetPasswordRequest(email="user@example.com")

    # Act
    result = await reset_password(fake_background_tasks, data, request)

    # Assert
    assert result == {"message": "Message sent to RabbitMQ"}

    mock_create_reset_password_token.assert_called_once_with("user@example.com")
    fake_background_tasks.add_task.assert_called_once()
    _, args,_ = fake_background_tasks.add_task.mock_calls[0]

    assert args[0] is mock_publish_message
    assert args[1] is request.app

    message = json.loads(args[2])

    assert message["email"] == "user@example.com"
    assert message["token"] == "fake_token"
    assert message["subject"] == "Reset your password"
    assert message["subject"] == "Reset your password"
    assert message["body"] == f"Click the link to reset your password: {reset_link}"
    assert message["datetime"] == "2026-04-28T12:00:00+00:00"


@pytest.mark.asyncio
@patch("src.user_management_api.services.auth.publish_message")
@patch("src.user_management_api.services.auth.create_reset_password_token")
async def test_reset_password_create_reset_password_token_fail(
        mock_create_reset_password_token,
        mock_publish_message,
        fake_background_tasks,
        freezer_time
):
    """
    reset_password() should raise Exception when token generation fails.
    """
    # Arrange
    mock_create_reset_password_token.return_value = Exception()
    request = FakeRequest(cookies=None)
    data = ForgetPasswordRequest(email="user@example.com")

    # Act
    with pytest.raises(Exception):
        await reset_password(fake_background_tasks, data, request)

    # Assert
    mock_publish_message.assert_not_called()
    fake_background_tasks.add_task.assert_not_called()


# Tests for save_password()

@pytest.mark.asyncio
@patch("src.user_management_api.services.auth.decode_token")
@patch("src.user_management_api.services.auth.validate_reset_password_token")
@patch("src.user_management_api.services.auth.get_password_hash")
@patch("src.user_management_api.services.auth.verify_password")
@patch("src.user_management_api.services.auth.UserDAO.find_one_or_none")
@patch("src.user_management_api.services.auth.UserDAO.patch_by_id")
async def test_save_password_success(
        mock_patch_user,
        mock_find_user,
        mock_verify_password,
        mock_get_password_hash,
        mock_validate_reset_password_token,
        mock_decode_token,
        mock_db,
        reset_password_payload,
        reset_password_request

):
    """
    save_password() should update user password when reset token is valid.
    """
    # Arrange
    mock_decode_token.return_value = reset_password_payload
    data = reset_password_request

    mock_validate_reset_password_token.return_value = None
    mock_get_password_hash.return_value = "new_password_hash"
    mock_verify_password.return_value = False

    fake_user = type("User", (), {"id": "123", "name": "name", "surname": "surname","password": "old_hash"})
    mock_find_user.return_value = fake_user

    # Act
    result = await save_password(data, mock_db)

    # Assert
    assert result == {"message": "Password was changed successfully"}

    mock_decode_token.assert_called_once_with("fake_token")
    mock_validate_reset_password_token.assert_called_once()

    assert mock_find_user.call_count == 1
    calls = mock_find_user.call_args_list

    for call in calls:
        args, kwargs = call
        assert args[0] is mock_db
        assert isinstance(args[1], BinaryExpression)

    mock_verify_password.assert_called_once_with(data.new_password, fake_user.password)
    mock_get_password_hash.assert_called_once_with(data.new_password)

    mock_patch_user.assert_called_once()
    patch_args, patch_kwargs = mock_patch_user.call_args

    assert patch_args[0] is mock_db
    assert patch_args[1] == "123"
    assert patch_args[2] == {"password": "new_password_hash"}
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
@patch("src.user_management_api.services.auth.decode_token")
@patch("src.user_management_api.services.auth.validate_reset_password_token")
@patch("src.user_management_api.services.auth.get_password_hash")
@patch("src.user_management_api.services.auth.verify_password")
@patch("src.user_management_api.services.auth.UserDAO.find_one_or_none")
@patch("src.user_management_api.services.auth.UserDAO.patch_by_id")
async def test_save_password_old_password(
        mock_patch_user,
        mock_find_user,
        mock_verify_password,
        mock_get_password_hash,
        mock_validate_reset_password_token,
        mock_decode_token,
        mock_db,
        reset_password_payload,
        reset_password_request

):
    """
    save_password() should raise APIException when updating password fails.
    """
    mock_decode_token.return_value = reset_password_payload
    data = reset_password_request

    mock_validate_reset_password_token.return_value = None
    mock_get_password_hash.return_value = "new_password_hash"

    fake_user = type("User", (), {"id": "123", "name": "name", "surname": "surname","password": "old_hash"})
    mock_find_user.return_value = fake_user
    mock_verify_password.return_value = False

    mock_patch_user.side_effect = APIException()

    # Act
    with pytest.raises(APIException) as e:
        await save_password(data, mock_db)

    # Assert
    assert e.value.detail == "Failed to update password."

    mock_decode_token.assert_called_once_with("fake_token")
    mock_validate_reset_password_token.assert_called_once()

    mock_find_user.assert_called_once()
    args, kwargs = mock_find_user.call_args
    assert args[0] is mock_db
    assert isinstance(args[1], BinaryExpression)

    mock_verify_password.assert_called_once_with(data.new_password, fake_user.password)
    mock_get_password_hash.assert_called_once_with(data.new_password)
    mock_db.commit.assert_not_awaited()


@pytest.mark.asyncio
@patch("src.user_management_api.services.auth.decode_token")
@patch("src.user_management_api.services.auth.validate_reset_password_token")
@patch("src.user_management_api.services.auth.get_password_hash")
@patch("src.user_management_api.services.auth.verify_password")
@patch("src.user_management_api.services.auth.UserDAO.find_one_or_none")
@patch("src.user_management_api.services.auth.UserDAO.patch_by_id")
async def test_save_password_verify_password_fail(
        mock_patch_user,
        mock_find_user,
        mock_verify_password,
        mock_get_password_hash,
        mock_validate_reset_password_token,
        mock_decode_token,
        mock_db,
        reset_password_payload,
        reset_password_request
):
    """
    save_password() should return a warning message when the new password matches the old one.
    """
    # Arrange
    mock_decode_token.return_value = reset_password_payload
    data = reset_password_request

    mock_validate_reset_password_token.return_value = None
    mock_get_password_hash.return_value = "new_password_hash"

    fake_user = type("User", (), {"id": "123", "name": "name", "surname": "surname","password": "old_hash"})
    mock_find_user.return_value = fake_user

    mock_verify_password.return_value = True

    # Act
    result = await save_password(data, mock_db)

    # Assert
    assert result == {"message": "Don't use the old password."}

    mock_decode_token.assert_called_once_with("fake_token")
    mock_validate_reset_password_token.assert_called_once()

    mock_find_user.assert_called_once()
    args, kwargs = mock_find_user.call_args
    assert args[0] is mock_db
    assert isinstance(args[1], BinaryExpression)

    mock_verify_password.assert_called_once_with(data.new_password, fake_user.password)
    mock_get_password_hash.assert_called_once_with(data.new_password)
    mock_db.commit.assert_not_awaited()


@pytest.mark.asyncio
@patch("src.user_management_api.services.auth.decode_token")
@patch("src.user_management_api.services.auth.validate_reset_password_token")
@patch("src.user_management_api.services.auth.get_password_hash")
@patch("src.user_management_api.services.auth.verify_password")
@patch("src.user_management_api.services.auth.UserDAO.find_one_or_none")
async def test_save_password_verify_not_user(
        mock_find_user,
        mock_verify_password,
        mock_get_password_hash,
        mock_validate_reset_password_token,
        mock_decode_token,
        mock_db,
        reset_password_payload,
        reset_password_request
):
    """
    save_password() should raise ResourceNotFound when the user does not exist in the database.
    """
    # Arrange
    mock_decode_token.return_value = reset_password_payload
    data = reset_password_request

    mock_validate_reset_password_token.return_value = None
    mock_get_password_hash.return_value = "new_password_hash"

    mock_find_user.return_value = None

    # Act
    with pytest.raises(ResourceNotFound) as e:
        await save_password(data, mock_db)

    # Assert
    assert e.value.detail == "User is not found"

    mock_decode_token.assert_called_once_with("fake_token")
    mock_validate_reset_password_token.assert_called_once()

    mock_find_user.assert_called_once()