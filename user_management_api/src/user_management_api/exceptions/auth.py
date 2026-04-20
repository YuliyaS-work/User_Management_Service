"""
Custom exceptions classes used acsross the API.

The module provides typed error classes such as AuthenticationException(401),
and ConflictException (409), which are converted into standartized JSON
responses by global exception handlers.
"""
from fastapi import HTTPException


class APIException(HTTPException):
    """
    Base class for all API exceptions.
    """
    status_code: int = 500
    detail: str = "Internal server error"

    def __init__(self, detail: str | None = None ):
        super().__init__(
            status_code=self.status_code,
            detail = detail or self.detail
        )

class AuthenticationException(APIException):
    """
    Raised when a user is not authenticated or JWT tokens are invalid.
    """
    status_code: int = 401
    detail: str = "The user is not authenticated"


class ConflictException(APIException):
    """
    Raised when a request cannot be completed due to a resource conflict.
    """
    status_code: int = 409
    detail: str = "The user already exists"