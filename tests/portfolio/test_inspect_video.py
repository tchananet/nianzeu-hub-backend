import pytest

from app.modules.portfolio import inspection, limits
from app.modules.portfolio.deadline import Deadline
from app.modules.portfolio.errors import Rejected
from tests.portfolio.video_samples import mp4_bytes


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
