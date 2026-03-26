from fastapi import status, Request
from fastapi.responses import JSONResponse

from src.user_management_api.exceptions.auth import AuthenticationException, ConflictException
from src.user_management_api.main import app


@app.exception_handler(AuthenticationException)
async def token_from_cookies_handler(request: Request, exc: AuthenticationException):
    return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail":exc.detail}
        )


@app.exception_handler(ConflictException)
async def token_from_cookies_handler(request: Request, exc: ConflictException):
    return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail":exc.detail}
        )