"""Tests for DoclingProcessor."""

import asyncio
import base64
from unittest.mock import MagicMock, patch

import pytest

from agent.models import DocumentMetadata, OutputFormat, ProcessingOptions


@pytest.fixture
def processor():
    """Create a DoclingProcessor with mocked converter."""
    from agent.processor import DoclingProcessor

    proc = DoclingProcessor()

    # Create mock conversion result
    mock_doc = MagicMock()
    mock_doc.export_to_markdown.return_value = "# Test\n\nContent"
    mock_doc.export_to_text.return_value = "Test\nContent"
    mock_doc.export_to_dict.return_value = {"name": "test", "texts": []}
    mock_doc.tables = []
    mock_doc.pictures = []

    mock_result = MagicMock()
    mock_result.document = mock_doc
    mock_result.pages = [MagicMock()]  # 1 page

    proc.converter = MagicMock()
    proc.converter.convert.return_value = mock_result
    return proc


@pytest.mark.asyncio
async def test_process_base64_success(processor):
    """Test successful base64 processing."""
    doc_b64 = base64.b64encode(b"%PDF-1.4 content").decode()
    result = await processor.process_base64(doc_b64, "application/pdf")
    assert result.status == "ok"
    assert result.content is not None
    assert result.metadata is not None
    assert result.metadata.pages == 1


@pytest.mark.asyncio
async def test_process_base64_unsupported_mime(processor):
    """Test rejection of unsupported MIME type."""
    doc_b64 = base64.b64encode(b"content").decode()
    result = await processor.process_base64(doc_b64, "video/mp4")
    assert result.status == "error"
    assert "Unsupported" in result.error


@pytest.mark.asyncio
async def test_process_base64_invalid_base64(processor):
    """Test rejection of invalid base64."""
    result = await processor.process_base64("not-valid-base64!!!", "application/pdf")
    assert result.status == "error"
    assert "base64" in result.error.lower()


@pytest.mark.asyncio
async def test_process_base64_too_large(processor):
    """Test rejection of oversized documents."""
    import os
    os.environ["MAX_DOCUMENT_SIZE_MB"] = "0"
    try:
        doc_b64 = base64.b64encode(b"content").decode()
        result = await processor.process_base64(doc_b64, "application/pdf")
        assert result.status == "error"
        assert "too large" in result.error.lower()
    finally:
        os.environ.pop("MAX_DOCUMENT_SIZE_MB", None)


@pytest.mark.asyncio
async def test_process_url_success(processor):
    """Test successful URL processing."""
    result = await processor.process_url("https://example.com/doc.pdf")
    assert result.status == "ok"
    assert result.content is not None


@pytest.mark.asyncio
async def test_output_format_markdown(processor):
    """Test markdown output format."""
    doc_b64 = base64.b64encode(b"%PDF-1.4 content").decode()
    result = await processor.process_base64(
        doc_b64, "application/pdf", OutputFormat.markdown
    )
    assert result.status == "ok"
    assert result.metadata.format == "markdown"


@pytest.mark.asyncio
async def test_output_format_json(processor):
    """Test JSON output format."""
    doc_b64 = base64.b64encode(b"%PDF-1.4 content").decode()
    result = await processor.process_base64(
        doc_b64, "application/pdf", OutputFormat.json
    )
    assert result.status == "ok"
    assert result.metadata.format == "json"


@pytest.mark.asyncio
async def test_output_format_text(processor):
    """Test text output format."""
    doc_b64 = base64.b64encode(b"%PDF-1.4 content").decode()
    result = await processor.process_base64(
        doc_b64, "application/pdf", OutputFormat.text
    )
    assert result.status == "ok"
    assert result.metadata.format == "text"


@pytest.mark.asyncio
async def test_max_pages_option(processor):
    """Test max_pages option is passed to converter."""
    doc_b64 = base64.b64encode(b"%PDF-1.4 content").decode()
    options = ProcessingOptions(max_pages=5)
    result = await processor.process_base64(
        doc_b64, "application/pdf", options=options
    )
    assert result.status == "ok"
    # Verify max_num_pages was passed to converter
    call_kwargs = processor.converter.convert.call_args
    assert call_kwargs[1].get("max_num_pages") == 5


@pytest.mark.asyncio
async def test_conversion_error(processor):
    """Test handling of Docling conversion error."""
    processor.converter.convert.side_effect = RuntimeError("Conversion failed")
    doc_b64 = base64.b64encode(b"%PDF-1.4 content").decode()
    result = await processor.process_base64(doc_b64, "application/pdf")
    assert result.status == "error"


@pytest.mark.asyncio
async def test_timeout_handling(processor):
    """Test processing timeout."""
    import os
    os.environ["PROCESSING_TIMEOUT_SECONDS"] = "0"

    def slow_convert(*args, **kwargs):
        import time
        time.sleep(5)

    processor.converter.convert.side_effect = slow_convert
    try:
        doc_b64 = base64.b64encode(b"%PDF-1.4 content").decode()
        result = await processor.process_base64(doc_b64, "application/pdf")
        assert result.status == "error"
        assert "timed out" in result.error.lower()
    finally:
        os.environ.pop("PROCESSING_TIMEOUT_SECONDS", None)
