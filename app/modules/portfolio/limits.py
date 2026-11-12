from typing import Final

MIB: Final = 1048576
VALIDATION_MEMORY_BYTES: Final = 128 * MIB
VALIDATION_TIMEOUT_SECONDS: Final = 30
STREAM_CHUNK_BYTES: Final = 262144

MEDIA: Final[dict[str, dict[str, tuple[str, ...]]]] = {
    "image": {
        "image/jpeg": (".jpg", ".jpeg"),
        "image/png": (".png",),
        "image/webp": (".webp",),
    },
    "pdf": {"application/pdf": (".pdf",)},
    "video": {"video/mp4": (".mp4",)},
}
MAX_BYTES: Final[dict[str, int]] = {"image": 10 * MIB, "pdf": 20 * MIB, "video": 100 * MIB}
MAX_PIXELS: Final = 25_000_000
MAX_PDF_PAGES: Final = 100
MAX_VIDEO_SECONDS: Final = 120
MAX_VIDEO_EDGES: Final = (1920, 1080)


def valid_filename(name: str) -> bool:
    """Basename only: no separator, control character, parent reference or leading dot."""
    return (
        1 <= len(name) <= 120
        and not any(char in name for char in "/\\")
        and all(ord(char) >= 32 and ord(char) != 127 for char in name)
        and ".." not in name
        and not name.startswith(".")
    )


def extension_of(name: str) -> str:
    return name[name.rindex(".") :].lower() if "." in name else ""


def media_allowed(item_type: str, media_type: str, filename: str) -> bool:
    allowed = MEDIA.get(item_type, {})
    return media_type in allowed and extension_of(filename) in allowed[media_type]


def size_allowed(item_type: str, size_bytes: int) -> bool:
    return 1 <= size_bytes <= MAX_BYTES[item_type]


def resolution_allowed(width: int, height: int) -> bool:
    long_edge, short_edge = MAX_VIDEO_EDGES
    return max(width, height) <= long_edge and min(width, height) <= short_edge
