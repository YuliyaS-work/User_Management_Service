import copy
from unittest.mock import patch, MagicMock, ANY

import pytest

from src.user_management_api.core.config import settings
from src.user_management_api.exceptions.auth import AuthenticationException
from src.user_management_api.exceptions.user import S3StorageError, ResourceNotFound, AuthorizationError
from src.user_management_api.models.roles import StatusRole
from src.user_management_api.schemas.auth import CurrentUser
from src.user_management_api.schemas.user import ConfirmAvatarRequest, UserResponse, \
    UserPatchByAdmin, UserFilter, UserPagination
from src.user_management_api.services.user import get_me, delete_me, patch_me, get_avatar, confirm_avatar, \
    delete_avatar, get_presigned_post, get_user, patch_user, get_users, serialize_user_data


def test_serialize_user_data_success(mock_user):
    """
    serialize_user_data() should convert a User model into a UserResponse object.
    """
    # Act
    result = serialize_user_data(mock_user)

    # Assert
    assert isinstance(result, UserResponse)
    assert result.id == mock_user.id
    assert result.roles[0].role_name == "USER"
    assert result.group.group_name == "First"


def test_serialize_user_data_none():
    """
    serialize_user_data() should raise ResourceNotFound when user is None.
    """
    # Act
    with pytest.raises(ResourceNotFound) as e:
        serialize_user_data(None)

    # Assert
    assert e.value.detail == "User is not found"


@pytest.mark.asyncio
@patch("src.user_management_api.services.user.UserDAO.find_one_or_none_with_related_data")
async def test_get_me_success(
        mock_find_user_with_related_data,
        mock_db,
        mock_user
):
    """
    get_me() should return the current user's full profile with related data.
    """
    # Arrange
    mock_find_user_with_related_data.return_value = mock_user
    current_user = CurrentUser(user_id=str(mock_user.id), group_id=1, roles=["USER"])

    # Act
    result = await get_me(mock_db, current_user)

    # Assert
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
        mock_db
):
    """
    delete_me() should remove user profile, avatar, tokens, and Redis data.
    """
    # Arrange
    mock_verify_refresh_token.return_value = (str(mock_user.id), "jti")
    mock_find_user.return_value = mock_user
    current_user = CurrentUser(user_id=str(mock_user.id), group_id=1, roles=["USER"])

    # Act
    result = await delete_me(fake_request, fake_response, mock_db, current_user)

    # Assert
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
        mock_db
):
    """
    delete_me() should raise ResourceNotFound when user does not exist.
    """
    # Arrange
    mock_verify_refresh_token.return_value = (str(mock_user.id), "jti")
    mock_find_user.return_value = None
    current_user = CurrentUser(user_id=str(mock_user.id), group_id=1, roles=["USER"])

    # Act
    with pytest.raises(ResourceNotFound) as e:
        await delete_me(fake_request, fake_response, mock_db, current_user)

    # Assert
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
        mock_db
):
    """
    delete_me() should raise AuthenticationException when token user_id mismatches.
    """
    # Arrange
    mock_verify_refresh_token.return_value = ("wrong_id", "jti")
    current_user = CurrentUser(user_id=str(mock_user.id), group_id=1, roles=["USER"])

    # Act
    with pytest.raises(AuthenticationException):
        await delete_me(fake_request, fake_response, mock_db, current_user)


@pytest.mark.asyncio
@patch("src.user_management_api.services.user.UserDAO.patch_by_id")
@patch("src.user_management_api.services.user.UserDAO.find_one_or_none_with_related_data")
async def test_patch_me_success(
        mock_find_user_with_related_data,
        mock_patch_user,
        mock_user,
        mock_db
):
    """
    patch_me() should update user fields and return updated profile.
    """
    # Arrange
    mock_find_user_with_related_data.return_value = mock_user

    async def patch_side_effect(db, user_id, data):
        for key, value in data.items():
            setattr(mock_user, key, value)

    data = MagicMock()
    data.model_dump.return_value = {"name": "new_name"}

    mock_patch_user.side_effect = patch_side_effect
    current_user = CurrentUser(user_id=str(mock_user.id), group_id=1, roles=["USER"])

    # Act
    result = await patch_me(data, mock_db, current_user)

    # Assert
    assert result.id == mock_user.id
    assert result.name == "new_name"
    mock_find_user_with_related_data.assert_called_once()
    mock_patch_user.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.rollback.assert_not_called()


