"""
Connection module responsible for initializing and managing the RabbitMQ
lifecycle for the FastAPI application, including creating a robust and channel
on startup and closing the connection on shutdown.
"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import aio_pika
from fastapi import FastAPI

from src.user_management_api.core.config import settings

# Create a module specific logger
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Initialize and shut down the RabbitMQ connection from the FastAPI application.
    """
    logger.info("Connecting to RabbitMq")

    try:
        app.state.connection = await aio_pika.connect_robust(
            settings.rabbitmq_url,
        )
        logger.info("RabbitMq connection was established")

        app.state.channel = await app.state.connection.channel()
        logger.info("RabbitMq channel was established")

        await app.state.channel.declare_queue(
            "reset-password-stream",
            durable=True
        )
        logger.info("Queue 'reset-password-stream' was declared")

        yield

    except Exception:
        logger.exception("Failed to initialized RabbitMq")
        raise

    finally:
        await app.state.connection.close()