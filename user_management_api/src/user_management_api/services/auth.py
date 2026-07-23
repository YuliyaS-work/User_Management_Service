"""
Authentication module providing handlers for user authentication,
including sign-up, login, logout, token refresh operations,
reset a user's password and save a new user's password into tha database.
"""
import json
import logging
from datetime import datetime, timezone

import phonenumbers
from fastapi import Response, Request, BackgroundTasks, status
from phonenumbers.phonenumberutil import NumberParseException
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.user_management_api.core.security import get_password_hash, create_access_token, create_refresh_token, \
    verify_password, decode_token, validate_refresh_token, get_token_hash, validate_access_token, \
    create_reset_password_token, validate_reset_password_token
from src.user_management_api.exceptions.auth import ConflictException, APIException, AuthenticationException
from src.user_management_api.exceptions.user import ResourceNotFound
from src.user_management_api.models import User
from src.user_management_api.rabbitmq.publisher import safe_publish
from src.user_management_api.redis.auth import save_refresh_token_to_redis, delete_refresh_token_from_redis

from src.user_management_api.schemas.auth import UserRegister, UserLogin, TokenResponse, CurrentUser, \
    ForgetPasswordRequest, ResetPasswordRequest
from src.user_management_api.dao.user import UserDAO
from src.user_management_api.utils.auth import send_tokens_to_user, delete_tokens_from_cookies, \
    get_refresh_token_from_cookie, get_access_token_from_cookie


# Create a module specific logger
logger = logging.getLogger(__name__)


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
    logger.info(f"Start: creating and saving tokens for user ID={user_id}")
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
    logger.info(f"Success: access and refresh tokens are created")
    return access_token, refresh_token


async def verify_refresh_token(request: Request) -> tuple[str, str]:
    """
    Verify refresh token from cookies to one stored in redis.
    """
    logger.info(f"Start: verifying refresh token from cookies")
    old_refresh_token = get_refresh_token_from_cookie(request)
    payload = decode_token(old_refresh_token)
    hash_token = get_token_hash(old_refresh_token)
    user_id, jti = await validate_refresh_token(payload, hash_token)
    logger.info(f"Success: refresh token verified for user ID={user_id}")
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
    logger.info(f"Start: user registration, data={user_data.model_dump()}")

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

    logger.info(f"Success: user registered: user ID={user_id}")

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
    logger.info(f"Start: user log in, data={user_data.login}")

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

    logger.info(f"Success: user logged in: user ID={user_id}")

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
    logger.info(f"Start: user log out")

    # Verify refresh token from cookies and move it to the blacklist.
    try:
        user_id, jti = await verify_refresh_token(request)
        await delete_refresh_token_from_redis(user_id, jti)
        logger.info(f"Success: user logged out: user ID={user_id}")
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

    logger.info(f"Start: renewing access and refresh tokens.")
    try:
        # Verify a refresh token and move it to the blacklist.
        user_id, jti = await verify_refresh_token(request)
        await delete_refresh_token_from_redis(user_id, jti)

        # Create tokens, set tokens in cookies and a refresh token in redis.
        new_access_token, new_refresh_token = await create_and_store_tokens(user_id, db)
        send_tokens_to_user(response, new_access_token, new_refresh_token)

        logger.info(f"Success: tokens are renewed for user ID={user_id}.")

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token
        )
    except APIException:
        delete_tokens_from_cookies(response)
        raise


async def reset_password(
        background_tasks: BackgroundTasks,
        data: ForgetPasswordRequest,
        request: Request
) -> dict[str, str]:
    """
    Generate a reset-password token and publish an email message to RabbitMQ.

    Args:
        background_tasks (BackgroundTasks): Schedules publishing the message asynchronously.
        data (ForgetPasswordRequest): A user's email used to generate reset token.
        request (Request): used to build the reset-password URL.

    Returns:
        dict[str, str]: Confirm that the message was published to RabbitMQ.
    """
    logger.info(f"Start: reset password.")

    # Create a reset-password token.
    token = create_reset_password_token(data.email)

    # Create a link to reset a password.
    reset_link = f"{request.base_url}reset-password?token={token}"

    # Create an email message for publishing.
    message = {
        "subject": "Reset your password",
        "body": f"Click the link to reset your password: {reset_link}",
        "email": data.email,
        "token": token,
        "datetime": datetime.now(timezone.utc).isoformat()
    }

    # Publish a reset-password message to RabbitMQ asynchronously.
    background_tasks.add_task(
        safe_publish,
        request.app,
        json.dumps(message),
        "reset-password-stream",
        headers={"x-retry-count": 0}
    )
    logger.info(f"Success: message sent to RabbitMQ for user email={data.email}.")

    return {"message": "Message sent to RabbitMQ"}


async def save_password(
        data: ResetPasswordRequest,
        db: AsyncSession
) -> dict[str, str]:
    """
    Validate the reset-password token and update the user's password into the database.

    Args:
        data (ResetPasswordRequest): A token and a new password provided by the user.
        db (AsyncSession): Database session.
    Returns:
        dict[str,str]: Confirm a message about the password update result.
    """
    logger.info(f"Start: saving new password, user token={data.token}.")

    payload = decode_token(data.token)
    validate_reset_password_token(payload)

    new_password_hash = get_password_hash(data.new_password)

    user = await UserDAO.find_one_or_none(db, User.email == payload.sub)
    if user is None:
        raise ResourceNotFound("User is not found")

    if  verify_password(data.new_password, user.password):
        return {"message": "Don't use the old password."}

    try:
        await UserDAO.patch_by_id(db, str(user.id), {"password": new_password_hash})
    except:
        raise APIException("Failed to update password.")

    await db.commit()

    logger.info(f"Success: password saved, user ID={user.id}.")

    return {"message": "Password was changed successfully"}


def validate_incoming_token(request: Request) -> CurrentUser :
    """
    Validate incoming access token from Innoter Service.

    Args:
        request (Request): used to build the reset-password URL.
    Returns:
        CurrentUser: contains user ID, roles ID, group ID.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise AuthenticationException("Missing token")

    incoming_access_token = auth_header.split(" ")[1]

    payload = decode_token(incoming_access_token)
    validate_access_token(payload)
    current_user = CurrentUser(
        user_id=payload.sub,
        group_id=payload.group_id,
        roles=payload.roles
    )
    return current_user
