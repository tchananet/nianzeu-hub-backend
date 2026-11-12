from app.modules.portfolio import inspect_image, inspect_pdf, inspect_video, signatures
from app.modules.portfolio.deadline import Deadline
from app.modules.portfolio.errors import rejected_invalid, rejected_media, rejected_too_large
from app.modules.portfolio.limits import MAX_BYTES, media_allowed


def verify_declaration(item_type: str, media_type: str, filename: str, size_bytes: int) -> None:
    if not media_allowed(item_type, media_type, filename):
        raise rejected_media()
    if size_bytes > MAX_BYTES[item_type]:
        raise rejected_too_large()


def inspect(item_type: str, media_type: str, data: bytes, deadline: Deadline) -> None:
    """Signature plus real format parsing; Content-Type alone never grants acceptance."""
    if signatures.detect(data) != media_type:
        raise rejected_media()
    if item_type == "image":
        inspect_image.inspect(data, media_type, deadline)
    elif item_type == "pdf":
        inspect_pdf.inspect(data, deadline)
    elif item_type == "video":
        inspect_video.inspect(data, deadline)
    else:
        raise rejected_invalid("UNKNOWN_TYPE")
