"""
Application security.

Defines functions for password hashing, password verification
and generating access and refresh tokens.
"""
import hashlib
import uuid
from typing import Any

from fastapi import HTTPException, status, Response
from pwdlib import PasswordHash
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone

from src.user_management_api.core.config import settings, r
from src.user_management_api.exceptions.auth import AuthenticationException
from src.user_management_api.schemas.auth import PayLoad

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

def get_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def create_access_token(data: dict[str, Any]) -> str:
    """
    Create a JWT access token using a secret_key and an algorithm.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=10)
    to_encode.update({"exp": expire, "type": "access"})
    encode_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encode_jwt

def create_refresh_token(data: dict[str, Any]) -> tuple[str, str]:
    """
    Create a JWT refresh token using a secret_key and an algorithm.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=30)
    jti = str(uuid.uuid4())
    to_encode.update({"exp": expire, "type": "refresh", "jti": jti})
    encode_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encode_jwt, jti


def decode_token(token: str) -> PayLoad | None:
    """
        Decode a JWT refresh token using a secret_key and an algorithm.
    """
    try:
        payload_decoded = jwt.decode(token, settings.secret_key, settings.algorithm)
        payload = PayLoad(**payload_decoded)
        return payload
    except JWTError:
        return None


def validate_access_token(payload: PayLoad | None) -> str:
    """
    Validate provided JWT access token.
    """
    if not payload:
        raise AuthenticationException(detail="Token invalid")

    # Check expire time  for access token.
    expire = payload.get('exp')
    expire_time = datetime.fromtimestamp(int(expire), tz=timezone.utc)
    if (not expire) or (expire_time < datetime.now(timezone.utc)):
        raise AuthenticationException(detail="Token is over")

    # Check ID user to ensure that it's authentic
    user_id = payload.get('sub')
    if not user_id:
        raise AuthenticationException(detail="User ID not found")

    return user_id


async def validate_refresh_token( payload: PayLoad | None, hash_token: str) -> tuple[str, str]:
    """
    Validate provided JWT refresh token.
    """
    if not payload:
        raise AuthenticationException(detail="Token invalid")

    jti = payload.get("jti")
    expire = payload.get('exp')
    user_id = payload.get('sub')
    saved_hash = await r.get(f"refresh_token:{user_id}:{jti}")

    # Check expire time  for refresh token.
    expire_time = datetime.fromtimestamp(int(expire), tz=timezone.utc)
    if (not expire) or (expire_time < datetime.now(timezone.utc)):
        raise AuthenticationException(detail="Token is over")

    # Check ID user to ensure that it's authentic
    if not user_id:
        raise AuthenticationException(detail="User ID not found")

    # Check refresh token in blacklist.
    if await r.get(f"revoked_token:{jti}"):
        raise AuthenticationException(detail="Token has been revoked")

    # Check hash of a provided refresh token with hash in redis.
    if hash_token != saved_hash:
        raise AuthenticationException(detail="Token is not current")

    return user_id, jti
