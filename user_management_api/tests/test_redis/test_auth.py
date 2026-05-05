from datetime import timedelta
from unittest.mock import patch, AsyncMock

import pytest

from src.user_management_api.redis.auth import delete_refresh_token_from_redis, save_refresh_token_to_redis


@pytest.mark.asyncio
@patch("src.user_management_api.redis.auth.r")
async def test_delete_refresh_token_success(
        mock_redis
):
    await delete_refresh_token_from_redis(user_id="123", jti="jti")

    mock_redis.delete.assert_called_once_with("refresh_token:123")
    mock_redis.set.assert_called_once_with("revoked_token:123:jti", "true")


@pytest.mark.asyncio
@patch("src.user_management_api.redis.auth.r")
async def test_delete_refresh_token_fail(
        mock_redis
):
    mock_redis.delete = AsyncMock(side_effect = Exception())
    mock_redis.set = AsyncMock()

    with pytest.raises(Exception):
        await delete_refresh_token_from_redis(user_id="123", jti="jti")

    mock_redis.delete.assert_called_once()


@pytest.mark.asyncio
@patch("src.user_management_api.redis.auth.get_token_hash")
@patch("src.user_management_api.redis.auth.r")
async def test_save_refresh_token_success(
        mock_redis,
        mock_get_token_hash
):
    mock_get_token_hash.return_value = "fake_token_hash"
    ttl = timedelta(days=30)
    await save_refresh_token_to_redis(refresh_token="token",user_id="123", jti="jti")

    mock_redis.setex.assert_called_once_with("refresh_token:123", int(ttl.total_seconds()), "fake_token_hash")


@pytest.mark.asyncio
@patch("src.user_management_api.redis.auth.get_token_hash")
@patch("src.user_management_api.redis.auth.r")
async def test_save_refresh_token_fail(
        mock_redis,
        mock_get_token_hash
):
    mock_redis.setex = AsyncMock(side_effect=Exception())
    mock_get_token_hash.return_value = "fake_token_hash"
    with pytest.raises(Exception):
        await save_refresh_token_to_redis(refresh_token="token",user_id="123", jti="jti")

    mock_redis.setex.assert_called_once()