@pytest.mark.asyncio
@patch("src.user_management_api.services.user.UserDAO.patch_by_id")
@patch("src.user_management_api.services.user.UserDAO.find_one_or_none_with_related_data")
async def test_patch_me_user_not_found(
        mock_find_user_with_related_data,
        mock_patch_user,
        mock_user,
        mock_db
):
    """
    patch_me() should raise ResourceNotFound when the user does not exist.
    """
    # Arrange
    mock_patch_user.side_effect = ResourceNotFound

    data = MagicMock()
    data.model_dump.return_value = {"name": "new_name"}

    current_user = CurrentUser(user_id=str(mock_user.id), group_id=1, roles=["USER"])

    # Act
    with pytest.raises(ResourceNotFound) as e:
        result = await patch_me(data, mock_db, current_user)

    # Assert
    assert e.value.detail == "User is not found"
    mock_db.rollback.assert_called_once()
    mock_db.commit.assert_not_called()
    mock_find_user_with_related_data.assert_not_called()




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
        mock_db,
        mock_user
):
    """
    get_avatar() should generate and store a new presigned URL when Redis has no entry.
    """
    # Arrange
    mock_get_presigned_url_from_redis.return_value = None
    mock_find_user.return_value = mock_user
    mock_create_presigned_url.return_value = "presigned_url"
    current_user = CurrentUser(user_id=str(mock_user.id), group_id=1, roles=["USER"])

    # Act
    result = await get_avatar(mock_db, current_user)

    # Assert
    assert result.presigned_url == "presigned_url"

    mock_create_presigned_url.assert_called_once()
    mock_save_presigned_url_to_redis.assert_called_once_with("presigned_url", str(mock_user.id))


@pytest.mark.asyncio
@patch("src.user_management_api.services.user.get_presigned_url_from_redis")
@patch("src.user_management_api.services.user.UserDAO.find_one_or_none")
async def test_get_avatar_success_url_none_image_path(
        mock_find_user,
        mock_get_presigned_url_from_redis,
        mock_db,
        mock_user
):
    """
    get_avatar() should raise S3StorageError when user has no image_s3_path.
    """
    # Arrange
    mock_user.image_s3_path = None
    mock_get_presigned_url_from_redis.return_value = None
    mock_find_user.return_value = mock_user
    current_user = CurrentUser(user_id=str(mock_user.id), group_id=1, roles=["USER"])

    # Act
    with pytest.raises(S3StorageError) as e:
        await get_avatar(mock_db, current_user)

    # Assert
    assert e.value.detail == "A way to the avatar in the database is not exist."


@pytest.mark.asyncio
@patch("src.user_management_api.services.user.get_presigned_url_from_redis")
@patch("src.user_management_api.services.user.UserDAO.find_one_or_none")
async def test_get_avatar_success_url_user_not_found(
        mock_find_user,
        mock_get_presigned_url_from_redis,
        mock_db,
        mock_user
):
    """
    get_avatar() should raise ResourceNotFound when user does not exist.
    """
    # Arrange
    mock_user.image_s3_path = None
    mock_get_presigned_url_from_redis.return_value = None
    mock_find_user.return_value = None
    current_user = CurrentUser(user_id=str(mock_user.id), group_id=1, roles=["USER"])

    # Act
    with pytest.raises(ResourceNotFound) as e:
        await get_avatar(mock_db, current_user)

    # Assert
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
        mock_db
):
    """
    confirm_avatar() should update avatar path, delete old file, and save new presigned URL.
    """
    # Arrange
    mock_find_user.return_value = mock_user
    mock_find_user_with_related_data.return_value = mock_user
    mock_create_presigned_url.return_value = "presigned_url"
    body = ConfirmAvatarRequest(key="key")
    current_user = CurrentUser(user_id=str(mock_user.id), group_id=1, roles=["USER"])

    # Act
    result = await confirm_avatar(body, mock_db, current_user)

    # Assert
    assert result.image_s3_path == mock_user.image_s3_path

    mock_delete_file.assert_called_once()
    mock_delete_presigned_url.assert_called_once_with(str(mock_user.id))
    mock_patch_user.assert_called_once_with(mock_db, str(mock_user.id), {"image_s3_path": "key"})
    mock_delete_presigned_url.assert_called_once()
    mock_find_user_with_related_data.assert_called_once()
    mock_save_presigned_url.assert_called_once_with("presigned_url", str(mock_user.id))
    mock_db.commit.assert_called_once()
    mock_db.rollback.assert_not_called()


