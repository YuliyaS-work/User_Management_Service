from fastapi import Response, Request

from src.user_management_api.core.config import settings
from src.user_management_api.exceptions.auth import AuthenticationException


def get_access_token_from_cookie(request: Request) -> str:
    """
    Get access token from cookies.
    """
    access_token = request.cookies.get("access_token")
    if not access_token:
        raise AuthenticationException(detail="Access token not found")
    return access_token


def get_refresh_token_from_cookie(request: Request) -> str:
    """
    Get refresh token from cookies.
    """
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise AuthenticationException(detail="Refresh token not found")
    return refresh_token


def send_tokens_to_user(response: Response, access_token: str, refresh_token: str) -> None:
    """
    Send a couple of JWT tokens to a user and refresh token to redis.
    """
    response.set_cookie(
        key="access_token",
        value=access_token,
        path="/",
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=600
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        path="/",
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=30*24*60*60
    )


def delete_tokens_from_cookies(response: Response) -> None:
    """
    Delete tokens from cookies.
    """
    response.delete_cookie(
        key="access_token",
        path="/",
        httponly=True,
        secure=settings.is_production,
        samesite="lax"
    )
    response.delete_cookie(
        key="refresh_token",
        path="/",
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
    )