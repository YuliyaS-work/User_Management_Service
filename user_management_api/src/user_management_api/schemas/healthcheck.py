"""
Pydentic model used for Health check endpoint
"""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str