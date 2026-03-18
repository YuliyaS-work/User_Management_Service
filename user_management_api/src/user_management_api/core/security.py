"""
Application security.

Defines functions for password hashing, password verification
and generating access and refresh tokens.
"""
import os
from pathlib import Path

from pwdlib import PasswordHash
from jose import jwt
from datetime import datetime, timedelta, timezone

from .config import Settings

pwd = PasswordHash.recommended()

def get_password_hash(password: str) -> str:
    return pwd.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd.verify(plain_password, hashed_password)

PUBLIC_KEY = Path(Settings.PUBLIC_KEY_PATH).read_text()
PRIVATE_KEY = Path(Settings.PRIVATE_KEY_PATH).read_text()

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=10)
    to_encode.update({"exp": expire, "type": "access"})
    encode_jwt = jwt.encode(to_encode, PRIVATE_KEY, algorithm=os.getenv("ALGORITHM"))
    return encode_jwt

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=30)
    to_encode.update({"exp": expire, "type": "refresh"})
    encode_jwt = jwt.encode(to_encode, PRIVATE_KEY, algorithm=os.getenv("ALGORITHM"))
    return encode_jwt