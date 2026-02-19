"""Document processor using Docling library."""

import asyncio
import base64
import json
import logging
import tempfile
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from google.cloud import storage
from google.api_core import exceptions as gcs_exceptions
from docling.document_converter import DocumentConverter

from agent.config import get_max_document_size, get_processing_timeout, get_result_bucket
from agent.models import DocumentMetadata, DocumentResponse, OutputFormat, ProcessingOptions

logger = logging.getLogger(__name__)

SUPPORTED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/html",
    "text/markdown",
    "text/csv",
    "image/png",
    "image/jpeg",
    "image/tiff",
    "image/bmp",
    "image/webp",
}

FORMAT_TO_EXTENSION = {
    OutputFormat.markdown: ".md",
    OutputFormat.json: ".json",
    OutputFormat.text: ".txt",
}

MIME_TO_EXTENSION = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "text/html": ".html",
    "text/markdown": ".md",
    "text/csv": ".csv",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/tiff": ".tiff",
    "image/bmp": ".bmp",
    "image/webp": ".webp",
}


class DoclingProcessor:
    """Processes documents using the Docling library."""

    def __init__(self):
        self.converter = DocumentConverter()
        result_bucket = get_result_bucket()
        if result_bucket:
            self._result_bucket = result_bucket
            self._storage_client = storage.Client()
        else:
            self._result_bucket = None
            self._storage_client = None

    def _derive_result_filename(self, source: str, output_format: OutputFormat) -> str:
        """Derive result filename from document source."""
        ext = FORMAT_TO_EXTENSION.get(output_format, ".md")
        if source.startswith("gs://"):
            blob_path = source[len("gs://"):].split("/", 1)[-1] if "/" in source[len("gs://"):] else source
            basename = Path(blob_path).name
        elif source.startswith("http://") or source.startswith("https://"):
            basename = Path(urlparse(source).path).name or "document"
        else:
            # base64 temp file path or unknown
            basename = "document"
        return basename + ext

    def _upload_result(self, content: str, filename: str) -> Optional[str]:
        """Upload result content to GCS results/ folder. Returns gs:// URI or None on failure."""
        if not self._storage_client or not self._result_bucket:
            return None
        blob_path = f"results/{filename}"
        try:
            bucket = self._storage_client.bucket(self._result_bucket)
            blob = bucket.blob(blob_path)
            blob.upload_from_string(content, content_type="text/plain; charset=utf-8")
            uri = f"gs://{self._result_bucket}/{blob_path}"
            logger.info("Result uploaded: %s", uri)
            return uri
        except Exception as e:
            logger.error("GCS result upload failed: %s", e)
            return None

    def _convert_sync(
        self, source: str, max_pages: Optional[int] = None
    ):
        """Run Docling conversion synchronously (called in executor)."""
        kwargs = {}
        if max_pages is not None:
            kwargs["max_num_pages"] = max_pages
        return self.converter.convert(source, **kwargs)

    def _format_output(self, result, output_format: OutputFormat) -> str:
        """Convert Docling result to the requested output format."""
        doc = result.document
        if output_format == OutputFormat.markdown:
            return doc.export_to_markdown()
        elif output_format == OutputFormat.json:
            return json.dumps(doc.export_to_dict(), ensure_ascii=False, indent=2)
        elif output_format == OutputFormat.text:
            return doc.export_to_text()
        return doc.export_to_markdown()

    def _extract_metadata(
        self, result, output_format: OutputFormat, processing_time_ms: int
    ) -> DocumentMetadata:
        """Extract metadata from Docling conversion result."""
        doc = result.document
        return DocumentMetadata(
            format=output_format.value,
            pages=len(result.pages) if hasattr(result, "pages") and result.pages else 0,
            tables_found=len(doc.tables) if hasattr(doc, "tables") and doc.tables else 0,
            images_found=len(doc.pictures) if hasattr(doc, "pictures") and doc.pictures else 0,
            processing_time_ms=processing_time_ms,
        )

    async def process_base64(
        self,
        document_base64: str,
        mime_type: str,
        output_format: OutputFormat = OutputFormat.markdown,
        options: Optional[ProcessingOptions] = None,
    ) -> DocumentResponse:
        """Process a base64-encoded document."""
        options = options or ProcessingOptions()

        # Validate MIME type
        if mime_type not in SUPPORTED_MIME_TYPES:
            return DocumentResponse(
                status="error",
                error=f"Unsupported mime_type '{mime_type}'. Supported: {', '.join(sorted(SUPPORTED_MIME_TYPES))}",
            )

        # Decode and validate size
        try:
            raw_bytes = base64.b64decode(document_base64, validate=True)
        except Exception:
            return DocumentResponse(status="error", error="Invalid base64 encoding")

        max_size = get_max_document_size()
        if len(raw_bytes) > max_size:
            max_mb = max_size // (1024 * 1024)
            return DocumentResponse(
                status="error",
                error=f"Document too large (max {max_mb} MB)",
            )

        # Write to temp file and process
        ext = MIME_TO_EXTENSION.get(mime_type, ".bin")
        with tempfile.NamedTemporaryFile(suffix=ext, delete=True) as tmp:
            tmp.write(raw_bytes)
            tmp.flush()
            return await self._run_conversion(
                tmp.name, output_format, options, original_source=None
            )

    async def process_url(
        self,
        document_url: str,
        output_format: OutputFormat = OutputFormat.markdown,
        options: Optional[ProcessingOptions] = None,
        mime_type: str = "application/pdf",
    ) -> DocumentResponse:
        """Process a document from URL or GCS URI."""
        options = options or ProcessingOptions()
        if document_url.startswith("gs://"):
            return await self.process_gcs(document_url, output_format, options, mime_type)
        return await self._run_conversion(document_url, output_format, options, original_source=document_url)

    async def process_gcs(
        self,
        gcs_uri: str,
        output_format: OutputFormat = OutputFormat.markdown,
        options: Optional[ProcessingOptions] = None,
        fallback_mime_type: str = "application/pdf",
    ) -> DocumentResponse:
        """Process a document from Google Cloud Storage.

        Args:
            gcs_uri: GCS URI in format gs://bucket/path/to/file.
            output_format: Desired output format.
            options: Processing options.
            fallback_mime_type: MIME type to use if GCS metadata is missing.
        """
        options = options or ProcessingOptions()

        # Parse gs://bucket/path
        uri_body = gcs_uri[len("gs://"):]
        slash_idx = uri_body.find("/")
        if slash_idx < 1:
            return DocumentResponse(
                status="error",
                error=f"Invalid GCS URI format: '{gcs_uri}'. Expected gs://bucket/path",
            )
        bucket_name = uri_body[:slash_idx]
        blob_path = uri_body[slash_idx + 1:]
        if not blob_path:
            return DocumentResponse(
                status="error",
                error=f"Invalid GCS URI format: '{gcs_uri}'. Missing blob path",
            )

        try:
            client = storage.Client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            blob.reload()  # Fetch metadata
        except gcs_exceptions.NotFound:
            return DocumentResponse(
                status="error",
                error=f"GCS blob not found: {gcs_uri}",
            )
        except gcs_exceptions.Forbidden:
            return DocumentResponse(
                status="error",
                error=f"Permission denied accessing GCS blob: {gcs_uri}",
            )
        except Exception as e:
            logger.error("GCS metadata error: %s", e)
            return DocumentResponse(
                status="error",
                error="Failed to access GCS blob",
            )

        # Size check before download
        max_size = get_max_document_size()
        if blob.size and blob.size > max_size:
            max_mb = max_size // (1024 * 1024)
            return DocumentResponse(
                status="error",
                error=f"Document too large (max {max_mb} MB)",
            )

        # Resolve MIME type from GCS metadata or fallback
        mime_type = fallback_mime_type
        if blob.content_type and blob.content_type != "application/octet-stream":
            mime_type = blob.content_type

        if mime_type not in SUPPORTED_MIME_TYPES:
            return DocumentResponse(
                status="error",
                error=f"Unsupported mime_type '{mime_type}'. Supported: {', '.join(sorted(SUPPORTED_MIME_TYPES))}",
            )

        # Download to temp file
        ext = MIME_TO_EXTENSION.get(mime_type, ".bin")
        try:
            with tempfile.NamedTemporaryFile(suffix=ext, delete=True) as tmp:
                blob.download_to_filename(tmp.name)
                return await self._run_conversion(tmp.name, output_format, options, original_source=gcs_uri)
        except gcs_exceptions.NotFound:
            return DocumentResponse(
                status="error",
                error=f"GCS blob not found: {gcs_uri}",
            )
        except gcs_exceptions.Forbidden:
            return DocumentResponse(
                status="error",
                error=f"Permission denied accessing GCS blob: {gcs_uri}",
            )
        except Exception as e:
            logger.error("GCS download error: %s", e)
            return DocumentResponse(
                status="error",
                error="Failed to download document from GCS",
            )

    async def _run_conversion(
        self,
        source: str,
        output_format: OutputFormat,
        options: ProcessingOptions,
        original_source: Optional[str] = None,
    ) -> DocumentResponse:
        """Run Docling conversion with timeout.

        Args:
            source: File path or URL to pass to Docling.
            output_format: Desired output format.
            options: Processing options.
            original_source: Original document source (gs:// URI, HTTP URL, or None for base64)
                             used for result filename derivation.
        """
        timeout = get_processing_timeout()
        start_time = time.monotonic()

        try:
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    None, self._convert_sync, source, options.max_pages
                ),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            return DocumentResponse(
                status="error",
                error=f"Processing timed out after {timeout} seconds",
            )
        except Exception as e:
            logger.error("Docling conversion error: %s", e)
            return DocumentResponse(
                status="error",
                error="Document processing failed, please try again later",
            )

        try:
            content = self._format_output(result, output_format)
            doc_source = original_source or source
            filename = self._derive_result_filename(doc_source, output_format)
            result_gcs_uri = self._upload_result(content, filename)
        except Exception as e:
            logger.error("Output formatting error: %s", e)
            return DocumentResponse(
                status="error",
                error="Document processing failed, please try again later",
            )

        elapsed_ms = int((time.monotonic() - start_time) * 1000)

        try:
            metadata = self._extract_metadata(result, output_format, elapsed_ms)
        except Exception as e:
            logger.error("Metadata extraction error: %s", e)
            return DocumentResponse(
                status="error",
                error="Document processing failed, please try again later",
            )

        return DocumentResponse(
            status="ok",
            content=content,
            metadata=metadata,
            result_gcs_uri=result_gcs_uri,
        )
