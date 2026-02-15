"""Shared test fixtures and mock setup."""

import sys
from unittest.mock import MagicMock, AsyncMock

import pytest


# Mock docling before imports to avoid loading ML models in tests
mock_docling = MagicMock()
mock_converter_class = MagicMock()
mock_docling.document_converter.DocumentConverter = mock_converter_class
sys.modules["docling"] = mock_docling
sys.modules["docling.document_converter"] = mock_docling.document_converter


@pytest.fixture
def mock_processor():
    """Create a mock DoclingProcessor."""
    from agent.models import DocumentMetadata, DocumentResponse

    processor = MagicMock()
    processor.process_base64 = AsyncMock(
        return_value=DocumentResponse(
            status="ok",
            content="# Test Document\n\nHello world",
            metadata=DocumentMetadata(
                format="markdown",
                pages=1,
                tables_found=0,
                images_found=0,
                processing_time_ms=100,
            ),
        )
    )
    processor.process_url = AsyncMock(
        return_value=DocumentResponse(
            status="ok",
            content="# Test Document\n\nHello world",
            metadata=DocumentMetadata(
                format="markdown",
                pages=1,
                tables_found=0,
                images_found=0,
                processing_time_ms=100,
            ),
        )
    )
    return processor


@pytest.fixture
def test_client(mock_processor):
    """Create a FastAPI test client with mocked processor."""
    from fastapi.testclient import TestClient
    from app import app

    app.state.processor = mock_processor
    return TestClient(app)
