from fastapi import Request
from fastapi.exceptions import RequestValidationError


def reject_query(request: Request) -> None:
    if request.query_params:
        raise RequestValidationError([
            {"loc": ("query", key), "type": "value_error"} for key in request.query_params
        ])
