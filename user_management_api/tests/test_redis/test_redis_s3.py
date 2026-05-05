from datetime import timedelta
from unittest.mock import patch, AsyncMock

import pytest

from src.user_management_api.redis.redis_s3 import save_presigned_url_to_redis, delete_presigned_url_from_redis, \
    get_presigned_url_from_redis


@pytest.mark.asyncio
@patch("src.user_management_api.redis.redis_s3.r")
async def test_save_presigned_url_to_redis_success(
        mock_redis
):
    ttl = timedelta(seconds=3600)
    await save_presigned_url_to_redis(presigned_url="fake_presigned_url",user_id="123")

    mock_redis.setex.assert_called_once_with("presigned_url:123", int(ttl.total_seconds()), "fake_presigned_url")


@pytest.mark.asyncio
@patch("src.user_management_api.redis.redis_s3.r")
async def test_save_presigned_url_to_redis_fail(
        mock_redis,
        caplog
):
    mock_redis.setex = AsyncMock(side_effect = Exception())

    with caplog.at_level("WARNING"):
        await save_presigned_url_to_redis("fake_presigned_url", "user_id")
    assert "Redis error" in caplog.text
    mock_redis.setex.assert_called_once()

@pytest.mark.asyncio
@patch("src.user_management_api.redis.redis_s3.r")
async def test_delete_presigned_url_from_redis_success(
        mock_redis
):
    await delete_presigned_url_from_redis(user_id="123")

    mock_redis.delete.assert_called_once_with("presigned_url:123")


@pytest.mark.asyncio
@patch("src.user_management_api.redis.redis_s3.r")
async def test_delete_presigned_url_from_redis_fail(
        mock_redis,
        caplog
):
    mock_redis.delete = AsyncMock(side_effect = Exception())

    with caplog.at_level("WARNING"):
        await delete_presigned_url_from_redis("user_id")
    assert "Redis error" in caplog.text
    mock_redis.delete.assert_called_once()


@pytest.mark.asyncio
@patch("src.user_management_api.redis.redis_s3.r")
async def test_get_presigned_url_from_redis_user_exists(
        mock_redis
):
    mock_redis.get.return_value = "fake_presigned_url"
    result =await get_presigned_url_from_redis(user_id="123")
    assert result == "fake_presigned_url"
    mock_redis.get.assert_called_once_with("presigned_url:123")


@pytest.mark.asyncio
@patch("src.user_management_api.redis.redis_s3.r")
async def test_get_presigned_url_from_redis_user_none(
        mock_redis
):
    mock_redis.get.return_value = None
    result =await get_presigned_url_from_redis(user_id="123")
    assert result is None
    mock_redis.get.assert_called_once_with("presigned_url:123")



@pytest.mark.asyncio
@patch("src.user_management_api.redis.redis_s3.r")
async def test_get_presigned_url_from_redis_fail(
        mock_redis,
        caplog
):
    mock_redis.get = AsyncMock(side_effect = Exception())

    with caplog.at_level("WARNING"):
        await get_presigned_url_from_redis("user_id")
    assert "Redis error" in caplog.text
    mock_redis.get.assert_called_once()