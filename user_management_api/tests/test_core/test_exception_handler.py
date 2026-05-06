from unittest.mock import patch

import pytest
from starlette.responses import JSONResponse

from src.user_management_api.core.exception_handlers import api_exception_handler
from src.user_management_api.exceptions.auth import APIException


@pytest.mark.asyncio
@patch("src.user_management_api.core.exception_handlers.logger.warning")
async def test_api_exception_handler_api_exception(
        mock_warning,
        fake_request
):
    fake_request.url.path = "/test"

    exc = APIException(detail="Fake error")
    exc.status_code = 400
    response: JSONResponse = await api_exception_handler(fake_request, exc)

    assert response.status_code == 400

    body = response.body.decode()
    assert "Fake error" in body
    mock_warning.assert_called_once()


@pytest.mark.asyncio
@patch("src.user_management_api.core.exception_handlers.logger.exception")
async def test_api_exception_handler_unexpected_exception(
        mock_warning,
        fake_request
):
    fake_request.url.path = "/test"

    exc = ValueError("Fake error")
    response: JSONResponse = await api_exception_handler(fake_request, exc)

    assert response.status_code == 500

    body = response.body.decode()
    assert "Internal server error" in body
    mock_warning.assert_called_once()