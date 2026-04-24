"""
Main FastAPI application entry point.

Initializes the FastAPI app and registers all API routers.
"""

from fastapi import FastAPI

from src.user_management_api.core.exception_handlers import api_exception_handler
from src.user_management_api.core.logging_config import setup_logging
from src.user_management_api.exceptions.auth import APIException
from src.user_management_api.rabbitmq.connection import lifespan
from src.user_management_api.routers.auth import auth_router
from src.user_management_api.routers.healthcheck import health_router
from src.user_management_api.routers.user import user_router, users_router

setup_logging()

app = FastAPI(lifespan=lifespan)


app.include_router(health_router)
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(users_router)

app.add_exception_handler(APIException, api_exception_handler)