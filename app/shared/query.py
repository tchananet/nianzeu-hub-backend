from fastapi import Request
from fastapi.exceptions import RequestValidationError

from app.shared.dto import Pagination


def pagination(request: Request) -> Pagination:
    """Dependency for pagination-only endpoints; filtered routes validate their own allowlist."""
    values: dict[str, int] = {}
    for key in request.query_params:
        raw = request.query_params.getlist(key)
        if (
            key not in {"page", "page_size"}
            or len(raw) != 1
            or not raw[0].isascii()
            or not raw[0].isdecimal()
            or len(raw[0]) > 5
        ):
            raise RequestValidationError([{"loc": ("query", key), "type": "value_error"}])
        values[key] = int(raw[0])
    from pydantic import ValidationError

    try:
        return Pagination.model_validate(values)
    except ValidationError as error:
        raise RequestValidationError(
            [
                {"loc": ("query", *item["loc"]), "type": "value_error"}
                for item in error.errors(include_input=False)
            ]
        ) from None
