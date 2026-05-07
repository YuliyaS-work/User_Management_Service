"""
Pydantic model used for user authentication, including sign-up and login.
Provides validation are used for incoming and outgoing authentication data.
"""
from typing import Self, Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from src.user_management_api.exceptions.auth import APIException
from src.user_management_api.validators.auth import validate_phone_number_signup, validate_password


class UserRegister(BaseModel):
    """
    Schema for registration a new user.
    """
    name: str = Field(..., min_length=2, max_length=50, description="Name must be between 2 and 50 characters long.")
    surname: str = Field(..., min_length=2, max_length=50, description="Surname must be between 2 and 50 characters long.")
    username: str = Field(..., min_length=5, max_length=20, description="Username must be between 5 and 20 characters long.")
    password: str = Field(..., min_length=8, max_length=64, description="Password must be between 8 and 20 characters long.")
    phone_number: str | None = Field(..., description="Phone number in international format starting with '+'")
    email: EmailStr = Field(..., description="Email")

    @field_validator("phone_number")
    def validate_phone_number_reg(cls, value: str | None) -> str | None:
        """
        Validate provided phone number.
        """
        return validate_phone_number_signup(value)

    @field_validator("password")
    def validate_password_reg(cls, value: str) -> str:
        """
        Validate provided password.
        """
        return validate_password(value)


class UserLogin(BaseModel):
    """
    Schema for login a user.
    """
    login: str = Field(..., description="Login may be username, phone number or email")
    password: str = Field(..., min_length=8, max_length=64, description="Password must be between 8 and 20 characters long.")


class TokenResponse(BaseModel):
    """
    Schema for token response.
    """
    access_token: str
    refresh_token: str


class PayloadTokenBase(BaseModel):
    """
    Schema for common token payload.
    """
    sub: str
    exp: int
    type: Literal["access", "refresh", "reset_password"]
    jti: str


class PayLoadAccessToken(PayloadTokenBase):
    """
    Schema for access token payload.
    """
    group_id: int | None
    roles: list[str]
    type: Literal["access"]


class PayLoadRefreshToken(PayloadTokenBase):
    """
    Schema for refresh token payload.
    """
    type: Literal["refresh"]


class PayLoadResetPasswordToken(PayloadTokenBase):
    """
    Schema for reset token token payload.
    """
    type: Literal["reset_password"]


class APIErrorResponse(BaseModel):
    """
    Schema for error response returned by the API.
    """
    status_code: int
    detail: str

    @classmethod
    def from_exception(cls, exc: APIException) -> Self:
        return cls(
            status_code=exc.status_code,
            detail=exc.detail
        )


class CurrentUser(BaseModel):
    """
    Schema for a user data from JWT access token.
    """
    user_id: str
    group_id: int | None
    roles: list[str]


class ForgetPasswordRequest(BaseModel):
    """
    Schema for sending to get reset password token.
    """
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """
    Schema for updating user password.
    """
    token: str
    new_password: str