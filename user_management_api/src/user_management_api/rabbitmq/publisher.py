"""
RabbitMQ publishing module providing a reliable message delivery
layer with publisher confirms and automatic retry handling.

This module contains a helper function for publishing messages to any RabbitMQ
routing key using the application's shared AMQP channel. It ensures safe,
acknowledged delivery and gracefully retries while RabbitMQ remains
temporarily unavailable.
"""
import asyncio
import logging
import uuid
from typing import Any

import aio_pika
from aiormq.exceptions import DeliveryError
from fastapi import FastAPI

# Create a module specific logger
logger = logging.getLogger(__name__)

async def publish_message(
        app: FastAPI,
        message: str,
        routing_key: str,
        headers: dict[str, Any] | None = None
) -> dict[str, str]:
    """
    Publish a message to the RabbitMQ queue.
    """
    message_id = str(uuid.uuid4())

    try:
        await app.state.channel.default_exchange.publish(
            aio_pika.Message(
                body=message.encode(),
                message_id=message_id,
                headers=headers,
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key = routing_key,
            mandatory=True
        )
        return {"status": "ack", "message_id": message_id}

    except DeliveryError:
        logger.error(f"Message was not sent, message_id={message_id}.")
        return {"status": "nack", "message_id": message_id}


async def safe_publish(
        app: FastAPI,
        message: str,
        routing_key: str,
        headers: dict[str, Any] | None = None,
        retries: int = 5
) -> dict[str, str] | None:
    """
    Retries message publishing while RabbitMQ is temporarily unavailable.
    """
    for attempt in range(retries):
        result = await publish_message(app, message, routing_key, headers)
        if result["status"] == "ack":
            return result
        await asyncio.sleep(0.5 * 2 ** attempt)

    logger.error("RabbitMQ did not confirm message.")
    raise RuntimeError("RabbitMQ did not confirm message.")