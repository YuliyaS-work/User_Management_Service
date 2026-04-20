"""
Connection module responsible for initializing and managing the RabbitMQ
lifecycle for the FastAPI application, including creating a robust and channel
on startup and closing the connection on shutdown.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import aio_pika
from fastapi import FastAPI

from src.user_management_api.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Initialize and shut down the RabbitMQ connection from the FastAPI application.
    """
    app.state.connection = await aio_pika.connect_robust(
        settings.rabbitmq_url,
    )
    app.state.channel = await app.state.connection.channel()

    await app.state.channel.declare_queue(
        "reset-password-stream",
        durable=True
    )
    try:
        yield
    finally:
        await app.state.connection.close()