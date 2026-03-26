"""
User module providing routers for user information,
including get, patch and delete operations.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.user_management_api.db.session import get_session
from src.user_management_api.schemas.user import UserResponse
from src.user_management_api.services.user import get_me

user_router = APIRouter(prefix="/user")

@user_router.get("/me", response_model=UserResponse)
async def get_me_item(request: Request, db: AsyncSession = Depends(get_session)) -> UserResponse:
    """
    Information for authenticated user in a profile.

    Args:
        request (Request): Get an access token from cookies.
        db (AsyncSession): Database session.
    Returns:
        UserResponse: The profile information for an authenticated user.
    """
    return await get_me(request, db)