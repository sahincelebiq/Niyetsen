from app.services.attachment_service import AttachmentRejected, validate_attachment


def test_rejects_oversized_attachment():
    try:
        validate_attachment(b"x" * (5 * 1024 * 1024 + 1), "application/pdf")
        assert False, "expected rejection"
    except AttachmentRejected:
        pass


def test_rejects_unknown_mime():
    try:
        validate_attachment(b"hello", "text/plain")
        assert False, "expected rejection"
    except AttachmentRejected:
        pass
