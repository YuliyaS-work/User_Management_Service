from datetime import timedelta
from unittest.mock import patch, AsyncMock

import pytest

from src.user_management_api.redis.redis_s3 import save_presigned_url_to_redis, delete_presigned_url_from_redis, \
    get_presigned_url_from_redis


@pytest.mark.asyncio
@patch("src.user_management_api.redis.redis_s3.r")
async def test_save_presigned_url_to_redis_success(mock_redis):
    """
    save_presigned_url_to_redis() should store the presigned URL
    with correct TTL and key format.
    """
    # Arrange
    ttl = timedelta(seconds=3600)

    # Act
    await save_presigned_url_to_redis(presigned_url="fake_presigned_url",user_id="123")

    # Assert
    mock_redis.setex.assert_called_once_with(
        "presigned_url:123",
        int(ttl.total_seconds()),
        "fake_presigned_url"
    )


@pytest.mark.asyncio
@patch("src.user_management_api.redis.redis_s3.r")
async def test_save_presigned_url_to_redis_fail(mock_redis, caplog):
    """
    save_presigned_url_to_redis() should store the presigned URL
    with correct TTL and key format.
    """
    # Arrange
    mock_redis.setex = AsyncMock(side_effect = Exception())

    # Act/ Assert
    with caplog.at_level("WARNING"):
        await save_presigned_url_to_redis("fake_presigned_url", "user_id")
    assert "Redis error" in caplog.text
    mock_redis.setex.assert_called_once()


@pytest.mark.asyncio
@patch("src.user_management_api.redis.redis_s3.r")
async def test_delete_presigned_url_from_redis_success(mock_redis):
    """
    delete_presigned_url_from_redis() should delete the presigned URL key.
    """
    # Act
    await delete_presigned_url_from_redis(user_id="123")

    # Assert
    mock_redis.delete.assert_called_once_with("presigned_url:123")


@pytest.mark.asyncio
@patch("src.user_management_api.redis.redis_s3.r")
async def test_delete_presigned_url_from_redis_fail(mock_redis, caplog):
    """
    delete_presigned_url_from_redis() should log a warning
    when Redis delete operation fails.
    """
    # Arrange
    mock_redis.delete = AsyncMock(side_effect = Exception())

    # Act/Assert
    with caplog.at_level("WARNING"):
        await delete_presigned_url_from_redis("user_id")
    assert "Redis error" in caplog.text
    mock_redis.delete.assert_called_once()


@pytest.mark.asyncio
@patch("src.user_management_api.redis.redis_s3.r")
async def test_get_presigned_url_from_redis_user_exists(mock_redis):
    """
    get_presigned_url_from_redis() should return the stored URL
    when the key exists.
    """
    # Arrange
    mock_redis.get.return_value = "fake_presigned_url"

    # Act
    result =await get_presigned_url_from_redis(user_id="123")

    # Assert
    assert result == "fake_presigned_url"
    mock_redis.get.assert_called_once_with("presigned_url:123")


@pytest.mark.asyncio
@patch("src.user_management_api.redis.redis_s3.r")
async def test_get_presigned_url_from_redis_user_none(mock_redis):
    """
    get_presigned_url_from_redis() should return None
    when the key does not exist.
    """
    # Arrange
    mock_redis.get.return_value = None

    # Act
    result =await get_presigned_url_from_redis(user_id="123")

    # Assert
    assert result is None
    mock_redis.get.assert_called_once_with("presigned_url:123")



@pytest.mark.asyncio
@patch("src.user_management_api.redis.redis_s3.r")
async def test_get_presigned_url_from_redis_fail(mock_redis,caplog):
    """
     get_presigned_url_from_redis() should log a warning
    when Redis get operation fails.
    """
    # Arrange
    mock_redis.get = AsyncMock(side_effect = Exception())

    # Act/Assert
    with caplog.at_level("WARNING"):
        await get_presigned_url_from_redis("user_id")
    assert "Redis error" in caplog.text
    mock_redis.get.assert_called_once()