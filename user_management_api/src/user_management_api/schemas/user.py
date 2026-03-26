"""
Pydentic model used for getting user information.
Provides validation are used for incoming data.
"""
from pydantic import BaseModel


class UserResponse(BaseModel):
    """
    Schema for getting the profile information.
    """
    name: str
    surname: str
    username: str
    phone_number: str
    email: str
    image: str | None
    group_name: str