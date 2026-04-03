"""
Health check endpoint verifies that the application is running
and able to response to requests. Returns a simple status indicator for monitoring.
"""
from fastapi import APIRouter

from src.user_management_api.schemas.healthcheck import HealthResponse

health_router = APIRouter(prefix="/system")

@health_router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")