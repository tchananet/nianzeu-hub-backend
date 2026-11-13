from io import BytesIO

import av
import pytest

from app.modules.portfolio import inspection, limits
from app.modules.portfolio.deadline import Deadline
from app.modules.portfolio.errors import Rejected
from tests.portfolio.video_samples import lying_mp4_bytes, mp4_bytes


def reject(payload: bytes) -> Rejected:
    with pytest.raises(Rejected) as error:
        inspection.inspect("video", "video/mp4", payload, Deadline())
    return error.value


def test_h264_with_optional_aac_audio_is_accepted() -> None:
    inspection.inspect("video", "video/mp4", mp4_bytes(), Deadline())
    inspection.inspect("video", "video/mp4", mp4_bytes(audio="aac"), Deadline())


def test_other_codecs_are_unsupported_media() -> None:
    assert reject(mp4_bytes(codec="mpeg4")).error.status == 415
    assert reject(mp4_bytes(audio="mp3")).error.status == 415


def test_duration_budget_follows_the_contract() -> None:
    assert limits.MAX_VIDEO_SECONDS == 120
    rejection = reject(mp4_bytes(frames=1250))
    assert rejection.rejection_code == "VIDEO_DURATION"
    assert rejection.error.status == 400


def test_resolution_budget_is_enforced(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.modules.portfolio.limits.MAX_VIDEO_EDGES", (32, 24))
    assert reject(mp4_bytes()).rejection_code == "VIDEO_RESOLUTION"


def test_unparseable_and_non_mp4_payloads_are_refused() -> None:
    truncated = mp4_bytes()[:40]
    assert reject(truncated).error.status in (400, 415)


def test_a_header_lying_about_its_duration_is_refused_on_its_packets() -> None:
    """QA O01 D4: the demuxed stamps decide, never container.duration."""
    payload = lying_mp4_bytes(frames=1250, declared_seconds=2.0)
    with av.open(BytesIO(payload), "r") as container:
        assert container.duration is not None
        assert container.duration / av.time_base == 2.0  # the header claims 2 s...
    rejection = reject(payload)  # ...the packets carry 125 s.
    assert rejection.rejection_code == "VIDEO_DURATION"
    assert rejection.error.status == 400


def test_an_honest_short_video_still_passes_the_cross_check() -> None:
    inspection.inspect("video", "video/mp4", lying_mp4_bytes(10, 1.0), Deadline())


def test_an_unbounded_packet_budget_is_refused_rather_than_trusted(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.modules.portfolio.inspect_video.MAX_PACKETS", 3)
    assert reject(mp4_bytes()).rejection_code == "VALIDATION_LIMIT"
