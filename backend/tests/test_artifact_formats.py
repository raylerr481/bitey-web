from app.core.artifact_formats import describe_formats, resolve_format


def test_core_workspace_formats_are_editable():
    formats = {item["artifact_type"]: item for item in describe_formats()}
    assert formats["document"]["extension"] == ".docx"
    assert formats["presentation"]["extension"] == ".pptx"
    assert formats["spreadsheet"]["extension"] == ".xlsx"
    assert formats["document"]["editable"] is True


def test_pdf_is_supported_as_a_rendered_output():
    pdf = resolve_format("pdf")
    assert pdf is not None
    assert pdf.mime_type == "application/pdf"
    assert pdf.writer == "reportlab"
