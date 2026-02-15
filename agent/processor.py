"""Document processor using Docling library."""

import asyncio
import base64
import json
import logging
import tempfile
import time
from pathlib import Path
from typing import Optional

from docling.document_converter import DocumentConverter

from agent.config import get_max_document_size, get_processing_timeout
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
                tmp.name, output_format, options
            )

    async def process_url(
        self,
        document_url: str,
        output_format: OutputFormat = OutputFormat.markdown,
        options: Optional[ProcessingOptions] = None,
    ) -> DocumentResponse:
        """Process a document from URL."""
        options = options or ProcessingOptions()
        return await self._run_conversion(document_url, output_format, options)

    async def _run_conversion(
        self,
        source: str,
        output_format: OutputFormat,
        options: ProcessingOptions,
    ) -> DocumentResponse:
        """Run Docling conversion with timeout."""
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

        elapsed_ms = int((time.monotonic() - start_time) * 1000)

        try:
            content = self._format_output(result, output_format)
            metadata = self._extract_metadata(result, output_format, elapsed_ms)
        except Exception as e:
            logger.error("Output formatting error: %s", e)
            return DocumentResponse(
                status="error",
                error="Document processing failed, please try again later",
            )

        return DocumentResponse(
            status="ok",
            content=content,
            metadata=metadata,
        )
