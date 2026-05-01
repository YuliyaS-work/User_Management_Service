import copy
import uuid
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest

from src.user_management_api.core.config import settings
from src.user_management_api.exceptions.auth import AuthenticationException
from src.user_management_api.exceptions.user import S3StorageError, ResourceNotFound
from src.user_management_api.schemas.auth import CurrentUser
from src.user_management_api.schemas.user import PresignUrlGet, ConfirmAvatarRequest
from src.user_management_api.services.user import get_me, delete_me, patch_me, get_avatar, confirm_avatar, \
    delete_avatar, get_presigned_post


@pytest.mark.asyncio
@patch("src.user_management_api.services.user.UserDAO.find_one_or_none_with_related_data")
async def test_get_me_success(
        mock_find_user_with_related_data,
        mock_db_user,
        mock_user
):
    mock_find_user_with_related_data.return_value = mock_user

    current_user = CurrentUser(user_id=str(mock_user.id), group_id=1, roles=["USER"])

    result = await get_me(mock_db_user, current_user)

    assert result.id == mock_user.id
    assert result.roles[0].role_name == "USER"
    assert result.group.group_name == "First"

    mock_find_user_with_related_data.assert_awaited_once()


@pytest.mark.asyncio
@patch("src.user_management_api.services.user.verify_refresh_token")
@patch("src.user_management_api.services.user.delete_refresh_token_from_redis")
@patch("src.user_management_api.services.user.delete_tokens_from_cookies")
@patch("src.user_management_api.services.user.UserDAO.find_one_or_none")
@patch("src.user_management_api.services.user.delete_file")
@patch("src.user_management_api.services.user.delete_presigned_url_from_redis")
@patch("src.user_management_api.services.user.UserDAO.delete_by_id")
async def test_delete_me_success(
        mock_delete_by_id,
        mock_delete_presigned_url,
        mock_delete_file,
        mock_find_user,
        mock_delete_tokens_from_cookies,
        mock_delete_refresh_token_from_redis,
        mock_verify_refresh_token,
        mock_user,
        fake_response,
        fake_request,
        mock_db_user

):
    mock_verify_refresh_token.return_value = (str(mock_user.id), "jti")
    mock_find_user.return_value = mock_user

    current_user = CurrentUser(user_id=str(mock_user.id), group_id=1, roles=["USER"])

    result = await delete_me(fake_request, fake_response, mock_db_user, current_user)

    assert result == {"detail": "A user profile was deleted."}

    mock_verify_refresh_token.assert_called_once_with(fake_request)
    mock_delete_refresh_token_from_redis.assert_called_once_with(str(mock_user.id), "jti")
    mock_delete_tokens_from_cookies.assert_called_once_with(fake_response)
    mock_find_user.assert_awaited_once()
    mock_delete_file.assert_called_once()
    mock_delete_presigned_url.assert_called_once_with(str(mock_user.id))
    mock_delete_by_id.assert_awaited_once()


@pytest.mark.asyncio
@patch("src.user_management_api.services.user.verify_refresh_token")
@patch("src.user_management_api.services.user.delete_refresh_token_from_redis")
@patch("src.user_management_api.services.user.delete_tokens_from_cookies")
@patch("src.user_management_api.services.user.UserDAO.find_one_or_none")
@patch("src.user_management_api.services.user.delete_file")
@patch("src.user_management_api.services.user.delete_presigned_url_from_redis")
@patch("src.user_management_api.services.user.UserDAO.delete_by_id")
async def test_delete_me_user_not_found(
        mock_delete_by_id,
        mock_delete_presigned_url,
        mock_delete_file,
        mock_find_user,
        mock_delete_tokens_from_cookies,
        mock_delete_refresh_token_from_redis,
        mock_verify_refresh_token,
        mock_user,
        fake_response,
        fake_request,
        mock_db_user

):
    mock_verify_refresh_token.return_value = (str(mock_user.id), "jti")
    mock_find_user.return_value = None

    current_user = CurrentUser(user_id=str(mock_user.id), group_id=1, roles=["USER"])

    with pytest.raises(ResourceNotFound) as e:
        await delete_me(fake_request, fake_response, mock_db_user, current_user)

    assert e.value.detail == "User is not found"

    mock_verify_refresh_token.assert_called_once_with(fake_request)
    mock_delete_refresh_token_from_redis.assert_called_once_with(str(mock_user.id), "jti")
    mock_delete_tokens_from_cookies.assert_called_once_with(fake_response)
    mock_find_user.assert_awaited_once()


