# Docling Agent

Document processing microservice deployed on Google Cloud Run. Accepts documents
(PDF, DOCX, PPTX, XLSX, HTML, images) via HTTP, processes them through
[Docling](https://docling.ai/) library, and returns structured output.
Designed as a sub-agent called by the Master Agent service.

## Architecture

- **Docling**: Open-source document intelligence library (IBM) — table detection, formula extraction, OCR, reading order
- **FastAPI + Uvicorn**: Async HTTP service
- **Stateless**: No sessions, no LLM — pure document processing
- **Internal service**: Not exposed to the internet; called by Master Agent via Cloud Run service-to-service

```
Telegram Bot → Master Agent → Docling Agent → structured output
```

## Project Structure

```
app.py                  # FastAPI application, lifespan, API endpoints
agent/
  config.py             # Environment variable helpers
  models.py             # Pydantic request/response models
  processor.py          # DoclingProcessor — Docling conversion logic
tests/                  # pytest + pytest-asyncio tests
openspec/               # Specifications and change history
```

## Supported Formats

**Input:** PDF, DOCX, PPTX, XLSX, HTML, Markdown, CSV, PNG, JPEG, TIFF, BMP, WEBP

**Output:** Markdown (default), JSON, plain text

## Prerequisites

- Python 3.11+
- `gcloud` CLI (authenticated: `gcloud auth application-default login`)
- GCP project with Cloud Run API enabled
- For GCS support: service account with `roles/storage.objectViewer` on the target bucket

## API Endpoints

| Method | Path                    | Description              |
|--------|-------------------------|--------------------------|
| GET    | /health                 | Health check             |
| GET    | /healthz                | Health check (alias)     |
| POST   | /api/process-document   | Process a document       |

### POST /api/process-document

Request (base64):
```json
{
  "document_base64": "<base64-encoded-document>",
  "mime_type": "application/pdf",
  "output_format": "markdown",
  "options": {
    "ocr": false,
    "extract_tables": true,
    "extract_images": false,
    "max_pages": null
  }
}
```

Request (URL):
```json
{
  "document_url": "https://example.com/report.pdf",
  "output_format": "json"
}
```

Request (GCS):
```json
{
  "document_url": "gs://my-bucket/documents/report.pdf",
  "output_format": "markdown"
}
```

**Processing options defaults:** `ocr` is `false` by default — pass `"ocr": true` explicitly for scanned PDFs or images. `extract_tables` is `true` by default.

> **Breaking change:** `ocr` default changed from `true` to `false`. Callers processing scanned documents must now pass `"options": {"ocr": true}`.

When using `gs://` URIs, the MIME type is auto-detected from GCS blob metadata. The `mime_type` field acts as a fallback if GCS metadata is missing.

Response (success):
```json
{
  "status": "ok",
  "content": "# Document Title\n\nExtracted content...",
  "metadata": {
    "format": "markdown",
    "pages": 12,
    "tables_found": 3,
    "images_found": 5,
    "processing_time_ms": 15400
  }
}
```

Response (error):
```json
{
  "status": "error",
  "error": "Document too large (max 50 MB)"
}
```

## Local Development

1. Copy environment template:
   ```bash
   cp .env.example .env
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run:
   ```bash
   python -m uvicorn app:app --host 0.0.0.0 --port 8080
   ```

4. Verify:
   ```bash
   curl http://localhost:8080/health
   # {"status":"ok"}

   curl -X POST http://localhost:8080/api/process-document \
     -H 'Content-Type: application/json' \
     -d '{"document_url":"https://arxiv.org/pdf/2408.09869","output_format":"markdown"}'
   ```

## Testing

```bash
pytest tests/
```

## Cloud Run Deployment

Default deployment values:
- SERVICE_NAME=docling-agent
- REGION=europe-west4
- Memory: 2Gi
- Timeout: 300s

### Deploy

```bash
./deploy-agent.sh
```

Or with custom parameters:

```bash
PROJECT_ID=your-project REGION=us-central1 ./deploy-agent.sh
```

### Important: Terminal environment

Do not deploy from IDE-embedded terminals (VS Code, IntelliJ, etc.).
They may have restricted environments that cause authentication issues.
Use a standalone terminal application.

## Environment Variables

| Variable                    | Required | Default      | Description                              |
|-----------------------------|----------|--------------|------------------------------------------|
| GCP_PROJECT_ID              | No       | -            | GCP project ID                           |
| GCP_LOCATION                | No       | europe-west4 | GCP location                             |
| PORT                        | No       | 8080         | Server port (Cloud Run injects automatically) |
| LOG_LEVEL                   | No       | INFO         | Logging level                            |
| MAX_DOCUMENT_SIZE_MB        | No       | 50           | Maximum document size in MB              |
| PROCESSING_TIMEOUT_SECONDS  | No       | 300          | Processing timeout in seconds            |

## Security

- Internal-only ingress (`--ingress=internal`) — not publicly accessible
- Requires authentication (`--no-allow-unauthenticated`)
- API keys/tokens are masked in error messages
- Document content is never logged
- GCS access uses Application Default Credentials (service account on Cloud Run)
