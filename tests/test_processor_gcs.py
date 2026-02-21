"""Tests for GCS document processing in DoclingProcessor."""

import base64
from unittest.mock import MagicMock, patch

import pytest

from agent.models import OutputFormat, ProcessingOptions


@pytest.fixture
def processor():
    """Create a DoclingProcessor with mocked converter."""
    from agent.processor import DoclingProcessor

    proc = DoclingProcessor()

    mock_doc = MagicMock()
    mock_doc.export_to_markdown.return_value = "# GCS Doc\n\nContent"
    mock_doc.export_to_text.return_value = "GCS Doc\nContent"
    mock_doc.export_to_dict.return_value = {"name": "test"}
    mock_doc.tables = []
    mock_doc.pictures = []

    mock_result = MagicMock()
    mock_result.document = mock_doc
    mock_result.pages = [MagicMock()]

    mock_converter = MagicMock()
    mock_converter.convert.return_value = mock_result
    proc._build_converter = MagicMock(return_value=mock_converter)
    proc.converter = mock_converter
    return proc


def _mock_blob(size=1000, content_type="application/pdf"):
    """Create a mock GCS blob."""
    blob = MagicMock()
    blob.size = size
    blob.content_type = content_type
    blob.reload.return_value = None
    blob.download_to_filename.return_value = None
    return blob


def _mock_gcs_client(blob):
    """Create a mock GCS client that returns the given blob."""
    client = MagicMock()
    bucket = MagicMock()
    bucket.blob.return_value = blob
    client.bucket.return_value = bucket
    return client


@pytest.mark.asyncio
@patch("agent.processor.storage.Client")
async def test_process_gcs_success(mock_client_cls, processor):
    """Test successful GCS document processing."""
    blob = _mock_blob()
    mock_client_cls.return_value = _mock_gcs_client(blob)

    result = await processor.process_gcs("gs://my-bucket/doc.pdf")
    assert result.status == "ok"
    assert result.content is not None
    blob.reload.assert_called_once()
    blob.download_to_filename.assert_called_once()


@pytest.mark.asyncio
@patch("agent.processor.storage.Client")
async def test_process_gcs_not_found(mock_client_cls, processor):
    """Test GCS blob not found."""
    from google.api_core.exceptions import NotFound

    blob = _mock_blob()
    blob.reload.side_effect = NotFound("not found")
    mock_client_cls.return_value = _mock_gcs_client(blob)

    result = await processor.process_gcs("gs://my-bucket/missing.pdf")
    assert result.status == "error"
    assert "not found" in result.error


@pytest.mark.asyncio
@patch("agent.processor.storage.Client")
async def test_process_gcs_forbidden(mock_client_cls, processor):
    """Test GCS permission denied."""
    from google.api_core.exceptions import Forbidden

    blob = _mock_blob()
    blob.reload.side_effect = Forbidden("forbidden")
    mock_client_cls.return_value = _mock_gcs_client(blob)

    result = await processor.process_gcs("gs://private-bucket/doc.pdf")
    assert result.status == "error"
    assert "Permission denied" in result.error


@pytest.mark.asyncio
@patch("agent.processor.storage.Client")
async def test_process_gcs_too_large(mock_client_cls, processor):
    """Test GCS blob exceeds size limit."""
    import os
    os.environ["MAX_DOCUMENT_SIZE_MB"] = "0"
    try:
        blob = _mock_blob(size=10_000_000)
        mock_client_cls.return_value = _mock_gcs_client(blob)

        result = await processor.process_gcs("gs://my-bucket/huge.pdf")
        assert result.status == "error"
        assert "too large" in result.error.lower()
        blob.download_to_filename.assert_not_called()
    finally:
        os.environ.pop("MAX_DOCUMENT_SIZE_MB", None)


@pytest.mark.asyncio
@patch("agent.processor.storage.Client")
async def test_process_gcs_mime_from_metadata(mock_client_cls, processor):
    """Test MIME type auto-detected from GCS blob metadata."""
    blob = _mock_blob(content_type="text/html")
    mock_client_cls.return_value = _mock_gcs_client(blob)

    result = await processor.process_gcs(
        "gs://my-bucket/page.html",
        fallback_mime_type="application/pdf",
    )
    assert result.status == "ok"


@pytest.mark.asyncio
@patch("agent.processor.storage.Client")
async def test_process_gcs_mime_fallback(mock_client_cls, processor):
    """Test MIME type falls back to request value when GCS is octet-stream."""
    blob = _mock_blob(content_type="application/octet-stream")
    mock_client_cls.return_value = _mock_gcs_client(blob)

    result = await processor.process_gcs(
        "gs://my-bucket/doc.pdf",
        fallback_mime_type="application/pdf",
    )
    assert result.status == "ok"


@pytest.mark.asyncio
@patch("agent.processor.storage.Client")
async def test_process_gcs_unsupported_mime(mock_client_cls, processor):
    """Test unsupported MIME type from GCS metadata."""
    blob = _mock_blob(content_type="video/mp4")
    mock_client_cls.return_value = _mock_gcs_client(blob)

    result = await processor.process_gcs("gs://my-bucket/video.mp4")
    assert result.status == "error"
    assert "Unsupported" in result.error


@pytest.mark.asyncio
async def test_process_gcs_invalid_uri(processor):
    """Test invalid GCS URI format."""
    result = await processor.process_gcs("gs://noblobpath")
    assert result.status == "error"
    assert "Invalid GCS URI" in result.error


@pytest.mark.asyncio
async def test_process_gcs_empty_blob_path(processor):
    """Test GCS URI with empty blob path."""
    result = await processor.process_gcs("gs://bucket/")
    assert result.status == "error"
    assert "Missing blob path" in result.error
