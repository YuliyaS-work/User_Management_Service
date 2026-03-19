"""
Application security.

Defines functions for password hashing, password verification
and generating access and refresh tokens.
"""
import os

from pwdlib import PasswordHash
from jose import jwt
from datetime import datetime, timedelta, timezone


pwd = PasswordHash.recommended()


def get_password_hash(password: str) -> str:
    """
    Return password hash.
    """
    return pwd.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify that the provided password matches the hashed password.
    """
    return pwd.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    """
    Create a JWT access token using the PRIVATE_KEY.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=10)
    to_encode.update({"exp": expire, "type": "access"})
    encode_jwt = jwt.encode(to_encode, os.getenv("SECRET_KEY"), algorithm=os.getenv("ALGORITHM"))
    return encode_jwt

def create_refresh_token(data: dict) -> str:
    """
    Create a JWT refresh token using the PRIVATE_KEY.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=30)
    to_encode.update({"exp": expire, "type": "refresh"})
    encode_jwt = jwt.encode(to_encode, os.getenv("SECRET_KEY"), algorithm=os.getenv("ALGORITHM"))
    return encode_jwt