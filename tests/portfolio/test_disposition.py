from app.modules.portfolio.disposition import attachment


def test_quotes_and_backslashes_never_reach_the_header() -> None:
    header = attachment('bad"name' + chr(92) + ".pdf")
    assert header.startswith('attachment; filename="bad_name_.pdf"')
    assert chr(92) not in header.split("filename*=")[0]


def test_non_ascii_names_keep_an_encoded_original() -> None:
    header = attachment("rapport é.pdf")
    assert 'filename="rapport _.pdf"' in header
    assert "filename*=UTF-8''rapport%20%C3%A9.pdf" in header
