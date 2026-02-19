"""Tests for GCS result storage functionality."""

import os
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from agent.models import OutputFormat


# --- _derive_result_filename tests (5.1) ---

def make_processor():
    """Create a DoclingProcessor with result bucket disabled."""
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("GCS_RESULT_BUCKET", None)
        from agent.processor import DoclingProcessor
        return DoclingProcessor()


class TestDeriveResultFilename:
    def setup_method(self):
        os.environ.pop("GCS_RESULT_BUCKET", None)
        # Re-import fresh to avoid cached state
        import importlib
        import agent.processor
        importlib.reload(agent.processor)
        from agent.processor import DoclingProcessor
        self.processor = DoclingProcessor()

    def test_gcs_source_markdown(self):
        name = self.processor._derive_result_filename("gs://bucket/path/to/doc.pdf", OutputFormat.markdown)
        assert name == "doc.pdf.md"

    def test_gcs_source_json(self):
        name = self.processor._derive_result_filename("gs://bucket/reports/report.pdf", OutputFormat.json)
        assert name == "report.pdf.json"

    def test_gcs_source_text(self):
        name = self.processor._derive_result_filename("gs://bucket/docs/paper.pdf", OutputFormat.text)
        assert name == "paper.pdf.txt"

    def test_http_url_markdown(self):
        name = self.processor._derive_result_filename("https://example.com/file.pdf", OutputFormat.markdown)
        assert name == "file.pdf.md"

    def test_http_url_json(self):
        name = self.processor._derive_result_filename("http://example.com/report.docx", OutputFormat.json)
        assert name == "report.docx.json"

    def test_base64_fallback_markdown(self):
        name = self.processor._derive_result_filename("/tmp/tmpXYZ.pdf", OutputFormat.markdown)
        assert name == "document.md"

    def test_base64_fallback_none(self):
        name = self.processor._derive_result_filename("", OutputFormat.text)
        assert name == "document.txt"


# --- _upload_result tests (5.2, 5.3) ---

class TestUploadResult:
    def setup_method(self):
        os.environ.pop("GCS_RESULT_BUCKET", None)

    def _make_processor_with_bucket(self, bucket_name="test-results"):
        import importlib
        import agent.processor
        os.environ["GCS_RESULT_BUCKET"] = bucket_name
        importlib.reload(agent.processor)
        from agent.processor import DoclingProcessor

        mock_client = MagicMock()
        mock_blob = MagicMock()
        mock_client.bucket.return_value.blob.return_value = mock_blob

        p = DoclingProcessor()
        p._storage_client = mock_client
        return p, mock_client, mock_blob

    def test_upload_success(self):
        p, mock_client, mock_blob = self._make_processor_with_bucket()
        uri = p._upload_result("# Hello", "doc.pdf.md")

        mock_blob.upload_from_string.assert_called_once_with(
            "# Hello", content_type="text/plain; charset=utf-8"
        )
        assert uri == "gs://test-results/results/doc.pdf.md"

    def test_upload_returns_correct_uri(self):
        p, mock_client, mock_blob = self._make_processor_with_bucket("my-bucket")
        uri = p._upload_result("content", "report.json")
        assert uri == "gs://my-bucket/results/report.json"

    def test_upload_failure_returns_none(self):
        p, mock_client, mock_blob = self._make_processor_with_bucket()
        mock_blob.upload_from_string.side_effect = Exception("network error")
        uri = p._upload_result("content", "doc.pdf.md")
        assert uri is None

    def test_upload_skipped_when_no_bucket(self):
        import importlib
        import agent.processor
        os.environ.pop("GCS_RESULT_BUCKET", None)
        importlib.reload(agent.processor)
        from agent.processor import DoclingProcessor
        p = DoclingProcessor()
        assert p._result_bucket is None
        assert p._storage_client is None
        uri = p._upload_result("content", "doc.pdf.md")
        assert uri is None


# --- Full processor flow tests (5.4, 5.5) ---

class TestProcessorFlowWithStorage:
    def setup_method(self):
        os.environ.pop("GCS_RESULT_BUCKET", None)

    def _make_mock_result(self):
        """Create a mock Docling conversion result."""
        mock_doc = MagicMock()
        mock_doc.export_to_markdown.return_value = "# Converted Document"
        mock_doc.tables = []
        mock_doc.pictures = []
        mock_result = MagicMock()
        mock_result.document = mock_doc
        mock_result.pages = [MagicMock()]
        return mock_result

    @pytest.mark.asyncio
    async def test_result_gcs_uri_populated_when_bucket_set(self):
        import importlib
        import agent.processor
        os.environ["GCS_RESULT_BUCKET"] = "output-bucket"
        importlib.reload(agent.processor)
        from agent.processor import DoclingProcessor, OutputFormat, ProcessingOptions

        mock_docling_result = self._make_mock_result()
        mock_client = MagicMock()
        mock_blob = MagicMock()
        mock_client.bucket.return_value.blob.return_value = mock_blob

        p = DoclingProcessor()
        p._storage_client = mock_client
        p.converter.convert = MagicMock(return_value=mock_docling_result)

        resp = await p._run_conversion(
            "/tmp/doc.pdf",
            OutputFormat.markdown,
            ProcessingOptions(),
            original_source="gs://src-bucket/doc.pdf",
        )
        assert resp.status == "ok"
        assert resp.result_gcs_uri == "gs://output-bucket/results/doc.pdf.md"
        mock_blob.upload_from_string.assert_called_once()

    @pytest.mark.asyncio
    async def test_result_gcs_uri_none_when_no_bucket(self):
        import importlib
        import agent.processor
        os.environ.pop("GCS_RESULT_BUCKET", None)
        importlib.reload(agent.processor)
        from agent.processor import DoclingProcessor, OutputFormat, ProcessingOptions

        mock_docling_result = self._make_mock_result()

        p = DoclingProcessor()
        p.converter.convert = MagicMock(return_value=mock_docling_result)

        resp = await p._run_conversion(
            "/tmp/doc.pdf",
            OutputFormat.markdown,
            ProcessingOptions(),
        )
        assert resp.status == "ok"
        assert resp.result_gcs_uri is None
