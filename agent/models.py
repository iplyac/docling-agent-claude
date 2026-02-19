"""Request/response models for the document processing API."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, model_validator


class OutputFormat(str, Enum):
    markdown = "markdown"
    json = "json"
    text = "text"


class ProcessingOptions(BaseModel):
    """Options controlling Docling processing behavior."""

    ocr: bool = True
    extract_tables: bool = True
    extract_images: bool = False
    max_pages: Optional[int] = None


class DocumentRequest(BaseModel):
    """Document processing request. Exactly one of document_base64 or document_url must be provided."""

    document_base64: Optional[str] = None
    document_url: Optional[str] = None
    mime_type: str = "application/pdf"
    output_format: OutputFormat = OutputFormat.markdown
    options: ProcessingOptions = ProcessingOptions()

    @model_validator(mode="after")
    def validate_source(self):
        has_base64 = bool(self.document_base64)
        has_url = bool(self.document_url)
        if not has_base64 and not has_url:
            raise ValueError("Either document_base64 or document_url is required")
        if has_base64 and has_url:
            raise ValueError("Only one of document_base64 or document_url is allowed, not both")
        return self


class DocumentMetadata(BaseModel):
    """Metadata about the processing result."""

    format: str
    pages: int = 0
    tables_found: int = 0
    images_found: int = 0
    processing_time_ms: int = 0


class DocumentResponse(BaseModel):
    """Document processing response."""

    status: str  # "ok" or "error"
    content: Optional[str] = None
    metadata: Optional[DocumentMetadata] = None
    result_gcs_uri: Optional[str] = None
    error: Optional[str] = None
