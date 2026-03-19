import re

from pydantic_core import PydanticCustomError


def validate_phone_number(value: str) -> str | None:
    """
    Validate a phone number to an international standart form.
    """
    if value:
        if not re.match(r'^\+\d{10,17}$', value):
            raise ValueError(
                "phone_number_invalid",
                "Phone number must start with '+'  and contain between 10 and 17 digits."
            )
    return value


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