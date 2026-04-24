"""
Global handler for all custom API exceptions.

Converts APIException instances into consistent JSON error responses
with the appropriate HTTP status code and messages.
"""
import logging
import traceback

from fastapi import Request
from fastapi.responses import JSONResponse

from src.user_management_api.exceptions.auth import APIException
from src.user_management_api.schemas.auth import APIErrorResponse


logger = logging.getLogger(__name__)

async def api_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handles all APIException errors and returns a unified JSON response.
    """
    if isinstance(exc, APIException):
        logger.warning("APIException: status=%s | %s | path=%s", exc.status_code, exc.detail, request.url.path)
        return JSONResponse(
            status_code=exc.status_code,
            content=APIErrorResponse.from_exception(exc).model_dump()
        )

    logger.exception("Unhandled exception at %s | %s: %s, %s",
                     request.url.path,
                     type(exc).__name__, str(exc),
                     traceback.format_exc()
                     )

    return JSONResponse(
            status_code=500,
            content={
                "error_name": type(exc).__name__,
                "error_message": str(exc),
                "trace": traceback.format_exc()
            }
        )
