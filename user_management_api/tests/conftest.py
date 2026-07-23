import uuid
from datetime import datetime, timezone, timedelta

import pytest
from freezegun import freeze_time
from unittest.mock import AsyncMock, MagicMock

from src.user_management_api.models import User, Group
from src.user_management_api.schemas.auth import UserRegister, ResetPasswordRequest


@pytest.fixture
def freezer_time():
    """
    Freeze system time to a fixed datatime for tests connected with tokens"
    """
    with freeze_time("2026-04-28 12:00:00"):
        assert datetime.now() == datetime(2026,4,28,12,0,0)
        yield


@pytest.fixture
def mock_db():
    """
    Async mock representing the database layer.
    """
    mock = AsyncMock()
    return mock


@pytest.fixture
def mock_redis():
    """
    Async mock representing Redis storage.
    """
    mock = AsyncMock()
    return mock


@pytest.fixture
def mock_s3():
    """
    Async mock representing S3 storage.
    """
    s3 = AsyncMock()
    return s3


class FakeRequest:
    """
    Fake request object used for testing authentication handlers.
    """
    def __init__(self, cookies):
        self.cookies = cookies
        self.base_url = "http://testserver/"
        self.app = MagicMock()

@pytest.fixture
def get_fake_request():
    """
    Fake HTTP request with predefined access/refresh tokens.
    """
    fake_request = FakeRequest(cookies={
        "access_token": "fake_access_token",
        "refresh_token": "fake_refresh_token"
        }
    )
    return fake_request


@pytest.fixture
def fake_request():
    """
    Mocked HTTP request object for user's endpoints.
    """
    return MagicMock()


@pytest.fixture
def fake_response():
    """
    Mocked HTTP response object.
    """
    return MagicMock()


@pytest.fixture
def fake_background_tasks():
    """
    Mocked background tasks container with add_task stub.
    """
    bg = MagicMock()
    bg.add_task = MagicMock()
    return bg


@pytest.fixture
def mock_user():
    """
    Mocked user entity with roles and group for authentication/authorization tests.
    """
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
def user_register_data():
    """
    Base UserRegister payload used across registration tests.
    """
    return UserRegister(
        name="name",
        surname="surname",
        username="username",
        password="Password1!",
        phone_number="+375291111111",
        email="user@example.com"
    )


@pytest.fixture
def mock_user_data():
    def _mock_user_data():
        return User(
            id= uuid.uuid4(),
            name="old_name",
            surname="surname",
            username="username",
            phone_number="+375291111111",
            email="user@example.com",
            image_s3_path="image.webp",
            is_blocked=False,
            created_at=datetime.now().isoformat(),
            modified_at=datetime.now().isoformat(),
            group=Group(id=1, name="First"),
            roles=[]
        )
    return _mock_user_data


@pytest.fixture
def reset_password_payload():
    """
    Decoded reset-password token payload to test resetting new password.
    """
    return type("Payload", (), {
        "sub": "user@example.com",
        "exp": int((datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc) + timedelta(minutes=10)).timestamp()),
        "type": "reset_password",
        "jti": "12345678123456781234567812345678"
    })()


@pytest.fixture
def reset_password_request():
    """
    Common ResetPasswordRequest object to test resetting new password.
    """
    return ResetPasswordRequest(token="fake_token", new_password="new_password")