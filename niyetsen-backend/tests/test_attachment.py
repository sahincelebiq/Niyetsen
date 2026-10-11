import pytest

from app.services.attachment_service import AttachmentRejected, validate_attachment


def test_rejects_oversized_attachment():
    try:
        validate_attachment(b"x" * (5 * 1024 * 1024 + 1), "application/pdf")
        assert False, "expected rejection"
    except AttachmentRejected:
        pass


def test_corrupt_pdf_and_docx_are_rejected_not_raised():
    import asyncio

    from app.services.attachment_service import (
        AttachmentRejected, ingest_attachment,
    )

    with pytest.raises(AttachmentRejected):
        asyncio.run(
            ingest_attachment(b"%PDF-1.4\nnot a pdf", "application/pdf", "x.pdf")
        )
    with pytest.raises(AttachmentRejected):
        asyncio.run(
            ingest_attachment(
                b"PK\x03\x04not-a-docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "x.docx",
            )
        )


def test_rejects_unknown_mime():
    try:
        validate_attachment(b"hello", "text/plain")
        assert False, "expected rejection"
    except AttachmentRejected:
        pass
