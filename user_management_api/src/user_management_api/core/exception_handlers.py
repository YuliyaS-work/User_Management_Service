"""
Global handler for all custom API exceptions.

Converts APIException instances into consistent JSON error responses
with the appropriate HTTP status code and messages.
"""

from fastapi import Request
from fastapi.responses import JSONResponse

from src.user_management_api.exceptions.auth import APIException
from src.user_management_api.main import app
from src.user_management_api.schemas.auth import ErrorResponse


@app.exception_handler(APIException)
async def token_from_cookies_handler(request: Request, exc: APIException):
    """
    Handles all APIException errors and returns a unified JSON response.
    """
    return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse( detail=exc.detail).model_dump()
        )