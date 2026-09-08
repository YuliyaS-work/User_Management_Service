import uuid
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from sqlalchemy import Insert, Delete

from src.user_management_api.dao.user import UserDAO
from src.user_management_api.schemas.user import UserPagination, UserFilter


@pytest.mark.asyncio
@patch("src.user_management_api.dao.user.RoleDAO.find_one_or_none")
@patch("src.user_management_api.dao.base.BaseDAO.add")
async def test_user_add_success(
        mock_base_add,
        mock_find_role,
        mock_db,
        mock_user_data,
        user_register_data
):
    """
    UserDAO.add() should successfully create a user and assign default USER role.
    """
    # Arrange
    user = mock_user_data()
    mock_base_add.return_value = user
    fake_role = MagicMock(id = 1)
    mock_find_role.return_value = fake_role

    # Act
    result = await UserDAO.add(mock_db, **user_register_data.model_dump())

    # Assert
    assert result == user
    mock_base_add.assert_called_once_with(mock_db, **user_register_data.model_dump())
    mock_find_role.assert_called_once()

    mock_db.execute.assert_called_once()
    args, kwargs = mock_db.execute.call_args

    assert isinstance(args[0], Insert)
    assert args[0].table.name == "user_role"

    values = args[0].compile().params
    assert set(values.keys()) == {"user_id", "role_id"}
    assert values["user_id"] == user.id
    assert values["role_id"] == fake_role.id


@pytest.mark.asyncio
@patch("src.user_management_api.dao.user.RoleDAO.find_one_or_none")
@patch("src.user_management_api.dao.base.BaseDAO.add")
async def test_user_add_failed(
        mock_base_add,
        mock_find_role,
        mock_db,
        mock_user_data,
        user_register_data
):
    """
    UserDAO.add() should raise RuntimeError when default USER role is missing.
    """
    # Arrange
    user = mock_user_data()
    mock_base_add.return_value = user
    mock_find_role.return_value = None

    # Act
    with pytest.raises(RuntimeError) as e:
        result = await UserDAO.add(mock_db, **user_register_data.model_dump())

    # Assert
    assert str(e.value) == "Default USER role is missing in the database."
    mock_base_add.assert_called_once_with(mock_db, **user_register_data.model_dump())
    mock_find_role.assert_called_once()
    mock_db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_get_all_success_not_filter(mock_db, mock_user_data):
    """
    UserDAO.get_all() should return all users when no filters are applied.
    """
    # Arrange
    user1 = mock_user_data()
    user2 = mock_user_data()

    mock_count_result = MagicMock()
    mock_count_result.scalar.return_value = 2

    mock_items_result = MagicMock()
    mock_items_result.scalars.return_value.all.return_value = [user1, user2]

    mock_db.execute = AsyncMock(side_effect=[mock_count_result, mock_items_result])

    pagination = UserPagination(page=1, size=30)

    user_filter = UserFilter()

    # Act
    items, total = await UserDAO.get_all(
        mock_db,
        pagination=pagination,
        role_condition=None,
        user_filter=user_filter
    )

    # Assert
    assert total == 2
    assert items == [user1, user2]

    assert mock_db.execute.call_count == 2
    mock_items_result.scalars.return_value.all.assert_called_once()


@pytest.mark.asyncio
async def test_get_all_success_filter(mock_db, mock_user_data):
    """
    UserDAO.get_all() should return filtered users when name filter is applied.
    """
    # Arrange
    user = mock_user_data()

    mock_count_result = MagicMock()
    mock_count_result.scalar.return_value = 1

    mock_items_result = MagicMock()
    mock_items_result.scalars.return_value.all.return_value = [user]

    mock_db.execute = AsyncMock(side_effect=[mock_count_result, mock_items_result])

    pagination = UserPagination(page=1, size=30)

    user_filter = UserFilter(name="old_name")

    # Act
    items, total = await UserDAO.get_all(
        mock_db,
        pagination=pagination,
        role_condition=None,
        user_filter=user_filter
    )
    # Assert
    assert total == 1
    assert items == [user]

    assert mock_db.execute.call_count == 2
    mock_items_result.scalars.return_value.all.assert_called_once()



