from fastapi import Response, Request, Header

from src.user_management_api.exceptions.auth import AuthenticationException


# def get_access_token_from_header(authorization: str = Header(None)) -> str:
#     if not authorization:
#         raise AuthenticationException("Missing authorization header.")
#
#     try:
#         scheme, access_token = authorization.split()
#     except ValueError:
#         raise AuthenticationException("Invalid authorization header format.")
#
#     if scheme.lower() != "bearer":
#         raise AuthenticationException("Invalid auth scheme")
#
#     return access_token


def get_access_token_from_cookie(request: Request) -> str:
    """
    Get access token from cookies.
    """
    access_token = request.cookies.get("user_access_token")
    if not access_token:
        raise AuthenticationException(detail="Access token not found")
    return access_token


def get_refresh_token_from_cookie(request: Request) -> str:
    """
    Get refresh token from cookies.
    """
    refresh_token = request.cookies.get("user_refresh_token")
    if not refresh_token:
        raise AuthenticationException(detail="Refresh token not found")
    return refresh_token


def send_tokens_to_user(response: Response, access_token: str, refresh_token: str) -> None:
    """
    Send a couple of JWT tokens to a user and refresh token to redis.
    """
    response.set_cookie(
        key="user_access_token",
        value=access_token,
        path="/",
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=600
    )
    response.set_cookie(
        key="user_refresh_token",
        value=refresh_token,
        path="/",
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=30*24*60*60
    )


def delete_tokens_from_cookies(response: Response) -> None:
    """
    Delete tokens from cookies.
    """
    response.delete_cookie(
        key="user_access_token",
        path="/",
        httponly=True,
        secure=True,
        samesite="lax"
    )
    response.delete_cookie(
        key="user_refresh_token",
        path="/",
        httponly=True,
        secure=True,
        samesite="lax",
    )