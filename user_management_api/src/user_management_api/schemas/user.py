"""
Pydentic model used for getting user information.
Provides validation are used for incoming data.
"""
import uuid
from datetime import datetime
from typing import Any
from uuid import UUID

import phonenumbers
from pydantic import BaseModel, field_validator, Field, field_serializer, EmailStr, model_validator
from fastapi_filter.contrib.sqlalchemy import Filter
from fastapi_pagination import Params

from src.user_management_api.models import User
from src.user_management_api.validators.auth import validate_phone_number_signup
from src.user_management_api.validators.user import serialize_phone, serialize_uuid


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


class ProfileUserPatch(BaseModel):
    """
    Schema for patching the profile information.
    """
    name: str | None = Field(default=None, min_length=2, max_length=50, description="Name must be between 2 and 50 characters long.")
    surname: str | None = Field(default=None, min_length=2, max_length=50, description="Surname must be between 2 and 50 characters long.")
    username: str | None = Field(default=None, min_length=5, max_length=20, description="Username must be between 5 and 20 characters long.")
    phone_number: str | None = Field(default=None, description="Phone number in international format starting with '+'")
    email: EmailStr | None = Field(default=None, description="Email")

    @field_validator("phone_number")
    def validate_phone_number_reg(cls, value: str | None) -> str | None:
        """
        Validate provided phone number.
        """
        return validate_phone_number_signup(value)

    @model_validator(mode="after")
    def ensure_not_empty_data(self) -> "ProfileUserPatch":
        if not self.model_dump(exclude_unset=True):
            raise ValueError("At least one field must be provided for update.")
        return self

class UserPatchByAdmin(ProfileUserPatch):
    """
    Schema for patching the user profile information by admin.
    """
    is_blocked: bool | None = Field(default=None, description="Block or unblock a user.")
    group_id: int | None = Field(default=None, description="Assign a user to a group")
    roles_id: list[int] | None = Field(default=None, description="List of user role Ids.")

    @field_validator("roles_id")
    def validate_roles_id_list(cls, value: list[str]) -> list[str]:
        if value is not None and len(value) == 0:
            raise ValueError("Roles_id cannot be an empty list.")
        return value

class GroupResponse(BaseModel):
    """
    Schema for the group entity.
    """
    id: int
    group_name: str


class RoleResponse(BaseModel):
    """
    Schema for the role entity.
    """
    id: int
    role_name: str


class UserResponse(BaseModel):
    """
    Schema for getting user profile data.
    """
    id: UUID
    name: str
    surname: str
    username: str
    phone_number: Any | None
    email: str
    is_blocked: bool
    created_at: datetime
    modified_at: datetime
    group: GroupResponse | None
    roles: list[RoleResponse]

    @field_serializer("phone_number")
    def serialize_phone_number(self: Any, value: str | phonenumbers.PhoneNumber | None) -> str | None:
        return serialize_phone(self, value)

    @field_serializer("id")
    def serialize_user_id(self: Any, value: uuid.UUID) -> str:
        return serialize_uuid(self, value)


class UserPagination(Params):
    """
    Schema for pagination.
    """
    page: int = 1
    size: int = 30

    @property
    def limit(self) -> int:
        return self.size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


class UserFilter(Filter):
    """
    Schema for filter and sort a list of user information.
    """
    name: str | None = None
    surname: str | None = None

    sort_field: str | None = None
    order_by: str | None = None

    class Constants(Filter.Constants):
        model = User
        ordering_field_name: list[str] = ["name", "surname"]