@pytest.mark.asyncio
@patch("src.user_management_api.services.user.get_presigned_url_from_redis")
@patch("src.user_management_api.services.user.UserDAO.patch_by_id")
@patch("src.user_management_api.services.user.UserDAO.find_one_or_none")
async def test_confirm_avatar_not_found_user(
        mock_find_user,
        mock_patch_by_id,
        mock_get_presigned_url_from_redis,
        mock_db,
        mock_user
):
    """
    confirm_avatar() should raise ResourceNotFound when user does not exist.
    """
    # Arrange
    mock_find_user.return_value = None
    body = ConfirmAvatarRequest(key="key")
    current_user = CurrentUser(user_id=str(mock_user.id), group_id=1, roles=["USER"])

    # Act
    with pytest.raises(ResourceNotFound) as e:
        await confirm_avatar(body, mock_db, current_user)

    # Assert
    assert e.value.detail == "User is not found"
    mock_patch_by_id.assert_not_called()
    mock_get_presigned_url_from_redis.assert_not_called()


@pytest.mark.asyncio
@patch("src.user_management_api.services.user.get_presigned_url_from_redis")
@patch("src.user_management_api.services.user.UserDAO.patch_by_id")
@patch("src.user_management_api.services.user.UserDAO.find_one_or_none")
async def test_confirm_avatar_patch_user_failed(
        mock_find_user,
        mock_patch_by_id,
        mock_get_presigned_url_from_redis,
        mock_db,
        mock_user
):
    """
    confirm_avatar() should raise ResourceNotFound when user does not exist.
    """
    # Arrange
    mock_find_user.return_value = mock_user
    mock_patch_by_id.side_effect = ResourceNotFound
    body = ConfirmAvatarRequest(key="key")
    current_user = CurrentUser(user_id=str(mock_user.id), group_id=1, roles=["USER"])

    # Act
    with pytest.raises(ResourceNotFound) as e:
        await confirm_avatar(body, mock_db, current_user)

    # Assert
    assert e.value.detail == "User is not found"
    mock_db.rollback.assert_called_once()
    mock_get_presigned_url_from_redis.assert_not_called()
    mock_db.commit.assert_not_called()


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
        mock_db
):
    """
    delete_avatar() should remove avatar file, clear Redis entry, and update user record.
    """
    # Arrange
    mock_user.image_s3_path = "image_s3_path"
    mock_find_user.return_value = mock_user
    mock_user_after = copy.copy(mock_user)
    mock_user_after.image_s3_path = None
    mock_find_user_with_related_data.return_value = mock_user_after
    current_user = CurrentUser(user_id=str(mock_user.id), group_id=1, roles=["USER"])

    # Act
    result = await delete_avatar(mock_db, current_user)

    # Assert
    assert result.id == mock_user.id
    assert result.image_s3_path is None

    mock_delete_file.assert_called_once_with(settings.bucket_name, "image_s3_path")
    mock_delete_presigned_url.assert_called_once_with(str(mock_user.id))
    mock_patch_user.assert_called_once_with(mock_db, str(mock_user.id), {"image_s3_path": None})


