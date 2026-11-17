from typing import Literal

from fastapi import Request, Response

from app.core.config import Settings
from app.core.origins import is_allowed_origin
from app.shared.errors import AppError


class BrowserPolicy:
    def __init__(self, settings: Settings) -> None:
        self.environment = settings.environment
        self.frontend_origins = settings.allowed_origins()
        self.cross_site = settings.session_cross_site_enabled
        self.secure = settings.secure_cookies
        self.cookie_name = "__Host-session" if self.secure else "session_local"
        self.same_site: Literal["lax", "none"] = "none" if self.cross_site else "lax"

    def validate_origin(self, request: Request, required: bool) -> None:
        if not self.frontend_origins:
            return  # Open mode: no origin is configured, so none is enforced.
        origins = request.headers.getlist("origin")
        origin = origins[0] if len(origins) == 1 else None
        if (len(origins) > 1 or required and origin is None
                or origin is not None
                and not is_allowed_origin(origin, self.environment, self.frontend_origins)
                or not self.cross_site and request.headers.get("sec-fetch-site") == "cross-site"):
            raise AppError("ORIGIN_FORBIDDEN", 403, "Origin forbidden")

    def validate_mutation(self, request: Request) -> None:
        self.validate_origin(request, required=True)
        if request.url.path.endswith(("/auth/login", "/auth/register")):
            # JSON only. This is the defence against a cross-site form post, and it is
            # the effective one: a form can emit urlencoded, multipart or text/plain,
            # never application/json. A custom intent header used to be demanded here
            # too, but it guarded nothing this check and the origin check do not
            # already cover, while breaking Swagger and every direct client.
            media = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
            if media != "application/json":
                raise AppError("UNSUPPORTED_MEDIA_TYPE", 415, "JSON required")

    def validate_auth_read(self, request: Request) -> None:
        self.validate_origin(request, required=self.cross_site)

    def validate_csrf_read(self, request: Request) -> None:
        self.validate_origin(request, required=True)

    def read_token(self, request: Request) -> str | None:
        return request.cookies.get(self.cookie_name)

    def set_cookie(self, response: Response, token: str) -> None:
        response.set_cookie(self.cookie_name, token, max_age=604800, path="/",
                            secure=self.secure, httponly=True, samesite=self.same_site)

    def expire_cookie(self, response: Response) -> None:
        response.delete_cookie(self.cookie_name, path="/", secure=self.secure,
                               httponly=True, samesite=self.same_site)
