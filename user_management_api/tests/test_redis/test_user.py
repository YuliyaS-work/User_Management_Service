import json
from datetime import timedelta
from unittest.mock import patch, AsyncMock

import pytest

from src.user_management_api.redis.user import get_list_users_from_redis, save_list_users_to_redis

@pytest.fixture
def list_users():
    return [{"id": "123", "name": "Name"}]

@pytest.mark.asyncio
@patch("src.user_management_api.redis.user.r")
async def test_get_list_users_found(
        mock_redis,
        list_users
):
    mock_redis.get.return_value = json.dumps(list_users)

    result = await get_list_users_from_redis("ADMIN", "user_id")

    assert result == list_users

    mock_redis.get.assert_called_once_with("list_users:ADMIN:user_id")


@pytest.mark.asyncio
@patch("src.user_management_api.redis.user.r")
async def test_get_list_users_not_found(
        mock_redis,
        list_users
):
    mock_redis.get.return_value = None

    result = await get_list_users_from_redis("ADMIN", "user_id")

    assert result is None

    mock_redis.get.assert_called_once_with("list_users:ADMIN:user_id")


@pytest.mark.asyncio
@patch("src.user_management_api.redis.user.r")
async def test_get_list_users_fail(
        mock_redis,
        caplog,
        list_users
):
    mock_redis.get = AsyncMock(side_effect = Exception())

    with caplog.at_level("WARNING"):
        result = await get_list_users_from_redis("ADMIN", "user_id")
    assert result is None
    assert "Redis error" in caplog.text
    mock_redis.get.assert_called_once()


@pytest.mark.asyncio
@patch("src.user_management_api.redis.user.r")
async def test_save_list_users_success(
        mock_redis,
        list_users
):
    ttl = timedelta(seconds=3600)
    await save_list_users_to_redis(users=list_users, role="MODERATOR", user_id="user_id")

    mock_redis.setex.assert_called_once_with("list_users:MODERATOR:user_id", int(ttl.total_seconds()), json.dumps(list_users))


@pytest.mark.asyncio
@patch("src.user_management_api.redis.user.r")
async def test_save_list_users_fail(
        mock_redis,
        caplog,
        list_users
):
    mock_redis.setex = AsyncMock(side_effect = Exception())

    with caplog.at_level("WARNING"):
        await save_list_users_to_redis(list_users, "ADMIN", "user_id")
    assert "Redis error" in caplog.text
    mock_redis.setex.assert_called_once()