@pytest.mark.asyncio
@patch("src.user_management_api.services.user.UserDAO.find_one_or_none")
async def test_delete_avatar_not_found_user(
        mock_find_user,
        mock_db,
        mock_user
):
    """
    delete_avatar() should raise ResourceNotFound when user does not exist.
    """
    # Arrange
    mock_find_user.return_value = None
    current_user = CurrentUser(user_id=str(mock_user.id), group_id=1, roles=["USER"])

    # Act
    with pytest.raises(ResourceNotFound) as e:
        await delete_avatar(mock_db, current_user)

    # Assert
    assert e.value.detail == "User is not found"

@pytest.mark.asyncio
@patch("src.user_management_api.services.user.UserDAO.patch_by_id")
@patch("src.user_management_api.services.user.UserDAO.find_one_or_none")
async def test_delete_avatar_patch_user_failed(
        mock_find_user,
        mock_patch_by_id,
        mock_db,
        mock_user
):
    """
    delete_avatar() should raise ResourceNotFound when user does not exist.
    """
    # Arrange
    mock_patch_by_id.side_effect = ResourceNotFound
    mock_find_user.return_value = mock_user
    current_user = CurrentUser(user_id=str(mock_user.id), group_id=1, roles=["USER"])

    # Act
    with pytest.raises(ResourceNotFound) as e:
        await delete_avatar(mock_db, current_user)

    # Assert
    assert e.value.detail == "User is not found"
    mock_db.rollback.assert_called_once()
    mock_db.commit.assert_not_called()
    mock_find_user.assert_called_once()


@pytest.mark.asyncio
@patch("src.user_management_api.services.user.create_presigned_post")
@patch("src.user_management_api.services.user.generate_image_s3_path")
async def test_get_presigned_post_success(
        mock_generate_path_image,
        mock_create_post,
        mock_user,
        mock_db
):
    """
    get_presigned_post() should generate a new S3 upload URL and return key + URL.
    """
    # Arrange
    mock_generate_path_image.return_value = "path_image"
    mock_create_post.return_value = {
        "url": "s3_url",
        "fields": {"key": "value"}
    }
    current_user = CurrentUser(user_id=str(mock_user.id), group_id=1, roles=["USER"])

    # Act
    result = await get_presigned_post(current_user)

    # Assert
    assert result.key == "path_image"
    assert result.url == "s3_url"

    mock_create_post.assert_called_once_with(settings.bucket_name, "path_image", settings.aws_region, expiration=3600)
    mock_generate_path_image.assert_called_once_with(str(mock_user.id))


@pytest.mark.asyncio
@patch("src.user_management_api.services.user.UserDAO.find_one_or_none_with_related_data")
async def test_get_user_admin_success(
        mock_find_user_with_related_data,
        mock_user,
        mock_db
):
    """
    get_user() should allow ADMIN to fetch any user profile.
    """
    # Arrange
    mock_find_user_with_related_data.return_value = mock_user
    current_user = CurrentUser(user_id=str(mock_user.id), group_id=1, roles=["ADMIN"])

    # Act
    result = await get_user(str(mock_user), mock_db, current_user)

    # Assert
    assert isinstance(result, UserResponse)
    mock_find_user_with_related_data.assert_called_once()


@pytest.mark.asyncio
@patch("src.user_management_api.services.user.UserDAO.find_one_or_none_with_related_data")
async def test_get_user_admin_user_not_found(
        mock_find_user_with_related_data,
        mock_user,
        mock_db
):
    """
    get_user() should raise ResourceNotFound when ADMIN requests a missing user.
    """
    # Arrange
    mock_find_user_with_related_data.return_value = None
    current_user = CurrentUser(user_id=str(mock_user.id), group_id=1, roles=["ADMIN"])

    # Act
    with pytest.raises(ResourceNotFound) as e:
        await get_user(str(mock_user), mock_db, current_user)

    # Assert
    assert e.value.detail == "User is not found"
    mock_find_user_with_related_data.assert_called_once()


