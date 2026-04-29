import pytest

from src.user_management_api.exceptions.auth import AuthenticationException
from src.user_management_api.utils.auth import get_access_token_from_cookie, get_refresh_token_from_cookie


def test_get_access_token_from_cookie_success(get_fake_request):
    access_token = get_access_token_from_cookie(get_fake_request)

    assert access_token == get_fake_request.cookies.get("access_token")

def test_get_access_token_from_cookie_fail(fake_request):
    fake_request.cookies.get.return_value = None
    with pytest.raises(AuthenticationException) as e:
        get_access_token_from_cookie(fake_request)

    assert e.value.detail == "Access token not found"


def test_get_refresh_token_from_cookie_success(get_fake_request):
    refresh_token = get_refresh_token_from_cookie(get_fake_request)

    assert refresh_token == get_fake_request.cookies.get("refresh_token")

def test_get_refresh_token_from_cookie_fail(fake_request):
    fake_request.cookies.get.return_value = None
    with pytest.raises(AuthenticationException) as e:
        get_refresh_token_from_cookie(fake_request)

    assert e.value.detail == "Refresh token not found"