@pytest.mark.asyncio
@patch("src.user_management_api.services.user.verify_refresh_token")
async def test_delete_me_fail(
        mock_verify_refresh_token,
        mock_user,
        fake_response,
        fake_request,
        mock_db_user

):
    mock_verify_refresh_token.return_value = ("wrong_id", "jti")
    current_user = CurrentUser(user_id=str(mock_user.id), group_id=1, roles=["USER"])

    with pytest.raises(AuthenticationException):
        await delete_me(fake_request, fake_response, mock_db_user, current_user)


@pytest.mark.asyncio
@patch("src.user_management_api.services.user.UserDAO.patch_by_id")
@patch("src.user_management_api.services.user.UserDAO.find_one_or_none_with_related_data")
async def test_patch_me_success(
        mock_find_user_with_related_data,
        mock_patch_user,
        mock_user,
        mock_db_user

):
    mock_find_user_with_related_data.return_value = mock_user


    async def patch_side_effect(db, user_id, data):
        for key, value in data.items():
            setattr(mock_user, key, value)

    data = MagicMock()
    data.model_dump.return_value = {"name": "new_name"}

    mock_patch_user.side_effect = patch_side_effect


    current_user = CurrentUser(user_id=str(mock_user.id), group_id=1, roles=["USER"])

    result = await patch_me(data, mock_db_user, current_user)

    assert result.id == mock_user.id
    assert result.name == "new_name"
    mock_find_user_with_related_data.assert_called_once()
    mock_patch_user.assert_called_once()

@pytest.mark.asyncio
@patch("src.user_management_api.services.user.get_presigned_url_from_redis")
@patch("src.user_management_api.services.user.UserDAO.find_one_or_none")
@patch("src.user_management_api.services.user.create_presigned_url")
@patch("src.user_management_api.services.user.save_presigned_url_to_redis")
async def test_get_avatar_success_url_none_in_redis(
        mock_save_presigned_url_to_redis,
        mock_create_presigned_url,
        mock_find_user,
        mock_get_presigned_url_from_redis,
        mock_db_user,
        mock_user
):
    mock_get_presigned_url_from_redis.return_value = None
    mock_find_user.return_value = mock_user

    mock_create_presigned_url.return_value = "presigned_url"

    current_user = CurrentUser(user_id=str(mock_user.id), group_id=1, roles=["USER"])

    result = await get_avatar(mock_db_user, current_user)

    assert result.presigned_url == "presigned_url"

    mock_create_presigned_url.assert_called_once()
    mock_save_presigned_url_to_redis.assert_called_once_with("presigned_url", str(mock_user.id))


@pytest.mark.asyncio
@patch("src.user_management_api.services.user.get_presigned_url_from_redis")
@patch("src.user_management_api.services.user.UserDAO.find_one_or_none")
async def test_get_avatar_success_url_none_in_redis(
        mock_find_user,
        mock_get_presigned_url_from_redis,
        mock_db_user,
        mock_user
):
    mock_user.image_s3_path = None
    mock_get_presigned_url_from_redis.return_value = None
    mock_find_user.return_value = mock_user

    current_user = CurrentUser(user_id=str(mock_user.id), group_id=1, roles=["USER"])

    with pytest.raises(S3StorageError) as e:
        await get_avatar(mock_db_user, current_user)

    assert e.value.detail == "A way to the avatar in the database is not exist."


@pytest.mark.asyncio
@patch("src.user_management_api.services.user.get_presigned_url_from_redis")
@patch("src.user_management_api.services.user.UserDAO.find_one_or_none")
async def test_get_avatar_success_url_none_in_redis(
        mock_find_user,
        mock_get_presigned_url_from_redis,
        mock_db_user,
        mock_user
):
    mock_user.image_s3_path = None
    mock_get_presigned_url_from_redis.return_value = None
    mock_find_user.return_value = None

    current_user = CurrentUser(user_id=str(mock_user.id), group_id=1, roles=["USER"])

    with pytest.raises(ResourceNotFound) as e:
        await get_avatar(mock_db_user, current_user)

    assert e.value.detail == "User is not found"

