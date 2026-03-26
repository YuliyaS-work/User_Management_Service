"""
Main FastAPI application entry point.

Initializes the FastAPI app and registers all API routers.
"""

from fastapi import FastAPI

from src.user_management_api.routers.auth import auth_router
from src.user_management_api.routers.user import user_router

app = FastAPI()

app.include_router(auth_router)
app.include_router(user_router)