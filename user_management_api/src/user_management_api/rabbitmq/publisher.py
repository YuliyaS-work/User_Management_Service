"""
RabbitMQ publishing module providing a helper function for sending messages
to the reset-password queue using the application's shared AMQP channel.
"""
import aio_pika
from fastapi import FastAPI


async def publish_message(app: FastAPI, message: str) -> dict[str, str]:
    """
    Publish a message to the reset-password RabbitMQ queue.
    """
    await app.state.channel.default_exchange.publish(
        aio_pika.Message(body=message.encode()),
        routing_key = "reset-password-stream",
    )
    return {"status": "ok"}