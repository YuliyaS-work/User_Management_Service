"""
Pydentic model used for user authentication, including sign-up and login.
Provides validation are used for incoming authentication data.
"""
import re

from pydantic import BaseModel, EmailStr, Field, field_validator
from pydantic_core import PydanticCustomError

class UserRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=50, description="Имя, от 2 до 50 символов")
    surname: str = Field(..., min_length=2, max_length=50, description="Фамилия, от 2 до 50 символов")
    username: str = Field(..., min_length=5, max_length=20, description="Никнейм, от 5 до 20 символов")
    password: str = Field(..., min_length=8, max_length=64, description="Имя, от 8 до 64 символов")
    phone_number: str | None = Field(..., description="Номер телефона в международном формате, начинающийся с '+'")
    email: EmailStr = Field(..., description="Электронная почта")

    @field_validator("email", mode="before")
    def validate_email(cls, value: EmailStr) -> EmailStr:
        # check input befor EmailStr
        if "@" not in value or "." not in value:
            raise PydanticCustomError(
                'email.invalid',
                'Email введён некорректно.Пожалуйста, проверьте формат.'
            )
        return value

    @field_validator("phone_number")
    def validate_phone_number(cls, value: str) -> str | None:
        if value:
            if not re.match(r'^\+\d{10,17}$', value):
                raise ValueError("Номер телефона должен начинаться с '+'  и содержать от 10 до 17 цифр")
        return value




