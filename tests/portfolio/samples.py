from io import BytesIO

from PIL import Image
from pypdf import PdfWriter
from pypdf.generic import ArrayObject, DictionaryObject, NameObject, TextStringObject


def image_bytes(fmt: str, width: int = 16, height: int = 16) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (width, height), (10, 120, 200)).save(buffer, format=fmt)
    return buffer.getvalue()


def writer(pages: int = 1) -> PdfWriter:
    document = PdfWriter()
    for _ in range(pages):
        document.add_blank_page(width=72, height=72)
    return document


def pdf_from(document: PdfWriter) -> bytes:
    buffer = BytesIO()
    document.write(buffer)
    return buffer.getvalue()


def pdf_bytes(pages: int = 1) -> bytes:
    return pdf_from(writer(pages))


def pdf_encrypted() -> bytes:
    document = writer()
    document.encrypt("owner-secret")
    return pdf_from(document)


def pdf_with_javascript() -> bytes:
    document = writer()
    action = DictionaryObject(
        {NameObject("/S"): NameObject("/JavaScript"),
         NameObject("/JS"): TextStringObject("app.alert('x');")}
    )
    document.root_object[NameObject("/Names")] = DictionaryObject(
        {NameObject("/JavaScript"): ArrayObject([TextStringObject("entry"), action])}
    )
    return pdf_from(document)


def pdf_with_attachment() -> bytes:
    document = writer()
    document.add_attachment("payload.txt", b"embedded")
    return pdf_from(document)


def pdf_with_open_action() -> bytes:
    document = writer()
    action = DictionaryObject(
        {NameObject("/S"): NameObject("/JavaScript"),
         NameObject("/JS"): TextStringObject("app.alert('x');")}
    )
    document.root_object[NameObject("/OpenAction")] = action
    return pdf_from(document)


def pdf_with_launch_annotation() -> bytes:
    document = writer()
    action = DictionaryObject({NameObject("/S"): NameObject("/Launch")})
    annotation = DictionaryObject(
        {NameObject("/Subtype"): NameObject("/Link"), NameObject("/A"): action}
    )
    document.pages[0][NameObject("/Annots")] = ArrayObject([annotation])
    return pdf_from(document)
