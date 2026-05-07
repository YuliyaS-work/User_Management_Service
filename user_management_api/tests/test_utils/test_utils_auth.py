import pytest

from src.user_management_api.exceptions.auth import AuthenticationException
from src.user_management_api.utils.auth import get_access_token_from_cookie, get_refresh_token_from_cookie, \
    delete_tokens_from_cookies


def test_get_access_token_from_cookie_success(get_fake_request):
    """
    get_access_token_from_cookie() should return the access token
    when it exists in request cookies.
    """
    # Act
    access_token = get_access_token_from_cookie(get_fake_request)

    # Assert
    assert access_token == get_fake_request.cookies.get("access_token")


def test_get_access_token_from_cookie_fail(fake_request):
    """
    get_access_token_from_cookie() should raise AuthenticationException
    when access token is missing.
    """
    # Arrange
    fake_request.cookies.get.return_value = None

    # Act
    with pytest.raises(AuthenticationException) as e:
        get_access_token_from_cookie(fake_request)

    # Assert
    assert e.value.detail == "Access token not found"


def test_get_refresh_token_from_cookie_success(get_fake_request):
    """
    get_refresh_token_from_cookie() should return the refresh token
    when it exists in request cookies.
    """
    # Act
    refresh_token = get_refresh_token_from_cookie(get_fake_request)

    # Assert
    assert refresh_token == get_fake_request.cookies.get("refresh_token")


def test_get_refresh_token_from_cookie_fail(fake_request):
    """
    get_refresh_token_from_cookie() should raise AuthenticationException
    when refresh token is missing.
    """
    # Arrange
    fake_request.cookies.get.return_value = None

    # Act
    with pytest.raises(AuthenticationException) as e:
        get_refresh_token_from_cookie(fake_request)

    # Assert
    assert e.value.detail == "Refresh token not found"


def test_delete_tokens_from_cookies(fake_response):
    """
    delete_tokens_from_cookies() should remove both access and refresh tokens
    from the response cookies.
    """
    # Act
    delete_tokens_from_cookies(fake_response)

    # Assert
    fake_response.delete_cookie.assert_any_call(
        key="access_token",
        path="/",
        httponly=True,
        secure=True,
        samesite="lax"
    )
    fake_response.delete_cookie.assert_any_call(
        key="refresh_token",
        path="/",
        httponly=True,
        secure=True,
        samesite="lax",
    )

    assert fake_response.delete_cookie.call_count == 2