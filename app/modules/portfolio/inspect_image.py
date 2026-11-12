from io import BytesIO

from PIL import Image, UnidentifiedImageError

from app.modules.portfolio.deadline import Deadline
from app.modules.portfolio.errors import Rejected, rejected_invalid, rejected_media
from app.modules.portfolio.limits import MAX_PIXELS

FORMATS = {"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}


def inspect(data: bytes, media_type: str, deadline: Deadline) -> None:
    """Full decode after an explicit pixel-budget check, so decode memory stays bounded."""
    deadline.check()
    try:
        with Image.open(BytesIO(data)) as image:
            if image.format != FORMATS[media_type]:
                raise rejected_media()
            width, height = image.size
            if width < 1 or height < 1 or width * height > MAX_PIXELS:
                raise rejected_invalid("IMAGE_PIXELS")
            deadline.check()
            image.load()
    except Rejected:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise rejected_invalid("IMAGE_UNREADABLE") from None