@pytest.mark.asyncio
@patch("src.user_management_api.services.user.UserDAO.find_one_or_none_with_related_data")
async def test_get_user_moderator_success(
        mock_find_user_with_related_data,
        mock_user,
        mock_db
):
    """
    get_user() should allow MODERATOR to fetch user profiles.
    """
    # Arrange
    mock_find_user_with_related_data.return_value = mock_user
    current_user = CurrentUser(user_id=str(mock_user.id), group_id=1, roles=["MODERATOR"])

    # Act
    result = await get_user(str(mock_user), mock_db, current_user)

    # Assert
    assert isinstance(result, UserResponse)
    mock_find_user_with_related_data.assert_called_once()


@pytest.mark.asyncio
@patch("src.user_management_api.services.user.UserDAO.find_one_or_none_with_related_data")
async def test_get_user_moderator_user_not_found(
        mock_find_user_with_related_data,
        mock_user,
        mock_db
):
    """
    get_user() should raise AuthorizationError when MODERATOR tries to fetch missing user.
    """
    # Arrange
    mock_find_user_with_related_data.return_value = None
    current_user = CurrentUser(user_id=str(mock_user.id), group_id=1, roles=["MODERATOR"])

    # Act
    with pytest.raises(AuthorizationError) as e:
        await get_user(str(mock_user), mock_db, current_user)

    # Assert
    assert e.value.detail == "Not allowed"
    mock_find_user_with_related_data.assert_called_once()


@pytest.mark.asyncio
@patch("src.user_management_api.services.user.UserDAO.find_one_or_none_with_related_data")
async def test_get_user_not_allowed_for_user(
        mock_find_user_with_related_data,
        mock_user,
        mock_db
):
    """
    get_user() should deny access for regular USER role.
    """
    # Arrange
    current_user = CurrentUser(user_id=str(mock_user.id), group_id=1, roles=["USER"])

    # Act
    with pytest.raises(AuthorizationError) as e:
        await get_user(str(mock_user), mock_db, current_user)

    # Assert
    assert e.value.detail == "Not allowed"
    mock_find_user_with_related_data.assert_not_called()


@pytest.mark.asyncio
@patch("src.user_management_api.services.user.UserDAO.patch_by_id")
@patch("src.user_management_api.services.user.UserDAO.update_user_role")
@patch("src.user_management_api.services.user.UserDAO.find_one_or_none_with_related_data")
async def test_patch_user_success(
        mock_find_user_with_related_data,
        mock_update_user_role,
        mock_patch_user,
        mock_db,
        mock_user_data
):
    """
    patch_user() should update user fields and roles when called by ADMIN.
    """
    # Arrange
    role_1 = MagicMock(id = 1, role_name = StatusRole.USER)
    role_2 = MagicMock(id = 2, role_name = StatusRole.MODERATOR)
    user = mock_user_data()
    user.roles = [role_1]
    mock_find_user_with_related_data.return_value = user

    async def patch_side_effect(db, user_id, data):
        for key, value in data.items():
            setattr(user, key, value)

    mock_patch_user.side_effect = patch_side_effect

    async def update_role_side_effect(db, user_id, roles_id):
        user.roles = [role_1, role_2]
        mock_find_user_with_related_data.return_value = user

    mock_update_user_role.side_effect = update_role_side_effect
    data = UserPatchByAdmin(name="new_name", roles_id= [1,2])
    current_user = CurrentUser(user_id=str(user.id), group_id=1, roles=["ADMIN"])

    # Act
    result = await patch_user(str(user.id), data, mock_db, current_user)

    # Assert
    assert isinstance(result, UserResponse)
    assert result.id == user.id
    assert result.name == "new_name"
    assert len(result.roles) == 2
    assert result.roles[0].id == 1
    assert result.roles[0].role_name == "USER"
    assert result.roles[1].id == 2
    assert result.roles[1].role_name == "MODERATOR"

    assert mock_find_user_with_related_data.call_count == 1
    mock_patch_user.assert_called_once_with(mock_db, str(user.id), {"name": "new_name"})
    mock_update_user_role.assert_called_once_with(mock_db, str(user.id), [1,2])


