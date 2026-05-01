from unittest.mock import MagicMock, patch

import phonenumbers
import pytest
from phonenumbers.phonenumberutil import NumberParseException
from pydantic_core import PydanticCustomError

from src.user_management_api.validators.auth import validate_phone_number_signup, validate_password


@patch("src.user_management_api.validators.auth.phonenumbers.format_number")
@patch("src.user_management_api.validators.auth.phonenumbers.is_valid_number")
@patch("src.user_management_api.validators.auth.phonenumbers.parse")
def test_validate_phone_number_signup_success(
        mock_parse,
        mock_is_valid_number,
        mock_format_number
):

    mock_parsed = MagicMock()
    mock_parse.return_value = mock_parsed
    mock_is_valid_number.return_value = True
    mock_format_number.return_value = "+375291234567"

    result = validate_phone_number_signup("+375 29 1234567")

    assert result == "+375291234567"

    mock_parse.assert_called_once_with("+375 29 1234567", None)
    mock_is_valid_number.assert_called_once()
    mock_format_number.assert_called_once_with(mock_parsed, phonenumbers.PhoneNumberFormat.E164)

def test_validate_phone_number_signup_phonenumber_None():
    assert validate_phone_number_signup(None) == None

def test_validate_phone_number_signup_empty_phonenumber():
    assert validate_phone_number_signup("") == None

@patch("src.user_management_api.validators.auth.phonenumbers.format_number")
@patch("src.user_management_api.validators.auth.phonenumbers.is_valid_number")
@patch("src.user_management_api.validators.auth.phonenumbers.parse")
def test_validate_phone_number_signup_not_valid(
        mock_parse,
        mock_is_valid_number,
        mock_format_number
):

    mock_parsed = MagicMock()
    mock_parse.return_value = mock_parsed
    mock_is_valid_number.return_value = False

    with pytest.raises(ValueError) as e:
        validate_phone_number_signup("+375 29 1234567")

    assert str(e.value) == "Invalid phone number"

    mock_parse.assert_called_once_with("+375 29 1234567", None)
    mock_is_valid_number.assert_called_once_with(mock_parsed)
    mock_format_number.assert_not_called()

@patch("src.user_management_api.validators.auth.phonenumbers.format_number")
@patch("src.user_management_api.validators.auth.phonenumbers.is_valid_number")
@patch("src.user_management_api.validators.auth.phonenumbers.parse")
def test_validate_phone_number_signup_wrong_format(
        mock_parse,
        mock_is_valid_number,
        mock_format_number
):

    mock_parsed = MagicMock()
    mock_parse.return_value = mock_parsed
    mock_is_valid_number.return_value = True
    mock_format_number.side_effect = NumberParseException(NumberParseException.INVALID_COUNTRY_CODE,
    "Invalid phone number format")

    with pytest.raises(ValueError) as e:
        validate_phone_number_signup("+375 29 1234567")

    assert str(e.value) == "Invalid phone number format"

    mock_parse.assert_called_once_with("+375 29 1234567", None)
    mock_is_valid_number.assert_called_once_with(mock_parsed)


def test_validate_password_success():
    result = validate_password("Password1!")
    assert isinstance(result, str)
    assert len(result) > 0

def test_validate_password_wrong_length():
    with pytest.raises(PydanticCustomError) as e:
        validate_password("Word1!")

    assert e.value.type == "password_too_short"
    assert e.value.message_template == "Password must contain 8 characters and more."

def test_validate_password_no_uppercase():
    with pytest.raises(PydanticCustomError) as e:
        validate_password("password1!")

    assert e.value.type == "password_no_uppercase"
    assert e.value.message_template == "Password must contain at least one uppercase letter."


def test_validate_password_no_lowercase():
    with pytest.raises(PydanticCustomError) as e:
        validate_password("PASSWORD1!")

    assert e.value.type == "password_no_lowercase"
    assert e.value.message_template == "Password must contain at least one lowercase letter."

def test_validate_password_no_digit():
    with pytest.raises(PydanticCustomError) as e:
        validate_password("Password!")

    assert e.value.type == "password_no_digit"
    assert e.value.message_template == "Password must contain at least one digit."

def test_validate_password_no_special_symbol():
    with pytest.raises(PydanticCustomError) as e:
        validate_password("Password1")

    assert e.value.type == "password_no_special_character"
    assert e.value.message_template == "Password must contain at least one special character."
