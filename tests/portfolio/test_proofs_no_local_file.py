"""Proof 8 — not one uploaded byte reaches the container filesystem.

Dynamic: a full validation of each accepted type runs with every file-creating
primitive replaced by a guard that fails loudly. Static: no portfolio module even
names such a primitive, so untested code paths cannot regress silently.
"""

import re
from pathlib import Path

import pytest

import app.modules.portfolio as portfolio
from app.modules.portfolio.schemas import ValidateRequest
from app.modules.portfolio.validation import ValidationService
from tests.portfolio import samples, video_samples
from tests.portfolio.fakes import FakeStorage
from tests.portfolio.items import item
from tests.portfolio.proofs_rows import reservation
from tests.portfolio.proofs_wiring import PROFILE, QUARANTINE, USER, wire
from tests.portfolio.session_double import ScriptedSession

WATCHED = (
    "builtins.open",
    "os.open",
    "os.mkdir",
    "tempfile.mkstemp",
    "tempfile.mkdtemp",
    "tempfile.NamedTemporaryFile",
    "tempfile.TemporaryFile",
    "tempfile.SpooledTemporaryFile",
)
FORBIDDEN = re.compile(
    r"(?<![\w.])(open|mkstemp|mkdtemp)\s*\(|\b(tempfile|shutil|NamedTemporaryFile"
    r"|TemporaryFile)\b|os\.write|write_bytes|write_text"
)


def guard(name: str):  # noqa: ANN201
    def refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError(f"{name} reached the filesystem: {args!r} {kwargs!r}")

    return refuse


def validate(kind: str, media_type: str, filename: str, payload: bytes) -> str:
    row = item(PROFILE, state="pending", type=kind)
    upload = reservation(row.id, payload, media_type=media_type, filename=filename)
    storage = FakeStorage()
    storage.put(QUARANTINE, upload.quarantine_key, payload, media_type)
    context, _, factory = wire(
        ScriptedSession(PROFILE, row, upload),
        ScriptedSession(row, upload),
        storage=storage,
    )
    result = ValidationService(context).validate(
        USER, row.id, ValidateRequest(upload_id=upload.id)
    )
    assert factory.exhausted()
    return result.state


@pytest.mark.parametrize(
    ("kind", "media_type", "filename", "builder"),
    [
        ("image", "image/png", "shot.png", lambda: samples.image_bytes("PNG")),
        ("image", "image/jpeg", "shot.jpg", lambda: samples.image_bytes("JPEG")),
        ("pdf", "application/pdf", "doc.pdf", samples.pdf_bytes),
        ("video", "video/mp4", "clip.mp4", video_samples.mp4_bytes),
    ],
)
def test_validating_an_upload_never_creates_a_file(
    monkeypatch: pytest.MonkeyPatch, kind: str, media_type: str, filename: str, builder
) -> None:  # noqa: ANN001
    payload = builder()  # built before the watch: only validation is under scrutiny
    for target in WATCHED:
        monkeypatch.setattr(target, guard(target))
    assert validate(kind, media_type, filename, payload) == "validated"


def test_no_portfolio_module_names_a_filesystem_write_primitive() -> None:
    root = Path(str(portfolio.__file__)).parent
    offenders = [
        (path.name, match.group(0))
        for path in sorted(root.glob("*.py"))
        for match in FORBIDDEN.finditer(path.read_text(encoding="utf-8"))
    ]
    assert offenders == [], "Only in-memory buffers are allowed in this module"