@pytest.mark.asyncio
async def test_patch_user_not_allowed(mock_db):
    """
    patch_user() should raise AuthorizationError when USER or MODERATOR attempts to modify another user.
    """
    # Arrange
    data = MagicMock()
    current_user = CurrentUser(user_id="123", group_id=1, roles=["USER"])

    # Act
    with pytest.raises(AuthorizationError) as e:
        await patch_user("123", data, mock_db, current_user)

    # Assert
    assert e.value.detail == "Not allowed"


@pytest.mark.asyncio
@patch("src.user_management_api.services.user.UserDAO.find_one_or_none_with_related_data")
@patch("src.user_management_api.services.user.UserDAO.update_user_role")
@patch("src.user_management_api.services.user.UserDAO.patch_by_id")
async def test_patch_user_patch_failed(
        mock_patch_by_id,
        mock_update_user_role,
        mock_find_user_with_related_data,
        mock_db,
        mock_user_data
):
    """
    patch_user() should raise ResourceNotFound when updating the user record fails.
    """
    # Arrange
    role_1 = MagicMock(id = 1, role_name = StatusRole.USER)
    role_2 = MagicMock(id = 2, role_name = StatusRole.MODERATOR)
    user = mock_user_data()
    user.roles = [role_1]
    data = MagicMock()
    current_user = CurrentUser(user_id="123", group_id=1, roles=["ADMIN"])
    mock_patch_by_id.side_effect = ResourceNotFound
    # Act
    with pytest.raises(ResourceNotFound) as e:
        await patch_user("123", data, mock_db, current_user)

    # Assert
    assert e.value.detail == "User is not found"
    mock_db.rollback.assert_called_once()
    mock_db.commit.assert_not_called()
    mock_update_user_role.assert_not_called()
    mock_find_user_with_related_data.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "roles, expected_key",
    [
        (["ADMIN"], "ADMIN"),
        (["MODERATOR"], "MODERATOR"),
    ]
)
@patch("src.user_management_api.services.user.UserDAO.get_all")
@patch("src.user_management_api.services.user.get_response_list")
async def test_get_users_admin_moderator_success(
        mock_get_response_list,
        mock_get_all,
        mock_db,
        roles,
        expected_key,
        mock_user_data
):
    """
    get_users() should return filtered and sorted user list for ADMIN or MODERATOR.
    """
    # Arrange
    role = MagicMock(id=1, role_name=StatusRole.USER)
    user = mock_user_data()
    user.roles = [role]
    mock_get_all.return_value = ([user], 1)
    mock_get_response_list.return_value = ["serialized_users"]
    current_user = CurrentUser(user_id=str(user.id), group_id=1, roles=roles)

    user_filter = UserFilter()
    pagination = UserPagination(page=1, size=30)

    # Act
    result = await get_users(mock_db, current_user, user_filter, pagination)

    # Assert
    assert expected_key in result
    data = result[expected_key]
    assert data["users"] == ["serialized_users"]
    assert data["total_users"] == 1
    assert data["page"] == 1
    assert data["size"] == 30
    assert data["total_pages"] == 1
    mock_get_all.assert_called_once_with(mock_db, pagination, ANY, user_filter)
    mock_get_response_list.assert_called_once_with([user])


@pytest.mark.asyncio
async def test_get_users_wrong_role(mock_db, mock_user_data):
    """
    get_users() should raise AuthorizationError when USER attempts to access user list.
    """
    # Arrange
    role = MagicMock(id=1, role_name=StatusRole.USER)
    user = mock_user_data()
    user.roles = [role]
    current_user = CurrentUser(user_id=str(user.id), group_id=1, roles=["USER"])

    user_filter = UserFilter()
    pagination = UserPagination(page=1, size=30)

    # Act
    with pytest.raises(AuthorizationError) as e:
        await get_users(mock_db, current_user, user_filter, pagination)

    # Assert
    assert e.value.detail == "Not allowed"