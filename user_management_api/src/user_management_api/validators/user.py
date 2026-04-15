"""
Validators model used for pydantic models.
Provides validation are used for incoming data.
"""
import uuid
from typing import Any

import phonenumbers


def serialize_phone(self: Any, value: str | phonenumbers.PhoneNumber | None) -> str | None:
    """
    Serialize phone number from the database or redis.
    """
    if value is None:
        return None

    if isinstance(value, str):
        return value

    return phonenumbers.format_number(value, phonenumbers.PhoneNumberFormat.E164)


def serialize_uuid(self: Any, value: uuid.UUID) -> str:
    """
    Serialize the user ID from redis.
    """
    return str(value)