## Why

The docling-agent currently accepts documents only via base64-encoded content or HTTP URLs. When the master-agent receives files from Telegram (e.g., PDFs), it needs to pass them to the docling-agent. Base64 encoding large files into JSON payloads is impractical — it hits shell argument limits, inflates request size by ~33%, and creates memory pressure on both services. Google Cloud Storage (GCS) is already available in the GCP project and provides a natural intermediary: the master-agent uploads the file to GCS, then passes a `gs://` URI to the docling-agent for processing.

## What Changes

- **New GCS document source**: The docling-agent accepts `gs://bucket/path` URIs in the `document_url` field, downloads the blob to a temp file, and processes it with Docling
- **GCS client initialization**: A `google-cloud-storage` client is initialized at startup for downloading blobs
- **MIME type detection from GCS**: When processing a GCS URI, the MIME type is auto-detected from the blob's `content_type` metadata (fallback to the request's `mime_type` field)

## Capabilities

### New Capabilities
_(none — this extends an existing capability)_

### Modified Capabilities
- `document-processing`: Adds GCS URI (`gs://`) as a supported document source alongside base64 and HTTP URLs
- `agent-api`: The `document_url` field now accepts `gs://` URIs in addition to `http(s)://` URLs
- `agent-deployment`: Adds `google-cloud-storage` dependency and requires GCS read permissions for the service account

## Impact

- **Code**: `agent/processor.py` — new `process_gcs()` method and GCS URI detection in URL processing; `agent/models.py` — no schema change (reuses `document_url` field)
- **Dependencies**: Adds `google-cloud-storage` to `requirements.txt`
- **IAM**: Cloud Run service account needs `roles/storage.objectViewer` on the target GCS bucket
- **Docker**: Image size increases slightly (~5 MB for the GCS client library)
