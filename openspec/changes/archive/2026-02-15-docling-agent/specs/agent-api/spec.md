## ADDED Requirements

### Requirement: FastAPI application with lifespan management
The system SHALL be a FastAPI application that initializes Docling components during startup and performs cleanup during shutdown.

#### Scenario: Application startup
- **WHEN** the service starts
- **THEN** the system SHALL initialize the Docling `DocumentConverter`, configure structured JSON logging, and be ready to accept requests

#### Scenario: Application shutdown
- **WHEN** the service receives a shutdown signal
- **THEN** the system SHALL complete in-flight requests within a 9-second graceful shutdown period

### Requirement: Health check endpoint
The system SHALL expose health check endpoints for Cloud Run probes.

#### Scenario: Health check responds
- **WHEN** a GET request is sent to `/health` or `/healthz`
- **THEN** the system SHALL return HTTP 200 with `{"status": "ok"}`

### Requirement: Document processing endpoint
The system SHALL expose a POST endpoint at `/api/process-document` for document processing.

#### Scenario: Valid request with base64 document
- **WHEN** a POST request is sent with valid `document_base64` and `mime_type`
- **THEN** the system SHALL process the document and return the result

#### Scenario: Valid request with URL
- **WHEN** a POST request is sent with valid `document_url`
- **THEN** the system SHALL fetch and process the document

#### Scenario: Missing both document_base64 and document_url
- **WHEN** a POST request is sent without either `document_base64` or `document_url`
- **THEN** the system SHALL return HTTP 400 with an error message

#### Scenario: Both document_base64 and document_url provided
- **WHEN** a POST request is sent with both `document_base64` and `document_url`
- **THEN** the system SHALL return HTTP 400 with an error message indicating only one source is allowed

#### Scenario: Invalid JSON body
- **WHEN** a POST request is sent with an invalid JSON body
- **THEN** the system SHALL return HTTP 400 with an error message

### Requirement: Pydantic request/response validation
The system SHALL use Pydantic models for request validation and response serialization, consistent with the master-agent pattern.

#### Scenario: Request validation
- **WHEN** a request is received
- **THEN** the system SHALL validate it against the Pydantic model and return HTTP 400 with field-level errors for invalid requests

### Requirement: Structured JSON logging
The system SHALL use structured JSON logging compatible with Google Cloud Logging, including Cloud Trace context propagation.

#### Scenario: Request logging
- **WHEN** a document processing request is received
- **THEN** the system SHALL log the request with conversation context (document size, MIME type, requested format) but NOT the document content itself

#### Scenario: Cloud Trace integration
- **WHEN** a request includes the `X-Cloud-Trace-Context` header
- **THEN** the system SHALL include the trace ID in all log entries for that request

### Requirement: Error handling
The system SHALL return generic error messages to clients while logging detailed errors server-side.

#### Scenario: Internal processing error
- **WHEN** Docling processing fails with an unexpected error
- **THEN** the system SHALL return HTTP 500 with `{"status": "error", "error": "Document processing failed, please try again later"}` and log the full error details

### Requirement: Configuration via environment variables
The system SHALL read all configuration from environment variables, consistent with Cloud Run deployment.

#### Scenario: Required configuration
- **WHEN** the service starts
- **THEN** the system SHALL read: `GCP_PROJECT_ID`, `GCP_LOCATION` (default: `europe-west4`), `PORT` (default: `8080`), `LOG_LEVEL` (default: `INFO`), `MAX_DOCUMENT_SIZE_MB` (default: `50`), `PROCESSING_TIMEOUT_SECONDS` (default: `300`)
