from fastapi import Request
from fastapi.exceptions import RequestValidationError


async def reject_body(request: Request) -> None:
    if await request.body():
        raise RequestValidationError([{"loc": ("body",), "type": "value_error"}])
