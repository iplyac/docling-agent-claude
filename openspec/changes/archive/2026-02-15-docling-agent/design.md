## Context

The master-agent is a Python 3.11 FastAPI service deployed on Google Cloud Run (`europe-west4`). It uses Google ADK with Gemini models for conversational AI, processes text/voice/image messages from a Telegram bot, and maintains session context via Vertex AI. Currently it handles everything in a single service with no sub-agent delegation.

Docling is an open-source document intelligence library (by IBM) that converts PDF, DOCX, PPTX, XLSX, HTML, and images into structured data with table detection, formula extraction (LaTeX), OCR, reading order, and code block identification. It outputs Markdown, JSON, HTML, or plain text.

The docling-agent will be the first sub-agent in the ecosystem — a standalone Cloud Run service that the master-agent calls via HTTP when document processing is needed.

## Goals / Non-Goals

**Goals:**
- Create a standalone FastAPI service that processes documents via Docling
- Accept documents as base64-encoded content or URLs
- Return structured output in Markdown, JSON, or plain text
- Follow the same project conventions as master-agent (logging, deployment, testing)
- Deploy independently on Cloud Run in the same GCP project
- Provide a clean HTTP API that the master-agent can call

**Non-Goals:**
- No Telegram bot integration (all interaction goes through master-agent)
- No conversational AI / LLM integration (pure document processing)
- No session management or memory (stateless service)
- No authentication between services in v1 (both services are internal; IAM auth is a future enhancement)
- No document storage (process and return; caller handles persistence)
- No master-agent code changes in this change (delegation logic will be a separate change)

## Decisions

### D1: Standalone FastAPI service (same pattern as master-agent)

**Decision**: Mirror the master-agent's structure — FastAPI + Uvicorn, Pydantic models, JSON structured logging, Docker + Cloud Build + Cloud Run.

**Rationale**: Consistent toolchain reduces cognitive overhead. The deployment scripts, Dockerfile, and CI/CD pipeline are proven. Reusing the pattern means the team already knows how to deploy, monitor, and debug.

**Alternatives considered**:
- Google Cloud Functions: Simpler but less control over startup, timeout limits (9 min max), cold starts would be painful for Docling model loading
- gRPC service: Better for binary data but adds protocol complexity; HTTP/JSON is simpler and consistent with existing API

### D2: Docling as Python library (not CLI or Docling Serve)

**Decision**: Use `docling` Python library directly via `DocumentConverter` API.

**Rationale**: Maximum control over processing pipeline, no extra service to deploy, direct access to all Docling features (table extraction, OCR, formula detection). The library's `DocumentConverter` provides a clean API for converting documents and accessing structured results.

**Alternatives considered**:
- Docling CLI: Good for scripts but poor for integration, no async support
- Docling Serve: Adds another service to manage; unnecessary when we're already building a service wrapper
- Docling MCP: Interesting for agent integration but couples us to MCP protocol; HTTP API is more flexible

### D3: Document input via base64 or URL

**Decision**: Accept documents either as base64-encoded content (for files sent through Telegram) or as URLs (for web documents).

**Rationale**: Telegram bot sends files as binary/base64 through the master-agent. URL support enables processing web-hosted documents. Both paths converge to the same Docling processing pipeline.

### D4: Synchronous processing with timeout

**Decision**: Process documents synchronously within the HTTP request, with a configurable timeout (default 300 seconds).

**Rationale**: Docling processing can take 10-60 seconds for typical documents. Cloud Run supports up to 60-minute request timeouts. Synchronous processing is simpler than async job queues. If processing takes too long, the timeout returns an error and the caller can retry or inform the user.

**Alternatives considered**:
- Async job queue (Cloud Tasks + callback): More resilient for very large documents but adds significant complexity (job tracking, callbacks, GCS storage). Can be added later if needed.

### D5: Output format selection

**Decision**: Support three output formats — `markdown` (default), `json`, and `text`. The caller specifies the desired format in the request.

**Rationale**: Markdown is the most useful for chat-based interactions (Telegram supports it). JSON provides full structured data for programmatic use. Plain text is a fallback for simple scenarios.

### D6: No Gemini/LLM dependency

**Decision**: The docling-agent does NOT use any LLM. It is purely a document processing service using Docling's ML models (layout detection, table extraction, OCR).

**Rationale**: Keeps the service focused and cost-effective. The master-agent handles all conversational AI. Docling has its own specialized models for document understanding that don't require general-purpose LLMs.

## Risks / Trade-offs

**[Heavy Docker image]** → Docling includes ML models (table detection, layout analysis, OCR). The Docker image will be significantly larger than the master-agent's (~2-3 GB vs ~500 MB). **Mitigation**: Use multi-stage Docker build, pin specific Docling extras to avoid unnecessary dependencies.

**[Cold start latency]** → First request after deployment will be slow (model loading). **Mitigation**: Set Cloud Run min-instances=1 for production to keep one instance warm. Use startup probe with generous timeout.

**[Memory usage]** → Docling processing is memory-intensive, especially for large PDFs with many tables. **Mitigation**: Set Cloud Run memory limit to 2Gi (or 4Gi for production). Add document size limits in the API.

**[Processing timeout]** → Very large documents (100+ pages) may exceed reasonable timeout. **Mitigation**: Set 300s default timeout, document size limit (50 MB), page count advisory in response.

**[No retry/queue]** → If processing fails mid-way, the entire request fails. **Mitigation**: Acceptable for v1. The master-agent can implement retry logic. Async processing can be added later.

## Project Structure

```
docling-agent-claude/
├── app.py                      # FastAPI app, endpoints, lifespan
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container image (multi-stage for Docling)
├── cloudbuild.yaml             # Cloud Build CI/CD pipeline
├── deploy-agent.sh             # Deployment script
├── .env.example                # Environment variable template
├── agent/
│   ├── __init__.py
│   ├── config.py               # Environment config helpers
│   ├── models.py               # Pydantic request/response models
│   └── processor.py            # DoclingProcessor — document conversion logic
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # Shared test fixtures
│   ├── test_health.py          # Health endpoint tests
│   ├── test_document_api.py    # Document processing API tests
│   └── test_processor.py       # Processor unit tests
└── openspec/                   # OpenSpec artifacts
```

## API Design

### POST /api/process-document

```json
Request:
{
  "document_base64": "<base64-encoded-document>",  // either this
  "document_url": "https://example.com/doc.pdf",   // or this
  "mime_type": "application/pdf",
  "output_format": "markdown",  // "markdown" | "json" | "text"
  "options": {
    "ocr": true,               // enable OCR (default: true)
    "extract_tables": true,     // extract tables (default: true)
    "extract_images": false,    // extract images (default: false)
    "max_pages": null           // limit pages (null = all)
  }
}

Response (success):
{
  "status": "ok",
  "content": "<converted document content>",
  "metadata": {
    "format": "markdown",
    "pages": 12,
    "tables_found": 3,
    "images_found": 5,
    "processing_time_ms": 15400
  }
}

Response (error):
{
  "status": "error",
  "error": "Document too large (max 50 MB)"
}
```

### GET /health

```json
{"status": "ok"}
```
