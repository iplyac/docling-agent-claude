## 1. Dependencies

- [x] 1.1 Add `google-cloud-storage>=2.18.0` to `requirements.txt`

## 2. GCS Download Logic

- [x] 2.1 Add `process_gcs()` method to `DoclingProcessor` in `agent/processor.py` — parse `gs://bucket/path` URI, create GCS client, get blob metadata
- [x] 2.2 Implement size check in `process_gcs()` — read blob size from metadata, reject if exceeds MAX_DOCUMENT_SIZE_MB before downloading
- [x] 2.3 Implement MIME type detection in `process_gcs()` — use blob's `content_type`, fall back to request `mime_type` if missing or `application/octet-stream`
- [x] 2.4 Implement blob download to temp file in `process_gcs()` — download to NamedTemporaryFile with correct extension, pass to `_run_conversion()`
- [x] 2.5 Add GCS error handling — catch NotFound (blob not found), Forbidden (permission denied), and other GCS exceptions with descriptive error messages

## 3. URL Routing

- [x] 3.1 Update `process_url()` in `agent/processor.py` to detect `gs://` prefix and route to `process_gcs()`, otherwise keep existing Docling URL behavior

## 4. API Endpoint Update

- [x] 4.1 Update `/api/process-document` in `app.py` — when `document_url` starts with `gs://`, skip HTTP-specific MIME type validation (MIME comes from GCS metadata)

## 5. Tests

- [x] 5.1 Add `tests/test_processor_gcs.py` — test `process_gcs()` with mocked GCS client: successful download, blob not found, permission denied, blob too large, MIME type from metadata, MIME type fallback, unsupported MIME type
- [x] 5.2 Add GCS routing test to `tests/test_processor.py` — test that `process_url()` with `gs://` prefix calls `process_gcs()`
- [x] 5.3 Add GCS API test to `tests/test_document_api.py` — test `/api/process-document` with `document_url: "gs://bucket/doc.pdf"` (mocked processor)

## 6. Documentation

- [x] 6.1 Update `README.md` — add GCS URI support to API docs, add `google-cloud-storage` to dependencies, document IAM role requirement
- [x] 6.2 Update `.env.example` — no new env vars needed, but add comment about GCS bucket permissions
