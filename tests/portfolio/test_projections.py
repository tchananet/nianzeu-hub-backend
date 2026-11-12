import pytest

from app.modules.portfolio import projections
from tests.portfolio import items


def test_owner_hides_file_metadata_before_validation() -> None:
    dto = projections.owner(items.item(state="rejected", rejection_code="INVALID_UPLOAD"))
    assert dto.file is None and dto.rejection_code == "INVALID_UPLOAD"
    assert dto.validated_at is None and dto.published_at is None


def test_owner_exposes_only_the_contract_fields() -> None:
    dto = projections.owner(items.validated())
    assert set(dto.model_dump()) == {
        "id", "profile_id", "title", "description", "type", "state", "created_at",
        "updated_at", "validated_at", "published_at", "file", "rejection_code",
    }
    assert dto.file is not None
    assert set(dto.model_dump()["file"]) == {"filename", "media_type", "size_bytes", "sha256"}
    assert "items/x/y" not in str(dto.model_dump())


def test_public_projection_uses_a_relative_api_content_url() -> None:
    row = items.published()
    dto = projections.public(row)
    assert dto.content_url == f"/api/v1/portfolio/{row.id}/content"
    assert set(dto.model_dump()) == {
        "id", "profile_id", "title", "description", "type", "published_at", "file", "content_url",
    }
    assert "object_key" not in dto.model_dump()


def test_public_projection_refuses_unpublished_items() -> None:
    with pytest.raises(ValueError):
        projections.public(items.validated())
    with pytest.raises(ValueError):
        projections.public(items.item())
