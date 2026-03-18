import re

from pydantic import EmailStr
from pydantic_core import PydanticCustomError


def validate_email(value: EmailStr) -> EmailStr:
    # check input befor EmailStr
    if value:
        if "@" not in value or "." not in value:
            raise PydanticCustomError(
                'email.invalid',
                'Email is invalid. Please, check the format.'
            )
    return value


def validate_phone_number(value: str) -> str | None:
    if value:
        if not re.match(r'^\+\d{10,17}$', value):
            raise ValueError("Phone number must start with '+'  and contain between 10 and 17 digits")
    return value

def validate_password(value: str) -> str:
    ...

