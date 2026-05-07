from unittest.mock import MagicMock, AsyncMock

import pytest

from src.user_management_api.rabbitmq.publisher import publish_message


@pytest.mark.asyncio
async def test_publisher_message():
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

    message = "message"

    # Act
    result = await publish_message(mock_app, message)

    # Assert
    mock_exchange.publish.assert_called_once()
    args, kwargs = mock_exchange.publish.call_args

    sent_message = args[0]
    assert sent_message.body == message.encode()
    assert kwargs["routing_key"] == "reset-password-stream"
    assert result == {"status": "ok"}

