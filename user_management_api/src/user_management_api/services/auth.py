"""
Authentication module providing handlers for user authentication,
including sign-up, login, logout and token refresh operations.
"""

from datetime import timedelta

import phonenumbers
from fastapi import Response, Request
from phonenumbers.phonenumberutil import NumberParseException
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.user_management_api.core.security import get_password_hash, create_access_token, create_refresh_token, \
    verify_password, decode_token, validate_refresh_token, get_token_hash, validate_access_token
from src.user_management_api.exceptions.auth import ConflictException, APIException, AuthenticationException
from src.user_management_api.exceptions.user import ResourceNotFound
from src.user_management_api.models import User
from src.user_management_api.schemas.auth import UserRegister, UserLogin, TokenResponse, CurrentUser
from src.user_management_api.dao.user import UserDAO
from src.user_management_api.utils.auth import send_tokens_to_user, delete_tokens_from_cookies, \
    get_refresh_token_from_cookie, get_access_token_from_cookie
from src.user_management_api.core.config import r

def get_current_user(request: Request) -> CurrentUser:
    """
    Get a user ID from JWT access token.
    """
    access_token = get_access_token_from_cookie(request)
    payload = decode_token(access_token)
    validate_access_token(payload)
    current_user = CurrentUser(
        user_id=payload.sub,
        group_id=payload.group_id,
        roles=payload.roles
    )
    return current_user

async def create_and_store_tokens(user_id: str, db: AsyncSession) -> tuple[str, str]:
    """
    Create JWT tokens and put refresh token in redis.
    """
    user = await UserDAO.find_one_or_none_with_related_data(db, User.id == user_id)

    if user is None:
        raise ResourceNotFound("User is not found")

    roles = [role.role_name.value for role in user.roles]
    access_payload = {
        "sub": user_id,
        "group_id": user.group_id,
        "roles": roles
    }
    access_token = create_access_token(access_payload)
    refresh_token, jti = create_refresh_token({"sub": user_id})
    await save_refresh_token_to_redis(refresh_token, jti, user_id)
    return access_token, refresh_token


async def delete_refresh_token_from_redis(user_id: str, jti: str) -> None:
    """
    Delete refresh token hash and indicate jti of the refresh token is "revoked".
    """
    await r.delete(f"refresh_token:{user_id}")
    await r.set(f"revoked_token:{user_id}:{jti}", "true")


async def save_refresh_token_to_redis(refresh_token: str, jti: str, user_id: str) -> str:
    """
    Save refresh token hash to redis.
    """
    token_hash = get_token_hash(refresh_token)
    ttl = timedelta(days=30)
    refresh_token = await r.setex(f"refresh_token:{user_id}", int(ttl.total_seconds()), token_hash)
    return refresh_token


async def verify_refresh_token(request: Request) -> tuple[str, str]:
    """
    Verify refresh token from cookies to one stored in redis.
    """
    old_refresh_token = get_refresh_token_from_cookie(request)
    payload = decode_token(old_refresh_token)
    hash_token = get_token_hash(old_refresh_token)
    user_id, jti = await validate_refresh_token(payload, hash_token)
    return user_id, jti


async def register_user(response: Response, user_data: UserRegister, db: AsyncSession) -> TokenResponse:
    """
    Register a user and create a record in the database.

    Args:
        response (Response): save JWT tokens in cookies.
        user_data (UserRegister): Data required to create a new user in the database.
        db (AsyncSession): Database session.
    Returns:
        TokenResponse: An access and refresh tokens.
    """
     # Compare the data in login field with email, username and phone number in the database.
    if await UserDAO.find_one_or_none(db, User.username == user_data.username):
        raise ConflictException(detail="Username already exists")

    if await UserDAO.find_one_or_none(db, User.email == user_data.email):
        raise ConflictException(detail="Email already exists")

    if user_data.phone_number:
        if await UserDAO.find_one_or_none(db, User.phone_number == user_data.phone_number):
            raise ConflictException(detail="Phone number already exists")

    # Get a dictionary of instance.
    user_dict = user_data.model_dump()

    # Get password hash.
    user_dict["password"] = get_password_hash(user_data.password)

    # Add a user to the database.
    new_user = await UserDAO.add(db, **user_dict)
    await db.commit()

    # UUID to string for JSON serialization to get tokens.
    user_id = str(new_user.id)

    # Create tokens, set tokens in cookies and a refresh token in redis.
    access_token, refresh_token = await create_and_store_tokens( user_id, db)
    send_tokens_to_user(response, access_token, refresh_token)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )


async def login_user(request: Request, response: Response, user_data: UserLogin, db: AsyncSession) -> TokenResponse:
    """
    Check a user and login.

    Args:
        response (Response): save JWT tokens in cookies.
        user_data (UserRegister): Data required to create a new user in the database.
        db (AsyncSession): Database session.
    Returns:
        TokenResponse: An access and refresh tokens.
    """
    # Compare the data in login field with email, username and phone number in the database.
    filters = [User.username == user_data.login, User.email == user_data.login]

    # Avoid strict correspondence of email and username with PhoneNumber type.
    try:
        parsed_phone = phonenumbers.parse(user_data.login, None)
        if phonenumbers.is_valid_number(parsed_phone):
            normalized_phone = phonenumbers.format_number(parsed_phone, phonenumbers.PhoneNumberFormat.E164)
            filters.append(User.phone_number == normalized_phone)
    except NumberParseException:
        pass

    # Get the user from the database with filters.
    user = await UserDAO.find_one_or_none(db, or_(*filters))
    if not user:
        raise AuthenticationException(detail="User's not found.")

    # Get a password.
    password_db = user.password

    verification = verify_password(user_data.password, password_db)

    if not verification:
        raise AuthenticationException(detail=f"Password's not correct for {user.username}")

    # UUID to string for JSON serialization to get tokens.
    user_id = str(user.id)

    # Create tokens, set tokens in cookies and a refresh token in redis.
    access_token, refresh_token = await create_and_store_tokens(user_id, db)
    send_tokens_to_user(response, access_token, refresh_token)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )


async def logout_user(
        response: Response,
        request: Request,
) -> dict[str, str]:
    """
    Log out a user.

    Args:
        response (Response): save JWT tokens in cookies.
        request (Request): get JWT tokens from cookies.
    Returns:
        dict: Message about success of log out.
    """
    # Verify refresh token from cookies and move it to the blacklist.
    try:
        user_id, jti = await verify_refresh_token(request)
        await delete_refresh_token_from_redis(user_id, jti)
        return {"message": "User logged out"}
    finally:
        delete_tokens_from_cookies(response)


async def renew_tokens(request: Request, response: Response, db: AsyncSession) -> TokenResponse:
    """
    Renew JWT tokens with an old refresh_token.

    Args:
        response (Response): save JWT tokens in cookies.
        request (Request): get JWT tokens from cookies.
        db (AsyncSession): Database session.
    Returns:
        TokenResponse: An access and refresh tokens.
    """
    try:
        # Verify a refresh token and move it to the blacklist.
        user_id, jti = await verify_refresh_token(request)
        await delete_refresh_token_from_redis(user_id, jti)

        # Create tokens, set tokens in cookies and a refresh token in redis.
        new_access_token, new_refresh_token = await create_and_store_tokens(user_id, db)
        send_tokens_to_user(response, new_access_token, new_refresh_token)

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token
        )
    except APIException:
        delete_tokens_from_cookies(response)
        raise