"""Tests for /api/process-document endpoint."""

import base64

from unittest.mock import AsyncMock
from agent.models import DocumentResponse


def test_process_base64_document(test_client, mock_processor):
    """Test successful base64 document processing."""
    doc_b64 = base64.b64encode(b"%PDF-1.4 fake pdf content").decode()
    response = test_client.post(
        "/api/process-document",
        json={
            "document_base64": doc_b64,
            "mime_type": "application/pdf",
            "output_format": "markdown",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "content" in data
    assert "metadata" in data
    mock_processor.process_base64.assert_called_once()


def test_process_url_document(test_client, mock_processor):
    """Test successful URL document processing."""
    response = test_client.post(
        "/api/process-document",
        json={
            "document_url": "https://example.com/doc.pdf",
            "output_format": "markdown",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    mock_processor.process_url.assert_called_once()


def test_missing_both_sources(test_client):
    """Test error when neither base64 nor URL provided."""
    response = test_client.post(
        "/api/process-document",
        json={"mime_type": "application/pdf"},
    )
    assert response.status_code == 400


def test_both_sources_provided(test_client):
    """Test error when both base64 and URL provided."""
    doc_b64 = base64.b64encode(b"content").decode()
    response = test_client.post(
        "/api/process-document",
        json={
            "document_base64": doc_b64,
            "document_url": "https://example.com/doc.pdf",
            "mime_type": "application/pdf",
        },
    )
    assert response.status_code == 400


def test_invalid_json(test_client):
    """Test error on invalid JSON body."""
    response = test_client.post(
        "/api/process-document",
        content=b"not json",
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 400


def test_unsupported_mime_type(test_client):
    """Test error on unsupported MIME type."""
    doc_b64 = base64.b64encode(b"content").decode()
    response = test_client.post(
        "/api/process-document",
        json={
            "document_base64": doc_b64,
            "mime_type": "video/mp4",
        },
    )
    assert response.status_code == 400
    assert "Unsupported" in response.json()["error"]


def test_oversized_document(test_client):
    """Test error on oversized document (size check in endpoint)."""
    # Create a base64 string that decodes to > 50MB
    # We use a smaller mock and patch the config
    import os
    os.environ["MAX_DOCUMENT_SIZE_MB"] = "0"  # 0 MB limit for test
    try:
        doc_b64 = base64.b64encode(b"small content").decode()
        response = test_client.post(
            "/api/process-document",
            json={
                "document_base64": doc_b64,
                "mime_type": "application/pdf",
            },
        )
        assert response.status_code == 413
    finally:
        os.environ.pop("MAX_DOCUMENT_SIZE_MB", None)


def test_processing_error(test_client, mock_processor):
    """Test internal processing error returns 500."""
    mock_processor.process_base64 = AsyncMock(
        return_value=DocumentResponse(
            status="error",
            error="Document processing failed, please try again later",
        )
    )
    doc_b64 = base64.b64encode(b"%PDF-1.4 content").decode()
    response = test_client.post(
        "/api/process-document",
        json={
            "document_base64": doc_b64,
            "mime_type": "application/pdf",
        },
    )
    assert response.status_code == 500


def test_timeout_error(test_client, mock_processor):
    """Test timeout error returns 504."""
    mock_processor.process_base64 = AsyncMock(
        return_value=DocumentResponse(
            status="error",
            error="Processing timed out after 300 seconds",
        )
    )
    doc_b64 = base64.b64encode(b"%PDF-1.4 content").decode()
    response = test_client.post(
        "/api/process-document",
        json={
            "document_base64": doc_b64,
            "mime_type": "application/pdf",
        },
    )
    assert response.status_code == 504
