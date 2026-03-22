"""
Application security.

Defines functions for password hashing, password verification
and generating access and refresh tokens.
"""
from fastapi import HTTPException, status, Response
from pwdlib import PasswordHash
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone

from src.user_management_api.core.config import settings, r
from src.user_management_api.utils.auth import delete_tokens_from_cookies

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
    encode_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encode_jwt

def create_refresh_token(data: dict) -> str:
    """
    Create a JWT refresh token using the PRIVATE_KEY.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=30)
    to_encode.update({"exp": expire, "type": "refresh"})
    encode_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encode_jwt


def decode_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.secret_key, settings.algorithm)
        return payload
    except JWTError:
        return None


def validate_token(response: Response, payload: dict) -> str:
    if not payload:
        delete_tokens_from_cookies(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalid")

    expire = payload.get('exp')
    expire_time = datetime.fromtimestamp(int(expire), tz=timezone.utc)
    if (not expire) or (expire_time < datetime.now(timezone.utc)):
        delete_tokens_from_cookies(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token is over")

    user_id = payload.get('sub')
    if not user_id:
        delete_tokens_from_cookies(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not found")

    jti = payload.get("jti")
    if r.get(f"revoked_token::{jti}"):
        delete_tokens_from_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked"
        )
    return user_id
