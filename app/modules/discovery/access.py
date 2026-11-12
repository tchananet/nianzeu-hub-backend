from typing import Protocol

from fastapi import Request


class PublicReads(Protocol):
    """Shared public-read quota of http.md: 120/min/IP, scope ``public_json``.

    X01 injects the P01 ``ProfileAccess`` instance so profiles, contacts and search
    consume one single counter group; discovery never owns a second quota.
    """

    def public_limit(self, request: Request) -> None: ...
