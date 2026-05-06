from unittest.mock import MagicMock, AsyncMock

import pytest

from src.user_management_api.rabbitmq.publisher import publish_message


@pytest.mark.asyncio
async def test_publisher_message():
    mock_app = MagicMock()
    mock_channel = MagicMock()
    mock_exchange = MagicMock()

    mock_exchange.publish = AsyncMock()
    mock_channel.default_exchange = mock_exchange
    mock_app.state.channel = mock_channel

    message = "message"

    result = await publish_message(mock_app, message)

    args, kwargs = mock_exchange.publish.call_args

    sent_message = args[0]
    assert sent_message.body == message.encode()

    assert kwargs["routing_key"] == "reset-password-stream"
    assert result == {"status": "ok"}

    mock_exchange.publish.assert_called_once()