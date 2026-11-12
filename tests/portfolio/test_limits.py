import pytest

from app.modules.portfolio.limits import (
    MAX_BYTES,
    MIB,
    extension_of,
    media_allowed,
    resolution_allowed,
    size_allowed,
    valid_filename,
)


@pytest.mark.parametrize(
    "name",
    ["a/b.png", "a" + chr(92) + "b.png", "..secret.png", ".hidden.png", "x" * 121, ""],
)
def test_unsafe_filenames_are_refused(name: str) -> None:
    assert not valid_filename(name)


def test_safe_filename_and_case_insensitive_extension() -> None:
    assert valid_filename("My Photo (1).JPEG")
    assert extension_of("My Photo (1).JPEG") == ".jpeg"
    assert extension_of("noextension") == ""


def test_media_type_must_match_both_declaration_and_extension() -> None:
    assert media_allowed("image", "image/jpeg", "a.JPG")
    assert media_allowed("image", "image/webp", "a.webp")
    assert not media_allowed("image", "image/png", "a.jpg")
    assert not media_allowed("image", "application/pdf", "a.pdf")
    assert not media_allowed("video", "video/mp4", "a.mov")
    assert not media_allowed("link", "image/png", "a.png")


def test_size_bounds_follow_the_contract_table() -> None:
    assert MAX_BYTES == {"image": 10 * MIB, "pdf": 20 * MIB, "video": 100 * MIB}
    assert size_allowed("image", 10 * MIB)
    assert not size_allowed("image", 10 * MIB + 1)
    assert not size_allowed("pdf", 0)
    assert size_allowed("video", 100 * MIB)


def test_resolution_accepts_either_orientation_only() -> None:
    assert resolution_allowed(1920, 1080)
    assert resolution_allowed(1080, 1920)
    assert not resolution_allowed(1921, 1080)
    assert not resolution_allowed(1920, 1081)
