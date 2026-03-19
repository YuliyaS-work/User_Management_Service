"""
Health check endpoint verifies that the application is running
and able to response to requests. Returns a simple status indicator for monitoring.
"""

from src.user_management_api.schemas.healthcheck import HealthResponse
from src.user_management_api.main import app


@app.get("/healthcheck", response_model=HealthResponse)
async def healthcheck() -> HealthResponse:
    return HealthResponse(status="ok")