"""
Main FastAPI application entry point.

Initializes the FastAPI app and registers all API routers.
"""

from fastapi import FastAPI

app = FastAPI()

@app.get("/healthcheck")
async def healthcheck() -> dict:
    return {"status": "ok"}