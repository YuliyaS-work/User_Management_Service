from fastapi import HTTPException, status, Response, Request


def get_access_token_from_cookie(request: Request) -> str:
    """
    Get access token from cookies.
    """
    access_token = request.cookies.get("user_access_token")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token not found"
        )
    return access_token


def get_refresh_token_from_cookie(request: Request) -> str:
    """
    Get refresh token from cookies.
    """
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


def delete_tokens_from_cookies(response):
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