from datetime import datetime, timezone, timedelta
from typing import Any
from unittest.mock import patch, MagicMock

import pytest
from sqlalchemy import BinaryExpression, BooleanClauseList

from src.user_management_api.exceptions.auth import AuthenticationException, ConflictException
from src.user_management_api.exceptions.user import ResourceNotFound
from src.user_management_api.schemas.auth import UserRegister, UserLogin
from src.user_management_api.services.auth import get_current_user, create_and_store_tokens, verify_refresh_token, \
    register_user, login_user, logout_user


@patch("src.user_management_api.services.auth.validate_access_token")
@patch("src.user_management_api.services.auth.decode_token")
@patch("src.user_management_api.services.auth.get_access_token_from_cookie")
def test_get_current_user_success(
        mock_get_access_token_from_cookie,
        mock_decode_token,
        mock_validate_access_token,
        get_fake_request
):
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

    user = get_current_user(get_fake_request)

    assert user.user_id == "123"
    assert user.group_id == 1
    assert user.roles == ["USER"]

    mock_get_access_token_from_cookie.assert_called_once_with(get_fake_request)
    mock_decode_token.assert_called_once_with("fake_token")
    mock_validate_access_token.assert_called_once_with(mock_decode_token.return_value)




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
        mock_db
):
    user_id = "123"

    mock_user = MagicMock()
    mock_user.group_id = 1
    mock_role = MagicMock()
    mock_role.role_name.value = "USER"
    mock_user.roles = [mock_role]
    mock_find_user.return_value = mock_user

    mock_create_access_token.return_value = "fake_access_token"
    mock_create_refresh_token.return_value = ("fake_refresh_token", "fake_jti")
    mock_save_refresh_token_to_redis.return_value = None

    access_token, refresh_token = await create_and_store_tokens(user_id, mock_db)
    assert access_token == "fake_access_token"
    assert refresh_token == "fake_refresh_token"

    args, kwargs = mock_find_user.call_args
    assert args[0] is mock_db
    assert isinstance(args[1], BinaryExpression)

    mock_create_access_token.assert_called_once_with({"sub": user_id, "group_id": 1, "roles": ["USER"]})
    mock_create_refresh_token.assert_called_once_with({"sub": user_id})
    mock_save_refresh_token_to_redis.assert_called_once_with("fake_refresh_token", "fake_jti", user_id)


@pytest.mark.asyncio
@patch("src.user_management_api.services.auth.UserDAO.find_one_or_none_with_related_data")
async def test_create_and_store_tokens_user_not_found(
        mock_find_user,
        mock_db
):
    mock_find_user.return_value = None
    with pytest.raises(ResourceNotFound) as e:
        await create_and_store_tokens("123", mock_db)
        assert e.value.detail == "User is not found"
    mock_find_user.assert_called_once()


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
    mock_get_refresh_token_from_cookie.return_value = "fake_token"
    mock_decode_token.return_value = type("Payload", (), {
        "sub": "123",
        "exp": int((datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc) + timedelta(minutes=10)).timestamp()),
        "type": "refresh",
        "jti": "12345678123456781234567812345678"
    })()
    mock_get_token_hash.return_value = "fake_hash_token"
    mock_validate_refresh_token.return_value = ("123", "12345678123456781234567812345678")

    user_id, jti = await verify_refresh_token(get_fake_request)

    assert user_id == "123"
    assert jti == "12345678123456781234567812345678"

    mock_get_refresh_token_from_cookie.assert_called_once_with(get_fake_request)
    mock_decode_token.assert_called_once_with("fake_token")
    mock_validate_refresh_token.assert_called_once_with(mock_decode_token.return_value, mock_get_token_hash.return_value)


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
    mock_get_refresh_token_from_cookie.return_value = "fake_token"
    mock_decode_token.return_value = {"sub": "123"}
    mock_get_token_hash.return_value = "fake_hash_token"
    mock_validate_refresh_token.side_effect = AuthenticationException

    with pytest.raises(AuthenticationException) as e:
        await verify_refresh_token(get_fake_request)
        assert e.value.detail == "Invalid token type"
    mock_validate_refresh_token.assert_called_once()


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
        fake_response
):
    mock_find_user.return_value = None
    mock_get_password_hash.return_value = "fake_password_hash"

    mock_user = MagicMock()
    mock_user.id = "123"
    mock_add_user.return_value = mock_user

    mock_create_and_store_tokens.return_value = ("fake_access_token", "fake_refresh_token")

    user_data = UserRegister(
        name="name",
        surname="surname",
        username="username",
        password="Password1!",
        phone_number="+375291111111",
        email="user@example.com"
    )


    mock_send_token_to_user.return_value = None

    result = await register_user(fake_response, user_data, mock_db)

    assert mock_find_user.call_count == 3
    calls = mock_find_user.call_args_list

    for call in calls:
        args, kwargs = call
        assert args[0] is mock_db
        assert isinstance(args[1], BinaryExpression)


    mock_get_password_hash.assert_called_once_with(user_data.password)
    mock_add_user.assert_called_once()
    add_args, add_kwargs = mock_add_user.call_args

    assert add_args[0] is mock_db
    assert add_kwargs["name"] == user_data.name
    assert add_kwargs["surname"] == user_data.surname
    assert add_kwargs["username"] == user_data.username
    assert add_kwargs["email"] == user_data.email
    assert add_kwargs["password"] == "fake_password_hash"
    assert add_kwargs["phone_number"] == user_data.phone_number

    mock_create_and_store_tokens.assert_called_once_with("123",
                                                         mock_db)
    mock_send_token_to_user.assert_called_once_with(fake_response,"fake_access_token", "fake_refresh_token")

    assert result.access_token == "fake_access_token"
    assert result.refresh_token == "fake_refresh_token"



