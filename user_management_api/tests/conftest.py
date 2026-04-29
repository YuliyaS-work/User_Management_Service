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


class FakeRequest():
    def __init__(self, cookies):
        self.cookies = cookies

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