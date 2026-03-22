from fastapi import HTTPException, status, Response, Request

from src.user_management_api.core.config import r


def get_access_token_from_cookie(request: Request) -> str:
    access_token = request.cookies.get("user_access_token")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token not found"
        )
    return access_token

def get_refresh_token_from_cookie(request: Request) -> str:
    refresh_token = request.cookies.get("user_refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found"
        )
    return refresh_token


def send_tokens_to_user(response: Response, access_token: str, refresh_token: str) -> None:
    """
    Send a couple of JWT tokens to a user and refresh token to redis.
    """
    response.set_cookie(
        key="user_access_token",
        value=access_token,
        httponly=True,
        secure=True
    )
    response.set_cookie(
        key="user_refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True
    )


def delete_tokens_from_cookies(response):
    response.delete_cookie(
        key="user_access_token",
        httponly=True,
        secure=True
    )
    response.delete_cookie(
        key="user_refresh_token",
        httponly=True,
        secure=True
    )

def delete_refresh_token_from_redis(user_id: str, jti: str) -> None:
    r.delete(f"refresh_token:{user_id}", None)
    r.set(f"revoked_token::{jti}")


def save_refresh_token_to_redis(refresh_token, user_id) -> str:
        return r.set(f"refresh_token:{user_id}", f"{refresh_token}")