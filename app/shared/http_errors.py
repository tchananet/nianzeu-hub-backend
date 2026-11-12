import logging
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse

from app.shared.errors import AppError, RateLimited

logger = logging.getLogger("app.errors")


def error_response(
    request: Request,
    code: str,
    status: int,
    message: str,
    details: list[dict[str, str]] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None) or str(uuid4())
    return JSONResponse(
        {
            "error": {"code": code, "message": message, "details": details or []},
            "request_id": request_id,
        },
        status_code=status,
        headers={
            **(headers or {}),
            "X-Request-ID": request_id,
            "Cache-Control": "no-store",
            "Vary": "Origin",
        },
    )


async def app_error(request: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, AppError)
    headers = {"Retry-After": str(error.retry_after)} if isinstance(error, RateLimited) else {}
    return error_response(request, error.code, error.status, error.message, headers=headers)


async def validation_error(request: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, RequestValidationError)
    if any(item["type"] == "json_invalid" for item in error.errors()):
        return error_response(request, "INVALID_JSON", 400, "Invalid JSON")
    details = [
        {"field": ".".join(map(str, item["loc"])), "code": "invalid"} for item in error.errors()
    ]
    return error_response(request, "VALIDATION_ERROR", 422, "Invalid request", details)


async def http_error(request: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, HTTPException)
    codes = {
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        401: "AUTH_REQUIRED",
        403: "ORIGIN_FORBIDDEN",
        413: "BODY_TOO_LARGE",
        415: "UNSUPPORTED_MEDIA_TYPE",
    }
    headers = (
        {"Allow": error.headers["Allow"]} if error.headers and "Allow" in error.headers else {}
    )
    return error_response(
        request,
        codes.get(error.status_code, "INTERNAL_ERROR"),
        error.status_code,
        "Request failed",
        headers=headers,
    )


async def internal_error(request: Request, error: Exception) -> JSONResponse:
    # Never log exception text, SQL parameters, request bodies or secret-bearing URLs.
    logger.error(
        "Unhandled request error",
        extra={"code": "INTERNAL_ERROR", "request_id": getattr(request.state, "request_id", None)},
    )
    return error_response(request, "INTERNAL_ERROR", 500, "Internal server error")


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error)
    app.add_exception_handler(RequestValidationError, validation_error)
    app.add_exception_handler(HTTPException, http_error)
    app.add_exception_handler(Exception, internal_error)
