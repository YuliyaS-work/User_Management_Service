"""
Application security.

Defines functions for password hashing, password verification
and generating access and refresh tokens.
"""
from pwdlib import PasswordHash
from jose import jwt
from datetime import datetime, timedelta, timezone

from .config import Settings


def get_auth_data():
    return {"secret_key": Settings.SECRET_KEY, "algorithm": Settings.ALGORITHM}

pwd = PasswordHash.recommended()

def get_password_hash(password: str) -> str:
    return pwd.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=10)
    to_encode.update({"exp": expire, "type": "access"})
    auth_data = get_auth_data()
    encode_jwt = jwt.encode(to_encode, auth_data["secret_key"], algorithm=auth_data["algorithm"])
    return encode_jwt

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=30)
    to_encode.update({"exp": expire, "type": "refresh"})
    auth_data = get_auth_data()
    encode_jwt = jwt.encode(to_encode, auth_data["secret_key"], algorithm=auth_data["algorithm"])
    return encode_jwt