@pytest.mark.asyncio
@patch("src.user_management_api.services.user.UserDAO.find_one_or_none_with_related_data")
@patch("src.user_management_api.services.user.save_presigned_url_to_redis")
@patch("src.user_management_api.services.user.create_presigned_url")
@patch("src.user_management_api.services.user.UserDAO.patch_by_id")
@patch("src.user_management_api.services.user.delete_presigned_url_from_redis")
@patch("src.user_management_api.services.user.delete_file")
@patch("src.user_management_api.services.user.UserDAO.find_one_or_none")
async def test_confirm_avatar_success(
        mock_find_user,
        mock_delete_file,
        mock_delete_presigned_url,
        mock_patch_user,
        mock_create_presigned_url,
        mock_save_presigned_url,
        mock_find_user_with_related_data,
        mock_user,
        mock_db_user

):
    mock_find_user.return_value = mock_user
    mock_find_user_with_related_data.return_value = mock_user

    mock_create_presigned_url.return_value = "presigned_url"

    body = ConfirmAvatarRequest(key="key")
    current_user = CurrentUser(user_id=str(mock_user.id), group_id=1, roles=["USER"])

    result = await confirm_avatar(body, mock_db_user, current_user)

    assert result.image_s3_path == mock_user.image_s3_path

    mock_delete_file.assert_called_once()
    mock_delete_presigned_url.assert_called_once_with(str(mock_user.id))
    mock_patch_user.assert_called_once_with(mock_db_user, str(mock_user.id), {"image_s3_path": "key"})
    mock_delete_presigned_url.assert_called_once()
    mock_find_user_with_related_data.assert_called_once()
    mock_save_presigned_url.assert_called_once_with("presigned_url", str(mock_user.id))


@pytest.mark.asyncio
@patch("src.user_management_api.services.user.get_presigned_url_from_redis")
@patch("src.user_management_api.services.user.UserDAO.find_one_or_none")
async def test_confirm_avatar_not_found_user(
        mock_find_user,
        mock_get_presigned_url_from_redis,
        mock_db_user,
        mock_user
):
    mock_find_user.return_value = None

    body = ConfirmAvatarRequest(key="key")
    current_user = CurrentUser(user_id=str(mock_user.id), group_id=1, roles=["USER"])

    with pytest.raises(ResourceNotFound) as e:
        await confirm_avatar(body, mock_db_user, current_user)

    assert e.value.detail == "User is not found"


@pytest.mark.asyncio
@patch("src.user_management_api.services.user.UserDAO.find_one_or_none_with_related_data")
@patch("src.user_management_api.services.user.UserDAO.patch_by_id")
@patch("src.user_management_api.services.user.delete_presigned_url_from_redis")
@patch("src.user_management_api.services.user.delete_file")
@patch("src.user_management_api.services.user.UserDAO.find_one_or_none")
async def test_delete_avatar_success(
        mock_find_user,
        mock_delete_file,
        mock_delete_presigned_url,
        mock_patch_user,
        mock_find_user_with_related_data,
        mock_user,
        mock_db_user

):
    mock_user.image_s3_path = "image_s3_path"
    mock_find_user.return_value = mock_user

    mock_user_after = copy.copy(mock_user)
    mock_user_after.image_s3_path = None
    mock_find_user_with_related_data.return_value = mock_user_after

    current_user = CurrentUser(user_id=str(mock_user.id), group_id=1, roles=["USER"])

    result = await delete_avatar(mock_db_user, current_user)

    assert result.id == mock_user.id
    assert result.image_s3_path is None

    mock_delete_file.assert_called_once_with(settings.bucket_name, "image_s3_path")
    mock_delete_presigned_url.assert_called_once_with(str(mock_user.id))
    mock_patch_user.assert_called_once_with(mock_db_user, str(mock_user.id), {"image_s3_path": None})


@pytest.mark.asyncio
@patch("src.user_management_api.services.user.UserDAO.find_one_or_none")
async def test_delete_avatar_not_found_user(
        mock_find_user,
        mock_db_user,
        mock_user
):
    mock_find_user.return_value = None

    current_user = CurrentUser(user_id=str(mock_user.id), group_id=1, roles=["USER"])

    with pytest.raises(ResourceNotFound) as e:
        await delete_avatar(mock_db_user, current_user)

    assert e.value.detail == "User is not found"


@pytest.mark.asyncio
@patch("src.user_management_api.services.user.create_presigned_post")
@patch("src.user_management_api.services.user.generate_image_s3_path")
async def test_delete_avatar_success(
        mock_generate_path_image,
        mock_create_post,
        mock_user,
        mock_db_user

):
    mock_generate_path_image.return_value = "path_image"
    mock_create_post.return_value = {
        "url": "s3_url",
        "fields": {"key": "value"}
    }

    current_user = CurrentUser(user_id=str(mock_user.id), group_id=1, roles=["USER"])

    result = await get_presigned_post(current_user)

    assert result.key == "path_image"
    assert result.url == "s3_url"

    mock_create_post.assert_called_once_with(settings.bucket_name, "path_image", settings.aws_region, expiration=3600)
    mock_generate_path_image.assert_called_once_with(str(mock_user.id))

