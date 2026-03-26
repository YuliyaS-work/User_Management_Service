class AuthenticationException(Exception):
    def __init__(self, detail: str = "The user is not authenticated"):
        self.detail = detail


class ConflictException(Exception):
    def __init__(self, detail: str = "The user already exists"):
        self.detail = detail