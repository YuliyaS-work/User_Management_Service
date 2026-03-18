"""Authentication module providing handlers for user authentication,
including sign-up, login, logout and token refresh operations.
"""
from fastapi import HTTPException, status, Response
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.user_management_api.core.security import get_password_hash, create_access_token, create_refresh_token
from src.user_management_api.core.config import  Settings
from src.user_management_api.models import User
from src.user_management_api.schemas.auth import UserRegister
from src.user_management_api.dao.user import UserDAO


async def register_user(response: Response, user_data: UserRegister, db: AsyncSession) -> dict:
    user = await UserDAO.find_one_or_none(db, or_(User.username == user_data.username, User.email == user_data.email))
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
    user_dict = user_data.model_dump()
    user_dict["password"] = get_password_hash(user_data.password)
    new_user = await UserDAO.add(db, **user_dict)
    await db.commit()

    user_id = str(new_user.id)
    access_token = create_access_token({"sub": user_id})
    refresh_token = create_refresh_token({"sub": user_id})
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
    Settings.r.set(f"user_id_{user_id}", f"{refresh_token}")
    return {"message": "User registered successfully"}