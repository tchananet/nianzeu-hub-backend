from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PyPdfError
from pypdf.generic import DictionaryObject

from app.modules.portfolio.deadline import Deadline
from app.modules.portfolio.errors import Rejected, rejected_invalid
from app.modules.portfolio.limits import MAX_PDF_PAGES

ACTIONS = frozenset({"/JavaScript", "/Launch", "/SubmitForm", "/ImportData", "/GoToR", "/Movie"})


def reject_catalog(root: DictionaryObject) -> None:
    if "/OpenAction" in root or "/AA" in root:
        raise rejected_invalid("PDF_AUTO_ACTION")
    names = root.get("/Names")
    resolved = names.get_object() if names is not None else None
    if isinstance(resolved, DictionaryObject):
        if "/JavaScript" in resolved:
            raise rejected_invalid("PDF_JAVASCRIPT")
        if "/EmbeddedFiles" in resolved:
            raise rejected_invalid("PDF_EMBEDDED_FILE")


def reject_page(page: DictionaryObject) -> None:
    if "/AA" in page:
        raise rejected_invalid("PDF_AUTO_ACTION")
    annotations = page.get("/Annots")
    entries = annotations.get_object() if annotations is not None else []
    for annotation in entries if isinstance(entries, list) else []:
        target = annotation.get_object()
        action = target.get("/A") if isinstance(target, DictionaryObject) else None
        resolved = action.get_object() if action is not None else None
        if isinstance(resolved, DictionaryObject) and resolved.get("/S") in ACTIONS:
            raise rejected_invalid("PDF_AUTO_ACTION")


def inspect(data: bytes, deadline: Deadline) -> None:
    deadline.check()
    try:
        reader = PdfReader(BytesIO(data), strict=False)
        if reader.is_encrypted:
            raise rejected_invalid("PDF_ENCRYPTED")
        reject_catalog(reader.root_object)
        if any(True for _ in reader.attachment_list):
            raise rejected_invalid("PDF_EMBEDDED_FILE")
        pages = reader.pages
        if not 1 <= len(pages) <= MAX_PDF_PAGES:
            raise rejected_invalid("PDF_PAGES")
        for page in pages:
            deadline.check()
            reject_page(page)
            page.get_contents()
    except Rejected:
        raise
    except (PyPdfError, OSError, ValueError, KeyError, TypeError):
        raise rejected_invalid("PDF_UNREADABLE") from None
