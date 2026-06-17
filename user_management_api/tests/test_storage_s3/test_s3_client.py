from unittest.mock import patch, AsyncMock

import pytest
from botocore.exceptions import ClientError

from src.user_management_api.exceptions.user import S3StorageError
from src.user_management_api.storage_s3.s3_client import generate_image_s3_path, delete_file, create_presigned_post, \
    create_presigned_url


def test_generate_image_s3_path():
    """
    generate_image_s3_path() should return a valid S3 path for the user's avatar.
    """
    # Arrange
    user_id = "123"

    # Act
    path = generate_image_s3_path(user_id)

    # Assert
    assert path.startswith("users/avatar/123_")
    assert path.endswith(".webp")


@pytest.mark.asyncio
@patch("src.user_management_api.storage_s3.s3_client.s3_session.client")
async def test_delete_file_success(mock_s3_client, mock_s3):
    """
    delete_file() should delete the file from S3 when the client succeeds.
    """
    # Arrange
    mock_s3_client.return_value.__aenter__.return_value = mock_s3

    # Act
    await delete_file("bucket", "key")

    # Assert
    mock_s3.delete_object.assert_called_once_with(
        Bucket="bucket",
        Key="key"
    )


@pytest.mark.asyncio
@patch("src.user_management_api.storage_s3.s3_client.s3_session.client")
async def test_delete_file_client_error(mock_s3_client, mock_s3):
    """
     delete_file() should raise S3StorageError when S3 delete_object fails.
    """
    # Arrange
    mock_s3.__aenter__.return_value.delete_object.side_effect = ClientError(
        {"Error": {}}, "DeleteObject"
    )
    mock_s3_client.return_value = mock_s3

    # Act
    with pytest.raises(S3StorageError) as e:
        await delete_file("bucket", "key")

    # Assert
    assert e.value.detail == "The file is not deleted"


@pytest.mark.asyncio
@patch("src.user_management_api.storage_s3.s3_client.s3_session.client")
async def test_create_presigned_post_success(mock_s3_client, mock_s3):
    """
    create_presigned_post() should return a valid presigned POST dict.
    """
    # Arrange
    mock_s3.__aenter__.return_value.generate_presigned_post.return_value ={
        "url": "https://s3.aws.test",
        "fields": {"key": "value"}
    }
    mock_s3_client.return_value = mock_s3

    # Act
    result = await create_presigned_post("bucket", "image_s3_path", "region_mane")

    # Assert
    assert result["url"] == "https://s3.aws.test"
    assert "fields" in result


@pytest.mark.asyncio
@patch("src.user_management_api.storage_s3.s3_client.s3_session.client")
async def test_create_presigned_post_client_error(mock_s3_client, mock_s3):
    """
    create_presigned_post() should raise S3StorageError when S3 fails.
    """
    # Arrange
    mock_s3.__aenter__.return_value.generate_presigned_post.side_effect = ClientError (
        {"Error": {"Code": "500", "Message": "fail"}}, "GeneratePresignedPost"
    )
    mock_s3_client.return_value = mock_s3

    # Act
    with pytest.raises(S3StorageError) as e:
        await create_presigned_post("bucket", "image_s3_path", "region_mane")

    # Assert
    assert e.value.detail == "Presigned post is not generated"


@pytest.mark.asyncio
async def test_create_presigned_post_empty_path():
    """
    create_presigned_post() should raise S3StorageError when image_s3_path is missing.
    """
    # Act
    with pytest.raises(S3StorageError) as e:
        await create_presigned_post("bucket", None, "region_mane")

    # Assert
    assert e.value.detail == "A path to the avatar in the database is not exist."


@pytest.mark.asyncio
@patch("src.user_management_api.storage_s3.s3_client.s3_session.client")
async def test_create_presigned_url_success(mock_s3_client, mock_s3):
    """
    create_presigned_url() should return a valid presigned URL.
    """
    # Arrange
    mock_s3.__aenter__.return_value.generate_presigned_url.return_value = "https://s3.aws.test"
    mock_s3_client.return_value = mock_s3

    # Act
    result = await create_presigned_url("bucket", "users/avatar/1.webp", "region_mane")

    # Assert
    assert result == "https://s3.aws.test"


@pytest.mark.asyncio
async def test_create_presigned_url_empty_path():
    """
    create_presigned_url() should raise S3StorageError when S3 fails.
    """
    # Act
    with pytest.raises(S3StorageError) as e:
        await create_presigned_url("bucket", None, "region_mane")

    # Assert
    assert e.value.detail == "A way to the avatar in the database is not exist."


@pytest.mark.asyncio
@patch("src.user_management_api.storage_s3.s3_client.s3_session.client")
async def test_create_presigned_url_client_error(mock_s3_client, mock_s3):
    """
    create_presigned_url() should raise S3StorageError when image_s3_path is missing.
    """
    # Arrange
    mock_s3.__aenter__.return_value.generate_presigned_url.side_effect = ClientError (
        {"Error": {"Code": "500", "Message": "fail"}}, "GeneratePresignedUrl"
    )
    mock_s3_client.return_value = mock_s3

    # Act
    with pytest.raises(S3StorageError) as e:
        await create_presigned_url("bucket", "image_s3_path", "region_mane")

    # Assert
    assert e.value.detail == "The presigned url is not created"