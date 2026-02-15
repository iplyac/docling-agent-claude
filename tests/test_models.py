"""Tests for Pydantic models."""

import pytest

from agent.models import DocumentRequest, OutputFormat, ProcessingOptions


def test_document_request_base64_only():
    """Test valid request with base64 only."""
    req = DocumentRequest(document_base64="dGVzdA==", mime_type="application/pdf")
    assert req.document_base64 == "dGVzdA=="
    assert req.document_url is None


def test_document_request_url_only():
    """Test valid request with URL only."""
    req = DocumentRequest(document_url="https://example.com/doc.pdf")
    assert req.document_url == "https://example.com/doc.pdf"
    assert req.document_base64 is None


def test_document_request_neither_source():
    """Test error when neither source provided."""
    with pytest.raises(ValueError, match="Either document_base64 or document_url"):
        DocumentRequest(mime_type="application/pdf")


def test_document_request_both_sources():
    """Test error when both sources provided."""
    with pytest.raises(ValueError, match="Only one of"):
        DocumentRequest(
            document_base64="dGVzdA==",
            document_url="https://example.com/doc.pdf",
        )


def test_document_request_defaults():
    """Test default values."""
    req = DocumentRequest(document_url="https://example.com/doc.pdf")
    assert req.mime_type == "application/pdf"
    assert req.output_format == OutputFormat.markdown
    assert req.options.ocr is True
    assert req.options.extract_tables is True
    assert req.options.extract_images is False
    assert req.options.max_pages is None


def test_processing_options_custom():
    """Test custom processing options."""
    opts = ProcessingOptions(ocr=False, extract_tables=False, extract_images=True, max_pages=10)
    assert opts.ocr is False
    assert opts.extract_tables is False
    assert opts.extract_images is True
    assert opts.max_pages == 10


def test_output_format_enum():
    """Test output format values."""
    assert OutputFormat.markdown == "markdown"
    assert OutputFormat.json == "json"
    assert OutputFormat.text == "text"


def test_document_request_invalid_output_format():
    """Test invalid output format."""
    with pytest.raises(ValueError):
        DocumentRequest(
            document_url="https://example.com/doc.pdf",
            output_format="xml",
        )