@pytest.mark.asyncio
async def test_find_one_or_none_with_related_data_success(mock_db, mock_user_data):
    """
    UserDAO.find_one_or_none_with_related_data() should return user with related data when found.
    """
    # Arrange
    user = mock_user_data()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    mock_db.execute = AsyncMock(return_value=mock_result)

    # Act
    result = await UserDAO.find_one_or_none_with_related_data(mock_db, where=None, id=1)

    # Assert
    assert result == user
    mock_db.execute.assert_called_once()
    mock_result.scalar_one_or_none.assert_called_once()


@pytest.mark.asyncio
async def test_find_one_or_none_not_found(mock_db, mock_user_data):
    """
    UserDAO.find_one_or_none() should return None when no matching user exists.
    """
    # Arrange
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    # Act
    result = await UserDAO.find_one_or_none(mock_db, where=None)

    # Assert
    assert result is None
    mock_db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_update_user_role_success(mock_db):
    """
    UserDAO.update_user_role() should update roles except USER role.
    """
    # Arrange
    user_id = str(uuid.uuid4())

    mock_role_result = MagicMock()
    mock_role_result.scalar_one.return_value = 1
    mock_db.execute = AsyncMock(side_effect=[mock_role_result, None, None])

    # Act
    await UserDAO.update_user_role(mock_db, user_id, roles_id=[1,2,3])

    # Assert
    assert mock_db.execute.call_count == 3
    delete_call = mock_db.execute.call_args_list[1]
    delete_statement = delete_call[0][0]
    assert isinstance(delete_statement, Delete)

    insert_call = mock_db.execute.call_args_list[2]
    insert_statement, insert_values = insert_call[0]
    assert isinstance(insert_statement, Insert)
    assert insert_values == [
        {"user_id": uuid.UUID(user_id), "role_id": 2},
        {"user_id": uuid.UUID(user_id), "role_id": 3},
    ]


@pytest.mark.asyncio
async def test_update_user_role_empty_roles(mock_db):
    """
    UserDAO.update_user_role() should not insert anything when roles_id is empty.
    """
    # Arrange
    user_id = str(uuid.uuid4())

    mock_role_result = MagicMock()
    mock_role_result.scalar_one.return_value = 1
    mock_db.execute = AsyncMock(side_effect=[mock_role_result, None])

    # Act
    await UserDAO.update_user_role(mock_db, user_id, roles_id=[])

    # Assert
    assert mock_db.execute.call_count == 2
    insert_calls = [
        call for call in mock_db.execute.call_args_list if isinstance(call[0][0], Insert)
    ]
    assert insert_calls == []


@pytest.mark.asyncio
async def test_delete_by_id_success(mock_db):
    """
    UserDAO.delete_by_id() should User instance.
    """
    # Arrange
    user_id = str(uuid.uuid4())
    fake_user = MagicMock()
    mock_db.get = AsyncMock(return_value=fake_user)
    mock_db.delete = AsyncMock()
    mock_db.flush = AsyncMock()

    # Act
    await UserDAO.delete_by_id(mock_db, user_id)

    # Assert
    mock_db.get.assert_called_once_with(UserDAO.model, uuid.UUID(user_id))
    mock_db.delete.assert_called_once_with(fake_user)
    mock_db.flush.assert_called_once()


@pytest.mark.asyncio
async def test_delete_by_id_user_not_found(mock_db):
    """
    UserDAO.delete_by_id() should do nothing when user does not exist.
    """
    # Arrange
    user_id = str(uuid.uuid4())
    mock_db.get = AsyncMock(return_value=None)
    mock_db.delete = AsyncMock()
    mock_db.flush = AsyncMock()

    # Act
    await UserDAO.delete_by_id(mock_db, user_id)

    # Assert
    mock_db.get.assert_called_once()
    mock_db.delete.assert_not_called()
    mock_db.flush.assert_called_once()