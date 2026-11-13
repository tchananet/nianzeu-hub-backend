import pytest

from app.modules.portfolio import inspection, limits
from app.modules.portfolio.deadline import Deadline
from app.modules.portfolio.errors import Rejected
from tests.portfolio import samples


def reject(payload: bytes) -> str:
    with pytest.raises(Rejected) as error:
        inspection.inspect("pdf", "application/pdf", payload, Deadline())
    assert error.value.error.code == "INVALID_UPLOAD"
    return error.value.rejection_code


def test_plain_document_is_parsed() -> None:
    inspection.inspect("pdf", "application/pdf", samples.pdf_bytes(3), Deadline())


def test_encryption_javascript_attachments_and_actions_are_refused() -> None:
    assert reject(samples.pdf_encrypted()) == "PDF_ENCRYPTED"
    assert reject(samples.pdf_with_javascript()) == "PDF_JAVASCRIPT"
    assert reject(samples.pdf_with_attachment()) == "PDF_EMBEDDED_FILE"
    assert reject(samples.pdf_with_open_action()) == "PDF_AUTO_ACTION"
    assert reject(samples.pdf_with_launch_annotation()) == "PDF_AUTO_ACTION"
    # Carried by an annotation, so outside the catalog name tree attachment_list reads.
    assert reject(samples.pdf_with_attachment_annotation()) == "PDF_EMBEDDED_FILE"


def test_page_budget_follows_the_contract() -> None:
    assert limits.MAX_PDF_PAGES == 100
    assert reject(samples.pdf_bytes(101)) == "PDF_PAGES"
    inspection.inspect("pdf", "application/pdf", samples.pdf_bytes(100), Deadline())


def test_unparseable_document_is_refused() -> None:
    assert reject(b"%PDF-1.7\n" + b"garbage" * 20) == "PDF_UNREADABLE"
