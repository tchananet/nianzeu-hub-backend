class AppError(Exception):
    def __init__(self, code: str, status: int, message: str = "Request failed") -> None:
        self.code, self.status, self.message = code, status, message
        super().__init__(code)


class EmailUnavailable(AppError):
    def __init__(self) -> None:
        super().__init__("EMAIL_UNAVAILABLE", 503, "Email service unavailable")


class DependencyUnavailable(AppError):
    def __init__(self) -> None:
        super().__init__("DEPENDENCY_UNAVAILABLE", 503, "Dependency unavailable")


class StorageMissing(Exception):
    """Caller maps absent upload to 409; absent published content to 503."""


class StorageInvalid(Exception):
    """Object or conditional copy is invalid; never report successful storage."""


class StorageUnavailable(DependencyUnavailable):
    pass


class RateLimited(AppError):
    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after
        super().__init__("RATE_LIMITED", 429, "Rate limit exceeded")
