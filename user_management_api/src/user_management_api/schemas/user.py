"""
Pydentic model used for getting user information.
Provides validation are used for incoming data.
"""
from datetime import datetime
from typing import Any
from uuid import UUID

import phonenumbers
from pydantic import BaseModel, field_validator, ConfigDict, field_serializer

from src.user_management_api.validators.auth import validate_phone_number_signup
from src.user_management_api.validators.user import serialize_phone


class ProfileUserGet(BaseModel):
    """
    Schema for getting the profile information.
    """
    model_config = ConfigDict(from_attributes=True)

    name: str
    surname: str
    username: str
    phone_number: Any | None
    email: str
    group_name: str

    @field_serializer("phone_number")
    def serialize_phone_number(self, value):
        return serialize_phone(self, value)


class ProfileUserPatch(BaseModel):
    """
    Schema for patching the profile information.
    """
    name: str | None = None
    surname: str | None = None
    username: str | None = None
    phone_number: str | None = None
    email: str | None = None

    @field_validator("phone_number")
    def validate_phone_number_reg(cls, value: str | None) -> str | None:
        """
        Validate provided phone number.
        """
        return validate_phone_number_signup(value)

class ProfileUserResponse(BaseModel):
    """
    Schema for patching the profile information.
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    surname: str
    username: str
    phone_number: Any | None
    email: str
    image_s3_path: str | None
    is_blocked: bool
    created_at: datetime
    modified_at: datetime
    group_id: int | None

    @field_serializer("phone_number")
    def serialize_phone_number(self, value):
        return serialize_phone(self, value)


class PresignUrlGet(BaseModel):
    """
    Schema for getting the presign url from redis to an avatar usage.
    """
    presigned_url: str


class PresignedPostResponse(BaseModel):
    """
    Schema for presign post.
    """
    key: str
    url: str
    fields: dict[str, str]


class ConfirmAvatarRequest(BaseModel):
    """
    Schema for getting avatar url after confirm new avatar.
    """
    key: str


class UserResponse(BaseModel):
    name: str
    surname: str
    username: str
    phone_number: Any | None
    email: str
    is_blocked: bool
    created_at: datetime
    modified_at: datetime
    group_name: str | None
    role: list | str

    @field_serializer("phone_number")
    def serialize_phone_number(self, value):
        return serialize_phone(self, value)