from src.user_management_api.exceptions.auth import APIException


class S3StorageError(APIException):
    """
    Raised when errors exist while working with s3 storage.
    """
    status_code: int = 500
    detail: str = "Error while working with s3 storage."


class FileValidateError(APIException):
    """
    Raised when a user avatar is invalid.
    """
    status_code: int = 400
    detail: str = "The file is not downloaded"


class AuthorizationError(APIException):
    """
    Raised when errors exist while working with s3 storage.
    """
    status_code: int = 403
    detail: str = "Access is denied"

class ResourceNotFound(APIException):
    status_code: int = 404
    detail: str = "Resource is not found"