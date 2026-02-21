## ADDED Requirements

### Requirement: Process document from base64 content
The system SHALL accept a base64-encoded document with its MIME type and convert it to structured output using the Docling library.

#### Scenario: Successful PDF processing
- **WHEN** a POST request is sent to `/api/process-document` with a valid base64-encoded PDF and `mime_type: "application/pdf"`
- **THEN** the system SHALL return status `"ok"` with the converted document content in the requested output format

#### Scenario: Successful DOCX processing
- **WHEN** a POST request is sent with a valid base64-encoded DOCX file and `mime_type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document"`
- **THEN** the system SHALL return status `"ok"` with the converted document content

#### Scenario: Successful PPTX processing
- **WHEN** a POST request is sent with a valid base64-encoded PPTX file and `mime_type: "application/vnd.openxmlformats-officedocument.presentationml.presentation"`
- **THEN** the system SHALL return status `"ok"` with the converted document content

#### Scenario: Successful XLSX processing
- **WHEN** a POST request is sent with a valid base64-encoded XLSX file and `mime_type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"`
- **THEN** the system SHALL return status `"ok"` with the converted document content

#### Scenario: Successful HTML processing
- **WHEN** a POST request is sent with a valid base64-encoded HTML file and `mime_type: "text/html"`
- **THEN** the system SHALL return status `"ok"` with the converted document content

#### Scenario: Successful image processing
- **WHEN** a POST request is sent with a valid base64-encoded image (PNG, JPEG, TIFF, BMP, WEBP) and the corresponding `mime_type`
- **THEN** the system SHALL perform OCR and return the extracted text content

### Requirement: Process document from URL
The system SHALL accept a document URL and fetch, then convert the document to structured output.

#### Scenario: Successful URL-based processing
- **WHEN** a POST request is sent to `/api/process-document` with a valid `document_url` pointing to a supported document
- **THEN** the system SHALL fetch the document, process it with Docling, and return the structured content

#### Scenario: Unreachable URL
- **WHEN** a POST request is sent with a `document_url` that cannot be fetched (404, timeout, DNS failure)
- **THEN** the system SHALL return status `"error"` with a descriptive error message

### Requirement: Support multiple output formats
The system SHALL support `markdown`, `json`, and `text` output formats, with `markdown` as the default.

#### Scenario: Markdown output (default)
- **WHEN** a request is sent without specifying `output_format` or with `output_format: "markdown"`
- **THEN** the system SHALL return the document content as Markdown with tables, headings, and formatting preserved

#### Scenario: JSON output
- **WHEN** a request is sent with `output_format: "json"`
- **THEN** the system SHALL return the full Docling document structure as JSON, including page layout, tables, images, and metadata

#### Scenario: Text output
- **WHEN** a request is sent with `output_format: "text"`
- **THEN** the system SHALL return plain text content with reading order preserved but no formatting

#### Scenario: Invalid output format
- **WHEN** a request is sent with an unsupported `output_format` value
- **THEN** the system SHALL return status `"error"` with HTTP 400

### Requirement: Configurable processing options
The system SHALL accept optional processing parameters to control Docling behavior.

#### Scenario: OCR disabled by default
- **WHEN** a request is sent without specifying `options.ocr`
- **THEN** the system SHALL process the document without OCR

#### Scenario: OCR enabled explicitly
- **WHEN** a request is sent with `options.ocr: true`
- **THEN** the system SHALL process the document with OCR enabled

#### Scenario: OCR disabled explicitly
- **WHEN** a request is sent with `options.ocr: false`
- **THEN** the system SHALL skip OCR processing

#### Scenario: Table extraction enabled by default
- **WHEN** a request is sent without specifying `options.extract_tables`
- **THEN** the system SHALL extract and structure tables found in the document

#### Scenario: Page limit
- **WHEN** a request is sent with `options.max_pages: N`
- **THEN** the system SHALL process only the first N pages of the document

### Requirement: Return processing metadata
The system SHALL include metadata about the processing result in every successful response.

#### Scenario: Metadata in response
- **WHEN** a document is successfully processed
- **THEN** the response SHALL include `metadata` with: `format` (output format used), `pages` (total page count), `tables_found` (number of tables detected), `images_found` (number of images detected), `processing_time_ms` (processing duration in milliseconds)

### Requirement: Document size limits
The system SHALL enforce a maximum document size to prevent resource exhaustion.

#### Scenario: Document within size limit
- **WHEN** a document is submitted that is under 50 MB (decoded size)
- **THEN** the system SHALL process it normally

#### Scenario: Document exceeds size limit
- **WHEN** a document is submitted that exceeds 50 MB (decoded size)
- **THEN** the system SHALL return status `"error"` with HTTP 413 and message indicating the size limit

### Requirement: Unsupported format handling
The system SHALL reject documents with unsupported MIME types.

#### Scenario: Unsupported MIME type
- **WHEN** a request is sent with a `mime_type` not supported by Docling (e.g., `video/mp4`, `application/zip`)
- **THEN** the system SHALL return status `"error"` with HTTP 400 and a message listing supported formats

### Requirement: Processing timeout
The system SHALL enforce a processing timeout to prevent indefinite hangs.

#### Scenario: Processing within timeout
- **WHEN** a document processes within the configured timeout (default 300 seconds)
- **THEN** the system SHALL return the result normally

#### Scenario: Processing exceeds timeout
- **WHEN** document processing exceeds the configured timeout
- **THEN** the system SHALL abort processing and return status `"error"` with HTTP 504 and a timeout message

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
