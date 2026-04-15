"""
Global handler for all custom API exceptions.

Converts APIException instances into consistent JSON error responses
with the appropriate HTTP status code and messages.
"""

from fastapi import Request
from fastapi.responses import JSONResponse

from src.user_management_api.exceptions.auth import APIException
from src.user_management_api.schemas.auth import APIErrorResponse


async def api_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handles all APIException errors and returns a unified JSON response.
    """
    if isinstance(exc, APIException):
        return JSONResponse(
            status_code=exc.status_code,
            content=APIErrorResponse.from_exception(exc).model_dump()
        )
    raise exc