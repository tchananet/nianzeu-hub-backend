from fastapi import Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.modules.discovery.schemas import SearchQuery

SINGLE = frozenset({"q", "city", "country_code", "availability", "experience_level"})
NUMERIC = frozenset({"page", "page_size"})
MULTI = "skill_id"


def invalid(name: str) -> RequestValidationError:
    return RequestValidationError([{"loc": ("query", name), "type": "value_error"}])


def parse_search(request: Request) -> SearchQuery:
    """Strict allowlist per http.md: unknown or repeated query rejected, except skill_id."""
    values: dict[str, object] = {}
    for name in request.query_params:
        entries = request.query_params.getlist(name)
        if name == MULTI:
            values[MULTI] = entries
            continue
        if (name not in SINGLE and name not in NUMERIC) or len(entries) != 1:
            raise invalid(name)
        if name in NUMERIC:
            raw = entries[0]
            if not raw.isascii() or not raw.isdecimal() or len(raw) > 5:
                raise invalid(name)
            values[name] = int(raw)
        else:
            values[name] = entries[0]
    try:
        return SearchQuery.model_validate(values)
    except ValidationError as error:
        raise RequestValidationError([
            {"loc": ("query", *item["loc"]), "type": "value_error"}
            for item in error.errors(include_input=False)
        ]) from None