@pytest.mark.asyncio
@patch("src.user_management_api.services.auth.UserDAO.find_one_or_none")
async def test_register_user_username_conflict(
        mock_find_user,
        mock_db,
        fake_response
):
    mock_find_user.side_effect = [True]

    user_data = UserRegister(
        name="name",
        surname="surname",
        username="username",
        password="Password1!",
        phone_number="+375291111111",
        email="user@example.com"
    )

    with pytest.raises(ConflictException) as e:
        await register_user(fake_response, user_data, mock_db)
        assert e.value.detail == "Username already exists"

    mock_find_user.assert_called_once()


@pytest.mark.asyncio
@patch("src.user_management_api.services.auth.UserDAO.find_one_or_none")
async def test_register_user_username_conflict(
        mock_find_user,
        mock_db,
        fake_response
):
    mock_find_user.side_effect = [None, True]

    user_data = UserRegister(
        name="name",
        surname="surname",
        username="username",
        password="Password1!",
        phone_number="+375291111111",
        email="user@example.com"
    )

    with pytest.raises(ConflictException) as e:
        await register_user(fake_response, user_data, mock_db)
        assert e.value.detail == "Email already exists"

    assert mock_find_user.call_count == 2


@pytest.mark.asyncio
@patch("src.user_management_api.services.auth.UserDAO.find_one_or_none")
async def test_register_user_username_conflict(
        mock_find_user,
        mock_db,
        fake_response
):
    mock_find_user.side_effect = [None, None, True]

    user_data = UserRegister(
        name="name",
        surname="surname",
        username="username",
        password="Password1!",
        phone_number="+375291111111",
        email="user@example.com"
    )

    with pytest.raises(ConflictException) as e:
        await register_user(fake_response, user_data, mock_db)
        assert e.value.detail == "Phone number already exists"

    assert mock_find_user.call_count == 3


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
    mock_user = MagicMock()
    mock_user.id = "123"
    mock_user.username = "username"
    mock_user.password = "fake_password_hash"
    mock_find_user.return_value = mock_user

    mock_verify_password.return_value = True
    mock_create_and_store_tokens.return_value = ("fake_access_token", "fake_refresh_token")

    user_data = UserLogin(login="username", password="Password1!")

    result = await login_user(fake_request, fake_response, user_data, mock_db)

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

    result = await login_user(fake_request, fake_response, user_data, mock_db)

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

    mock_user = MagicMock()
    mock_user.id = "123"
    mock_user.password = "fake_password_hash"
    mock_find_user.return_value = mock_user

    mock_verify_password.return_value = True
    mock_create_and_store_tokens.return_value = ("fake_access_token", "fake_refresh_token")

    user_data = UserLogin(login="user@example.com", password="Password1!")

    result = await login_user(fake_request, fake_response, user_data, mock_db)

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
    mock_find_user.return_value = None

    user_data = UserLogin(login="unknown", password="Password1!")


    with pytest.raises(AuthenticationException) as e:
        await login_user(fake_request, fake_response, user_data, mock_db)
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
    mock_user = MagicMock()
    mock_user.username = "username"
    mock_user.password = "fake_password_hash"
    mock_find_user.return_value = mock_user

    mock_verify_password.return_value = False

    user_data = UserLogin(login="username", password="wrong_password")

    with pytest.raises(AuthenticationException):
        await login_user(fake_request, fake_response, user_data, mock_db)

    mock_verify_password.assert_called_once_with("wrong_password", "fake_password_hash")


@pytest.mark.asyncio
@patch("src.user_management_api.services.auth.UserDAO.find_one_or_none")
async def test_login_user_wrong_phonenumber(
        mock_find_user,
        mock_db,
        fake_response,
        fake_request
):
    mock_find_user.return_value = None

    user_data = UserLogin(login="wrong_phonenumber", password="Password1!")

    with pytest.raises(AuthenticationException) as e:
        await login_user(fake_request, fake_response, user_data, mock_db)
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
    mock_find_user.return_value = None

    user_data = UserLogin(login="wrong_email", password="Password1!")

    with pytest.raises(AuthenticationException) as e:
        await login_user(fake_request, fake_response, user_data, mock_db)
        assert e.value.detail == "User's not found."

    mock_find_user.assert_called_once()


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
    mock_verify_refresh_token.return_value = ("123", "fake_jti")

    result = await logout_user(fake_response, fake_request)

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
        mock_delete_refresh_token,
        mock_delete_tokens_from_cookies,
        fake_response,
        fake_request
):
    mock_verify_refresh_token.side_effect = AuthenticationException

    with pytest.raises(AuthenticationException):
        await logout_user(fake_response, fake_request)

    mock_verify_refresh_token.assert_called_once_with(fake_request)
    mock_delete_refresh_token.assert_not_called()
    mock_delete_tokens_from_cookies.assert_called_once_with(fake_response)