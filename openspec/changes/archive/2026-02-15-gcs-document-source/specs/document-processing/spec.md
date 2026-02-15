## ADDED Requirements

### Requirement: Process document from GCS URI
The system SHALL accept `gs://bucket/path` URIs in the `document_url` field, download the blob from Google Cloud Storage, and process it through the Docling conversion pipeline.

#### Scenario: Successful GCS document processing
- **WHEN** a POST request is sent to `/api/process-document` with `document_url` starting with `gs://` pointing to a valid document in GCS
- **THEN** the system SHALL download the blob, process it with Docling, and return the structured content

#### Scenario: GCS blob not found
- **WHEN** a POST request is sent with a `gs://` URI pointing to a non-existent blob
- **THEN** the system SHALL return status `"error"` with a descriptive error message indicating the blob was not found

#### Scenario: GCS permission denied
- **WHEN** a POST request is sent with a `gs://` URI that the service account cannot access
- **THEN** the system SHALL return status `"error"` with a message indicating insufficient permissions

#### Scenario: GCS blob exceeds size limit
- **WHEN** a POST request is sent with a `gs://` URI pointing to a blob larger than MAX_DOCUMENT_SIZE_MB
- **THEN** the system SHALL return status `"error"` with HTTP 413 without downloading the blob

### Requirement: Auto-detect MIME type from GCS metadata
The system SHALL use the GCS blob's `content_type` metadata as the MIME type when processing GCS documents.

#### Scenario: MIME type from GCS metadata
- **WHEN** a GCS blob has a valid `content_type` set (not `application/octet-stream`)
- **THEN** the system SHALL use the blob's `content_type` as the MIME type for processing

#### Scenario: Fallback to request MIME type
- **WHEN** a GCS blob has no `content_type` or it is `application/octet-stream`
- **THEN** the system SHALL fall back to the `mime_type` field from the request

#### Scenario: Unsupported MIME type from GCS
- **WHEN** the resolved MIME type (from GCS or request) is not in the supported formats list
- **THEN** the system SHALL return status `"error"` with HTTP 400
