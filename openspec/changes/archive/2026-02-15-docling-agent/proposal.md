## Why

The master-agent currently handles all processing itself with no delegation capability. Document processing (PDF, DOCX, PPTX, images, etc.) is a specialized task that requires dedicated tooling. Docling — an open-source document intelligence library by IBM — provides advanced parsing with table detection, formula extraction, OCR, and structured output. Creating a dedicated docling-agent as the first sub-agent establishes the agent delegation pattern and adds powerful document processing capabilities accessible through the Telegram bot via the master agent.

## What Changes

- **New standalone service**: `docling-agent` — a FastAPI microservice that accepts documents and returns structured data using the Docling library
- **Document processing pipeline**: Support for PDF, DOCX, PPTX, XLSX, HTML, and image formats with structured output (Markdown, JSON, text)
- **Master agent delegation**: The master-agent gains the ability to route document processing requests to the docling-agent via internal HTTP calls
- **Deployment infrastructure**: Dockerfile, Cloud Build config, and deploy scripts mirroring the master-agent's deployment pattern on Cloud Run
- **No direct Telegram bot access**: The docling-agent is an internal service; all user interaction goes through the master agent

## Capabilities

### New Capabilities
- `document-processing`: Core Docling integration — accepts documents (base64 or URL), processes them via Docling, returns structured output (Markdown, JSON, text) with extracted tables, images, formulas, and reading order
- `agent-api`: FastAPI service with health check and document processing endpoints, matching the master-agent's patterns (Pydantic models, structured logging, async processing)
- `agent-deployment`: Docker container, Cloud Build CI/CD, and Cloud Run deployment scripts following the master-agent conventions

### Modified Capabilities
_(none — this is a new standalone service; master-agent changes will be handled in a separate change)_

## Impact

- **New service**: Entirely new Cloud Run service (`docling-agent`) in the same GCP project
- **Dependencies**: Adds `docling` Python library (heavy — includes ML models for table detection, OCR, layout analysis)
- **Infrastructure**: New Cloud Run service, new Container Registry image, new Cloud Build trigger
- **Network**: Master agent will call docling-agent over internal Cloud Run URLs (service-to-service auth via IAM)
- **Cost**: Additional Cloud Run instance; Docling processing is CPU/memory intensive — may need higher resource limits
