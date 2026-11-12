from app.modules.portfolio import signatures
from tests.portfolio import samples, video_samples


def test_real_signatures_are_detected_per_type() -> None:
    assert signatures.detect(samples.image_bytes("JPEG")) == "image/jpeg"
    assert signatures.detect(samples.image_bytes("PNG")) == "image/png"
    assert signatures.detect(samples.image_bytes("WEBP")) == "image/webp"
    assert signatures.detect(samples.pdf_bytes()) == "application/pdf"
    assert signatures.detect(video_samples.mp4_bytes()) == "video/mp4"


def test_unknown_and_truncated_payloads_are_not_identified() -> None:
    assert signatures.detect(b"") is None
    assert signatures.detect(b"GIF89a" + b"0" * 32) is None
    assert signatures.detect(b"%PD") is None
    assert signatures.detect(b"\x00\x00\x00\x18ftypQQQQ") is None
