import pytest

from app.modules.portfolio import inspection, limits
from app.modules.portfolio.deadline import Deadline
from app.modules.portfolio.errors import Rejected
from tests.portfolio import samples


@pytest.mark.parametrize(
    ("media_type", "fmt"),
    [("image/jpeg", "JPEG"), ("image/png", "PNG"), ("image/webp", "WEBP")],
)
def test_declared_formats_are_decoded(media_type: str, fmt: str) -> None:
    inspection.inspect("image", media_type, samples.image_bytes(fmt), Deadline())


def test_forged_content_type_is_unsupported_media() -> None:
    with pytest.raises(Rejected) as error:
        inspection.inspect("image", "image/png", samples.image_bytes("JPEG"), Deadline())
    assert error.value.error.status == 415


def test_corrupted_bytes_are_an_invalid_upload() -> None:
    payload = bytearray(samples.image_bytes("PNG"))
    payload[30:60] = b"\x00" * 30
    with pytest.raises(Rejected) as error:
        inspection.inspect("image", "image/png", bytes(payload), Deadline())
    assert error.value.rejection_code == "IMAGE_UNREADABLE"
    assert error.value.error.status == 400


def test_pixel_budget_is_enforced_before_decoding(monkeypatch: pytest.MonkeyPatch) -> None:
    assert limits.MAX_PIXELS == 25_000_000
    monkeypatch.setattr("app.modules.portfolio.inspect_image.MAX_PIXELS", 10)
    with pytest.raises(Rejected) as error:
        inspection.inspect("image", "image/png", samples.image_bytes("PNG"), Deadline())
    assert error.value.rejection_code == "IMAGE_PIXELS"
