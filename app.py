import logging
import pathlib
import sys
from contextlib import asynccontextmanager
from contextvars import ContextVar
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pythonjsonlogger import jsonlogger

from agent.config import get_log_level, get_max_document_size, get_port, get_project_id, get_service_name, mask_token
from agent.models import DocumentRequest, DocumentResponse
from agent.processor import DoclingProcessor, SUPPORTED_MIME_TYPES

# Cloud Trace context variable
trace_context: ContextVar[str] = ContextVar("trace_context", default="")


class CloudTraceFormatter(jsonlogger.JsonFormatter):
    """JSON formatter that includes Cloud Trace context."""

    def __init__(self, *args, project_id: str = "", **kwargs):
        super().__init__(*args, **kwargs)
        self.project_id = project_id

    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record["timestamp"] = self.formatTime(record)
        log_record["level"] = record.levelname
        log_record["logger"] = record.name

        trace_id = trace_context.get("")
        if trace_id and self.project_id:
            log_record["logging.googleapis.com/trace"] = (
                f"projects/{self.project_id}/traces/{trace_id}"
            )


def setup_logging(project_id: str, log_level: str) -> None:
    """Configure JSON structured logging."""
    handler = logging.StreamHandler(sys.stdout)
    formatter = CloudTraceFormatter(
        "%(timestamp)s %(level)s %(logger)s %(message)s",
        project_id=project_id,
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    project_id = get_project_id()
    log_level = get_log_level()
    setup_logging(project_id, log_level)

    port = get_port()
    service_name = get_service_name()

    logger.info("Starting %s: port=%d", service_name, port)

    processor = DoclingProcessor()
    app.state.processor = processor
    app.state.started_at = datetime.now(timezone.utc)
    try:
        app.state.version = pathlib.Path("VERSION").read_text().strip()
    except FileNotFoundError:
        app.state.version = "unknown"

    yield

    logger.info("Shutting down %s", service_name)


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def trace_middleware(request: Request, call_next):
    """Extract X-Cloud-Trace-Context header and store in contextvar."""
    trace_header = request.headers.get("X-Cloud-Trace-Context", "")
    if trace_header:
        trace_id = trace_header.split("/")[0]
        trace_context.set(trace_id)
    else:
        trace_context.set("")
    return await call_next(request)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.get("/status")
async def service_status(request: Request):
    """Service status endpoint."""
    uptime = (datetime.now(timezone.utc) - request.app.state.started_at).total_seconds()
    return {
        "name": "docling-agent",
        "purpose": "Document processor — converts PDF/DOCX/PPTX/HTML to structured text using Docling",
        "version": request.app.state.version,
        "uptime_seconds": uptime,
        "status": "ok",
    }


@app.post("/api/process-document")
async def process_document(request: Request):
    """Process a document via Docling and return structured output."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"status": "error", "error": "Invalid JSON"})

    try:
        doc_request = DocumentRequest(**body)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"status": "error", "error": str(e)})

    # Validate MIME type early
    if doc_request.document_base64 and doc_request.mime_type not in SUPPORTED_MIME_TYPES:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "error": f"Unsupported mime_type '{doc_request.mime_type}'. Supported: {', '.join(sorted(SUPPORTED_MIME_TYPES))}",
            },
        )

    # Check document size for base64 input
    if doc_request.document_base64:
        approx_size = len(doc_request.document_base64) * 3 // 4
        max_size = get_max_document_size()
        if approx_size > max_size:
            max_mb = max_size // (1024 * 1024)
            return JSONResponse(
                status_code=413,
                content={"status": "error", "error": f"Document too large (max {max_mb} MB)"},
            )

    logger.info(
        "Document processing request: mime_type=%s, output_format=%s, has_base64=%s, has_url=%s",
        doc_request.mime_type,
        doc_request.output_format.value,
        doc_request.document_base64 is not None,
        doc_request.document_url is not None,
    )

    try:
        processor: DoclingProcessor = request.app.state.processor

        if doc_request.document_base64:
            result = await processor.process_base64(
                doc_request.document_base64,
                doc_request.mime_type,
                doc_request.output_format,
                doc_request.options,
            )
        else:
            result = await processor.process_url(
                doc_request.document_url,
                doc_request.output_format,
                doc_request.options,
                doc_request.mime_type,
            )

        if result.status == "error":
            error_msg = result.error or ""
            if "timed out" in error_msg:
                status_code = 504
            elif "too large" in error_msg:
                status_code = 413
            elif "Unsupported" in error_msg or "Invalid GCS URI" in error_msg:
                status_code = 400
            elif "not found" in error_msg.lower():
                status_code = 404
            elif "Permission denied" in error_msg:
                status_code = 403
            else:
                status_code = 500
            return JSONResponse(status_code=status_code, content=result.model_dump(exclude_none=True))

        return result.model_dump(exclude_none=True)

    except Exception as e:
        error_msg = mask_token(str(e))
        logger.error("Document processing error: %s", error_msg)
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": "Document processing failed, please try again later"},
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=get_port(),
        timeout_graceful_shutdown=9,
    )
