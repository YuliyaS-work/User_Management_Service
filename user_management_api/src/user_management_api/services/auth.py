"""Authentication module providing handlers for user authentication,
including sign-up, login, logout and token refresh operations.
"""

from fastapi import HTTPException, status, Response, Request
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.user_management_api.core.security import get_password_hash, create_access_token, create_refresh_token, \
    verify_password
from src.user_management_api.models import User
from src.user_management_api.schemas.auth import UserRegister, UserLogin
from src.user_management_api.dao.user import UserDAO
from src.user_management_api.core.config import  r


def get_token_cookie(request: Request):
    access_token = request.cookies.get("user_access_token")
    ...

def delete_tokens(request: Request):
    ...


def send_tokens_to_user(response: Response, user_id: str) -> None:
    """
    Send a couple of JWT tokens to a user and refresh token to redis.
    """
    # Create JWT tokens.
    access_token = create_access_token({"sub": user_id})
    refresh_token = create_refresh_token({"sub": user_id})

    # Set JWT tokens to cookies.
    response.set_cookie(
        key="user_access_token",
        value=access_token,
        httponly=True,
        secure=True
    )
    response.set_cookie(
        key="user_refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True
    )

    # Set JWT refresh token in Redis.
    redis_token = r.get("refresh_token:{user_id}")
    if redis_token:
        r["refresh_token:{user_id}"] = f"{refresh_token}"
    else:
        r.set(f"refresh_token:{user_id}", f"{refresh_token}")

    return None


async def register_user(response: Response, user_data: UserRegister, db: AsyncSession) -> dict:
    """
        Register a user and create a record in the database.

        Args:
            response (Response): save JWT tokens in cookies.
            user_data (UserRegister): Data required to create a new user in the database.
            db (AsyncSession): Database session.
        Returns:
            dict: Message about success of registration.
        """
    # Check that email and username are unique.
    user = await UserDAO.find_one_or_none(
        db,
        or_(User.username == user_data.username, User.email == user_data.email)
    )
    if user:
        if user.username == user_data.username:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already exists"
            )
        if user.email == user_data.email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already exists"
            )
    # Get a dictionary of instance.
    user_dict = user_data.model_dump()

    # Get password hash.
    user_dict["password"] = get_password_hash(user_data.password)

    # Add a user to the database.
    new_user = await UserDAO.add(db, **user_dict)
    await db.commit()

    # UUID to string for JSON serialization to get tokens.
    user_id = str(new_user.id)

    send_tokens_to_user(response, user_id)

    return {"message": "User registered successfully"}


async def login_user(response: Response, user_data: UserLogin, db: AsyncSession) -> User | None:
    """
        Check a user and login.

        Args:
            user_data (UserRegister): Data required to create a new user in the database.
            db (AsyncSession): Database session.
        Returns:
            dict: Message about success of login.
        """
    user = await UserDAO.find_one_or_none(
        db,
        or_(User.username == user_data.username, User.email == user_data.email, User.phone_number == user_data.phone_number)
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User's not found."
        )

    # Get a password from the database.
    password_db = UserDAO.find_one_or_none(db, User.password == user_data.password)

    # Get provided password hash.
    plain_password = get_password_hash(user_data.password)

    verification = verify_password(plain_password, password_db)

    if not verification:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Password's not correct."
        )

    # UUID to string for JSON serialization to get tokens.
    user_id = str(user.id)

    send_tokens_to_user(response, user_id)

    return user