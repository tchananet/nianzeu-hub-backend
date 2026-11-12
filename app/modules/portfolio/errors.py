from app.shared.errors import AppError


def not_found() -> AppError:
    """Absent, private or third-party items are indistinguishable by contract."""
    return AppError("NOT_FOUND", 404, "Item not found")


def profile_required() -> AppError:
    return AppError("PROFILE_REQUIRED", 409, "Profile required")


def invalid_state() -> AppError:
    return AppError("INVALID_STATE", 409, "Transition not allowed")


def quota_exceeded() -> AppError:
    return AppError("QUOTA_EXCEEDED", 409, "Portfolio quota exceeded")


def upload_expired() -> AppError:
    return AppError("UPLOAD_EXPIRED", 409, "Upload expired")


def invalid_upload() -> AppError:
    return AppError("INVALID_UPLOAD", 400, "Upload content rejected")


def file_too_large() -> AppError:
    return AppError("FILE_TOO_LARGE", 413, "File too large")


def unsupported_media() -> AppError:
    return AppError("UNSUPPORTED_MEDIA_TYPE", 415, "Unsupported media type")


def validation_busy() -> AppError:
    return AppError("VALIDATION_BUSY", 503, "Validation capacity saturated")


class Rejected(Exception):
    """Content refusal: the item becomes rejected and the reservation is released."""

    def __init__(self, rejection_code: str, error: AppError) -> None:
        self.rejection_code, self.error = rejection_code, error
        super().__init__(rejection_code)


def rejected_invalid(reason: str) -> Rejected:
    return Rejected(reason, invalid_upload())


def rejected_too_large() -> Rejected:
    return Rejected("FILE_TOO_LARGE", file_too_large())


def rejected_media() -> Rejected:
    return Rejected("UNSUPPORTED_MEDIA_TYPE", unsupported_media())


def rejected_limit() -> Rejected:
    return Rejected("VALIDATION_LIMIT", invalid_upload())
