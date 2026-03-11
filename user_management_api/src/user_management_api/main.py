"""
Main FastAPI application entry point.

Initializes the FastAPI app and registers all API routers.
"""

from fastapi import FastAPI
from starlette.staticfiles import StaticFiles
from core.config import Settings

app = FastAPI()
