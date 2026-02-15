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

# Mock GCS and google.api_core.exceptions before any imports
# The exceptions module must be a real module with real Exception subclasses
import types

_gcs_exc_module = types.ModuleType("google.api_core.exceptions")
class _NotFound(Exception):
    pass
class _Forbidden(Exception):
    pass
_gcs_exc_module.NotFound = _NotFound
_gcs_exc_module.Forbidden = _Forbidden

_api_core_module = types.ModuleType("google.api_core")
_api_core_module.exceptions = _gcs_exc_module

# Set up the module hierarchy
if "google" not in sys.modules:
    sys.modules["google"] = types.ModuleType("google")
if "google.cloud" not in sys.modules:
    sys.modules["google.cloud"] = types.ModuleType("google.cloud")
if "google.api_core" not in sys.modules:
    sys.modules["google.api_core"] = _api_core_module
sys.modules["google.api_core.exceptions"] = _gcs_exc_module
if "google.cloud.storage" not in sys.modules:
    sys.modules["google.cloud.storage"] = MagicMock()


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
