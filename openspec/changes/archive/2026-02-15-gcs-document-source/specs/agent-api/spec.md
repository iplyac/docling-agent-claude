## MODIFIED Requirements

### Requirement: Document processing endpoint
The system SHALL expose a POST endpoint at `/api/process-document` for document processing.

#### Scenario: Valid request with base64 document
- **WHEN** a POST request is sent with valid `document_base64` and `mime_type`
- **THEN** the system SHALL process the document and return the result

#### Scenario: Valid request with HTTP URL
- **WHEN** a POST request is sent with valid `document_url` starting with `http://` or `https://`
- **THEN** the system SHALL fetch and process the document via Docling

#### Scenario: Valid request with GCS URI
- **WHEN** a POST request is sent with valid `document_url` starting with `gs://`
- **THEN** the system SHALL download the blob from GCS and process the document

#### Scenario: Missing both document_base64 and document_url
- **WHEN** a POST request is sent without either `document_base64` or `document_url`
- **THEN** the system SHALL return HTTP 400 with an error message

#### Scenario: Both document_base64 and document_url provided
- **WHEN** a POST request is sent with both `document_base64` and `document_url`
- **THEN** the system SHALL return HTTP 400 with an error message indicating only one source is allowed

#### Scenario: Invalid JSON body
- **WHEN** a POST request is sent with an invalid JSON body
- **THEN** the system SHALL return HTTP 400 with an error message
