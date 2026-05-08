from datetime import timedelta
from unittest.mock import patch, AsyncMock

import pytest

from src.user_management_api.redis.auth import delete_refresh_token_from_redis, save_refresh_token_to_redis


@pytest.mark.asyncio
@patch("src.user_management_api.redis.auth.r")
async def test_delete_refresh_token_success(mock_redis):
    """
    delete_refresh_token_from_redis() should delete the active token
    and mark the jti as revoked.
    """
    # Arrange
    mock_redis.delete = AsyncMock()
    mock_redis.setex = AsyncMock()
    expected_ttl = int(timedelta(days=30).total_seconds())

    # Act
    await delete_refresh_token_from_redis(user_id="123", jti="jti")

    # Assert
    mock_redis.delete.assert_called_once_with("refresh_token:123")
    mock_redis.setex.assert_called_once_with(
        "revoked_token:123:jti",
        expected_ttl,
        "true"
    )


@pytest.mark.asyncio
@patch("src.user_management_api.redis.auth.r")
async def test_delete_refresh_token_fail(mock_redis):
    """
    delete_refresh_token_from_redis() should raise an exception
    if Redis delete operation fails.
    """
    # Arrange
    mock_redis.delete = AsyncMock(side_effect = Exception())
    mock_redis.setex = AsyncMock()

    # Act/Assert
    with pytest.raises(Exception):
        await delete_refresh_token_from_redis(user_id="123", jti="jti")

    mock_redis.delete.assert_called_once()
    mock_redis.setex.assert_not_called()


@pytest.mark.asyncio
@patch("src.user_management_api.redis.auth.get_token_hash")
@patch("src.user_management_api.redis.auth.r")
async def test_save_refresh_token_success(
        mock_redis,
        mock_get_token_hash
):
    """
    save_refresh_token_to_redis() should store the hashed token
    with correct TTL and key format.
    """
    # Arrange
    mock_get_token_hash.return_value = "fake_token_hash"
    ttl = timedelta(days=30)

    # Act
    await save_refresh_token_to_redis(refresh_token="token",user_id="123", jti="jti")

    # Assert
    mock_redis.setex.assert_called_once_with(
        "refresh_token:123",
        int(ttl.total_seconds()),
        "fake_token_hash"
    )


@pytest.mark.asyncio
@patch("src.user_management_api.redis.auth.get_token_hash")
@patch("src.user_management_api.redis.auth.r")
async def test_save_refresh_token_fail(
        mock_redis,
        mock_get_token_hash
):
    """
    save_refresh_token_to_redis() should raise an exception
    if Redis setex operation fails.
    """
    # Arrange
    mock_redis.setex = AsyncMock(side_effect=Exception())
    mock_get_token_hash.return_value = "fake_token_hash"

    # Act
    with pytest.raises(Exception):
        await save_refresh_token_to_redis(refresh_token="token",user_id="123", jti="jti")

    # Assert
    mock_redis.setex.assert_called_once()