"""
User module providing routers for user information,
including get, patch and delete operations.
"""

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.user_management_api.db.session import get_session
from src.user_management_api.schemas.user import ProfileUserResponse
from src.user_management_api.services.user import get_me, delete_me

user_router = APIRouter(prefix="/user")

@user_router.get("/me", response_model=ProfileUserResponse)
async def get_me_item(request: Request, db: AsyncSession = Depends(get_session)) -> ProfileUserResponse:
    """
    Information for authenticated user in a profile.

    Args:
        request (Request): Get an access token from cookies.
        db (AsyncSession): Database session.
    Returns:
        ProfileUserResponse: The profile information for an authenticated user.
    """
    return await get_me(request, db)


@user_router.delete("/me")
async def delete_me_item(request: Request, response: Response, db: AsyncSession = Depends(get_session)) -> dict[str, str]:
    """
    Delete a user profile.

    Args:
        request (Request): Get an access token from cookies.
        db (AsyncSession): Database session.
    Returns:
        dict: The message about deletion of a user.
    """
    return await delete_me(request, response, db)