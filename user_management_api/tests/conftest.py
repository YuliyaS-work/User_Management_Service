import uuid
from datetime import datetime

import pytest
from freezegun import freeze_time
from unittest.mock import patch, AsyncMock, MagicMock


@pytest.fixture
def freezer_time():
    with freeze_time("2026-04-28 12:00:00"):
        assert datetime.now() == datetime(2026,4,28,12,0,0)
        yield


@pytest.fixture
def mock_db():
    mock = AsyncMock()

    with patch("src.user_management_api.services.auth.AsyncSession", mock):
        yield mock


@pytest.fixture
def mock_db_user():
    mock = AsyncMock()

    with patch("src.user_management_api.services.user.AsyncSession", mock):
        yield mock

class FakeRequest:
    def __init__(self, cookies):
        self.cookies = cookies
        self.base_url = "http://testserver/"
        self.app = MagicMock()

@pytest.fixture
def get_fake_request():
    fake_request = FakeRequest(cookies={
        "access_token": "fake_access_token",
        "refresh_token": "fake_refresh_token"
        }
    )
    return fake_request


@pytest.fixture
def fake_response():
    return MagicMock()


@pytest.fixture
def fake_request():
    return MagicMock()


@pytest.fixture
def fake_background_tasks():
    bg = MagicMock()
    bg.add_task = MagicMock()
    return bg

@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = uuid.uuid4()
    user.name = "name"
    user.surname = "surname"
    user.username = "username"
    user.phone_number = "+375291111111"
    user.email = "user@example.com"
    user.image_s3_path = "image.webp"
    user.is_blocked = False
    user.created_at = datetime.now()
    user.modified_at = datetime.now()

    role = MagicMock()
    role.id = 1
    role.role_name.value = "USER"
    user.roles = [role]

    group = MagicMock()
    group.id = 1
    group.name = "First"
    user.group = group

    return user

@pytest.fixture
def mock_redis():
    mock = AsyncMock()
    return mock
