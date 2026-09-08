"""
RabbitMQ publishing module providing a helper function for sending messages
to the reset-password queue using the application's shared AMQP channel.
"""
import uuid

import aio_pika
from fastapi import FastAPI


async def publish_message(app: FastAPI, message: str) -> dict[str, str]:
    """
    Publish a message to the reset-password RabbitMQ queue.
    """
    message_id = str(uuid.uuid4())

    await app.state.channel.default_exchange.publish(
        aio_pika.Message(
            body=message.encode(),
            message_id=message_id,
            headers={"x-retry-count":0},
            content_type="application/json"
        ),
        routing_key = "reset-password-stream",
    )
    return {"status": "ok"}