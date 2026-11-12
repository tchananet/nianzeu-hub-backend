MP4_BRANDS = frozenset(
    {b"isom", b"iso2", b"iso4", b"iso5", b"iso6", b"mp41", b"mp42", b"avc1", b"M4V ", b"mmp4"}
)


def detect(data: bytes) -> str | None:
    """Real signature sniffing; the declared Content-Type is never trusted alone."""
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    if data[4:8] == b"ftyp" and data[8:12] in MP4_BRANDS:
        return "video/mp4"
    return None
