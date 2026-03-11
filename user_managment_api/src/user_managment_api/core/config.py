"""
Application configuration settings.

Defines global constants such as application name, debug mode,
and database connection URL.
"""


class Settings:
    """Global application configuration settings."""
    APP_NAME: str = "user_managment_api"
    DEBUG: bool = True

    MEDIA_DIR = "/media"