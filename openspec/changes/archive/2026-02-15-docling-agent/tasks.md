## 1. Project Scaffolding

- [x] 1.1 Create `requirements.txt` with docling, fastapi, uvicorn, httpx, python-json-logger, pydantic, pytest, pytest-asyncio
- [x] 1.2 Create `.env.example` documenting all environment variables (GCP_PROJECT_ID, GCP_LOCATION, PORT, LOG_LEVEL, MAX_DOCUMENT_SIZE_MB, PROCESSING_TIMEOUT_SECONDS)
- [x] 1.3 Create `agent/__init__.py`
- [x] 1.4 Create `agent/config.py` with environment variable helpers (get_project_id, get_location, get_port, get_log_level, get_max_document_size, get_processing_timeout)
- [x] 1.5 Create `tests/__init__.py`

## 2. Pydantic Models

- [x] 2.1 Create `agent/models.py` with `ProcessingOptions` model (ocr, extract_tables, extract_images, max_pages)
- [x] 2.2 Add `DocumentRequest` model with validation (document_base64 XOR document_url, mime_type, output_format, options)
- [x] 2.3 Add `DocumentMetadata` model (format, pages, tables_found, images_found, processing_time_ms)
- [x] 2.4 Add `DocumentResponse` model (status, content, metadata, error)

## 3. Document Processor

- [x] 3.1 Create `agent/processor.py` with `DoclingProcessor` class that initializes `DocumentConverter` on construction
- [x] 3.2 Implement `process_base64()` method — decode base64, write to temp file, run Docling conversion, return result
- [x] 3.3 Implement `process_url()` method — pass URL to Docling for direct URL processing
- [x] 3.4 Implement output format conversion — convert Docling result to markdown, JSON, or text based on requested format
- [x] 3.5 Implement metadata extraction — extract page count, table count, image count from Docling result
- [x] 3.6 Add document size validation (reject documents exceeding MAX_DOCUMENT_SIZE_MB)
- [x] 3.7 Add MIME type validation (reject unsupported formats, return list of supported types)
- [x] 3.8 Add processing timeout handling using asyncio.wait_for

## 4. FastAPI Application

- [x] 4.1 Create `app.py` with FastAPI app and lifespan manager (initialize DoclingProcessor on startup)
- [x] 4.2 Add structured JSON logging setup with Cloud Trace context propagation (CloudTraceFormatter)
- [x] 4.3 Add trace middleware for X-Cloud-Trace-Context header extraction
- [x] 4.4 Add `GET /health` and `GET /healthz` endpoints
- [x] 4.5 Add `POST /api/process-document` endpoint with Pydantic validation, error handling, and logging
- [x] 4.6 Add generic error responses for internal failures (mask details, log full error)

## 5. Deployment Infrastructure

- [x] 5.1 Create `Dockerfile` based on `python:3.11-slim` with docling dependencies (multi-stage if needed for image size)
- [x] 5.2 Create `cloudbuild.yaml` with build, push, and deploy steps (matching master-agent pattern)
- [x] 5.3 Create `deploy-agent.sh` with configurable PROJECT_ID, SERVICE_NAME=docling-agent, REGION, LOG_LEVEL, memory=2Gi, timeout=300s
- [x] 5.4 Create `.gitignore` (copy from master-agent, adjust as needed)

## 6. Tests

- [x] 6.1 Create `tests/conftest.py` with shared fixtures (FastAPI test client, mock DoclingProcessor)
- [x] 6.2 Create `tests/test_health.py` — test /health and /healthz endpoints
- [x] 6.3 Create `tests/test_document_api.py` — test /api/process-document with valid base64, valid URL, missing input, both inputs, invalid JSON, unsupported MIME type, oversized document
- [x] 6.4 Create `tests/test_processor.py` — test DoclingProcessor.process_base64(), process_url(), output format conversion, size validation, MIME validation, timeout handling
- [x] 6.5 Create `tests/test_models.py` — test Pydantic model validation (DocumentRequest XOR logic, options defaults, output_format enum)
