"""
Validators model used for pydantic models.
Provides validation are used for incoming data.
"""

import re

import phonenumbers
from phonenumbers.phonenumberutil import NumberParseException
from pydantic_core import PydanticCustomError


def validate_phone_number_signup(value: str | None) -> str | None:
    """
    Validate a phone number to an international standart form in signup.
    """
    if value is None or value.strip() == "":
        return None

    try:
        parsed_phone = phonenumbers.parse(value, None)
        if not phonenumbers.is_valid_number(parsed_phone):
            raise ValueError("Invalid phone number")
        return phonenumbers.format_number(parsed_phone, phonenumbers.PhoneNumberFormat.E164)
    except NumberParseException:
        raise ValueError("Invalid phone number format")



def validate_password(value: str) -> str:
    """
    Validate a password.

    Password must contain at least one digit, special character,
    uppercase letter, lowercase letter.
    The length of password must be between 8 and 64 characters.
    """
    if value:
        if len(value) < 8:
            raise PydanticCustomError(
                "password_too_short",
                "Password must contain 8 characters and more."
            )

        if not re.search(r"[A-Z]", value):
            raise PydanticCustomError(
                "password_no_uppercase",
                "Password must contain at least one uppercase letter."
            )

        if not re.search(r"[a-z]", value):
            raise PydanticCustomError(
                "password_no_lowercase",
                "Password must contain at least one lowercase letter."
            )

        if not re.search(r"[\d]", value):
            raise PydanticCustomError(
                "password_no_digit",
                "Password must contain at least one digit."
            )

        if not re.search(r"[!@#$%^&]", value):
            raise PydanticCustomError(
                "password_no_special_character",
                "Password must contain at least one special character."
            )

    return value