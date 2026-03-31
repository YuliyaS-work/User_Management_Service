"""
Validators model used for pydantic models.
Provides validation are used for incoming data.
"""

import phonenumbers


def serialize_phone(self, value):
    if value is None:
        return None
    return phonenumbers.format_number(value, phonenumbers.PhoneNumberFormat.E164)