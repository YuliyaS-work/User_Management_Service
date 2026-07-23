from unittest.mock import MagicMock, AsyncMock, patch

import pytest
from aiormq.exceptions import DeliveryError

from src.user_management_api.rabbitmq.publisher import publish_message, safe_publish


@pytest.mark.asyncio
@patch("src.user_management_api.rabbitmq.publisher.uuid.uuid4")
async def test_publisher_message_success(mock_uuid):
    """
    publish_message() should send a message to the default exchange
    with the correct routing key and return a success status.
    """
    # Arrange
    mock_app = MagicMock()
    mock_channel = MagicMock()
    mock_exchange = MagicMock()

    mock_exchange.publish = AsyncMock()
    mock_channel.default_exchange = mock_exchange
    mock_app.state.channel = mock_channel

    message_id = "123"
    mock_uuid.return_value = message_id
    message = "message"
    routing_key = "routing_key"
    headers = {"fake_header": 0}

    # Act
    result = await publish_message(mock_app, message, routing_key, headers)

    # Assert
    mock_exchange.publish.assert_called_once()
    args, kwargs = mock_exchange.publish.call_args

    sent_message = args[0]
    assert sent_message.body == message.encode()
    assert kwargs["routing_key"] == "routing_key"
    assert result == {"status": "ack", "message_id": message_id}


@pytest.mark.asyncio
@patch("src.user_management_api.rabbitmq.publisher.uuid.uuid4")
async def test_publisher_message_failed(mock_uuid):
    """
    publish_message() should send a message to the default exchange
    with the correct routing key and return a success status.
    """
    # Arrange
    mock_app = MagicMock()
    mock_channel = MagicMock()
    mock_exchange = MagicMock()

    mock_exchange.publish = AsyncMock(side_effect=DeliveryError(None, None))
    mock_channel.default_exchange = mock_exchange
    mock_app.state.channel = mock_channel

    message_id = "123"
    mock_uuid.return_value = message_id
    message = "message"
    routing_key = "routing_key"
    headers = {"fake_header": 0}

    # Act
    result = await publish_message(mock_app, message, routing_key, headers)

    # Assert
    mock_exchange.publish.assert_called_once()
    args, kwargs = mock_exchange.publish.call_args

    sent_message = args[0]
    assert sent_message.body == message.encode()
    assert kwargs["routing_key"] == "routing_key"
    assert result == {"status": "nack", "message_id": message_id}


@pytest.mark.asyncio
@patch("src.user_management_api.rabbitmq.publisher.publish_message")
async def test_safe_publish_success(mock_publish_message):
    """
    safe_publish() should return an 'ack' status and message ID when publish_message
    is successful.
    """
    # Arrange
    mock_publish_message.return_value = {"status": "ack", "message_id": "123"}
    mock_app = MagicMock()
    message = "message"
    routing_key = "routing_key"
    headers = {"fake_header": 0}

    # Act
    result = await safe_publish(mock_app, message,  routing_key, headers, retries=5)

    # Assert
    assert result["status"] == "ack"
    assert result["message_id"] == "123"
    mock_publish_message.assert_called()


@pytest.mark.asyncio
@patch("src.user_management_api.rabbitmq.publisher.publish_message")
async def test_safe_publish_failed(mock_publish_message):
    """
    safe_publish() should raise RuntimeError when publish_message
    fails on every retry attempt.
    """
    # Arrange
    mock_publish_message.return_value = {"status": "nack", "message_id": "123"}
    mock_app = MagicMock()
    message = "message"
    routing_key = "routing_key"
    headers = {"fake_header": 0}

    # Act
    with pytest.raises(RuntimeError) as e:
        await safe_publish(mock_app, message,  routing_key, headers, retries=5)

    # Assert
    assert str(e.value) == "RabbitMQ did not confirm message."
    assert mock_publish_message.await_count == 5