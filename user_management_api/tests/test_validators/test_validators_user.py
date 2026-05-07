import uuid
from typing import Any
from unittest.mock import patch, MagicMock

import phonenumbers

from src.user_management_api.validators.user import serialize_phone, serialize_uuid


@patch("src.user_management_api.validators.user.phonenumbers.format_number")
def test_serialize_phone_success(mock_format_number):
    """
    serialize_phone() should format a PhoneNumber object into E164 string.
    """
    # Arrange
    mock_number = MagicMock()
    mock_format_number.return_value = "+375291234567"

    # Act
    result = serialize_phone(None,mock_number)

    # Assert
    assert result == "+375291234567"
    mock_format_number.assert_called_once_with(mock_number, phonenumbers.PhoneNumberFormat.E164)


def test_serialize_phone_none():
    """
    serialize_phone() should return None when value is None.
    """
    # Act/Assert
    assert serialize_phone(Any, None) is None


def test_serialize_phone_str_type():
    """
    serialize_phone() should return the string when value is already a string.
    """
    # Act
    result = serialize_phone(Any, "+375291234567")

    # Assert
    assert isinstance(result, str)


def test_serialize_uuid_success():
    """
    serialize_uuid() should convert UUID to a string.
    """
    # Act
    result = serialize_uuid(None, uuid.uuid4())

    # Assert
    assert isinstance(result, str)