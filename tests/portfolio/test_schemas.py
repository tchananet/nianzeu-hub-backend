import pytest
from pydantic import ValidationError

from app.modules.portfolio.schemas import ItemCreate, UploadRequest, ValidateRequest

DIGEST = "a" * 64
ITEM = "00000000-0000-4000-8000-000000000001"


def upload(**overrides: object) -> dict[str, object]:
    return {
        "item_id": ITEM,
        "filename": "shot.png",
        "media_type": "image/png",
        "size_bytes": 1024,
        "sha256": DIGEST,
        **overrides,
    }


def test_link_type_and_unknown_fields_are_refused() -> None:
    with pytest.raises(ValidationError):
        ItemCreate.model_validate({"title": "t", "description": "", "type": "link"})
    with pytest.raises(ValidationError):
        ItemCreate.model_validate(
            {"title": "t", "description": "", "type": "image", "profile_id": ITEM}
        )
    assert ItemCreate.model_validate({"title": "t", "description": "", "type": "image"})


@pytest.mark.parametrize(
    "overrides",
    [
        {"sha256": "A" * 64},
        {"sha256": "a" * 63},
        {"size_bytes": 0},
        {"size_bytes": "1024"},
        {"filename": "../escape.png"},
        {"filename": ".hidden.png"},
        {"size_bytes": 104857601},
        {"item_id": "not-a-uuid"},
    ],
)
def test_upload_request_rejects_invalid_declarations(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        UploadRequest.model_validate(upload(**overrides))


def test_upload_request_accepts_a_valid_declaration() -> None:
    parsed = UploadRequest.model_validate(upload())
    assert parsed.filename == "shot.png" and parsed.sha256 == DIGEST
    assert ValidateRequest.model_validate({"upload_id": ITEM})
    with pytest.raises(ValidationError):
        ValidateRequest.model_validate({"upload_id": ITEM, "force": True})
