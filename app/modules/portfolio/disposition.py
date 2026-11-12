from urllib.parse import quote

UNSAFE = frozenset({'"', chr(92)})


def attachment(filename: str) -> str:
    """Safe Content-Disposition: ASCII fallback plus RFC 5987 encoded original."""
    fallback = "".join(
        char if 32 <= ord(char) < 127 and char not in UNSAFE else "_" for char in filename
    )
    encoded = quote(filename, safe="")
    quotes = chr(39) * 2
    name = fallback or "download"
    return f'attachment; filename="{name}"; filename*=UTF-8{quotes}{encoded}'
