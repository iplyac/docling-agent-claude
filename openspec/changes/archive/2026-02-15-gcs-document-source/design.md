## Context

The docling-agent is a stateless FastAPI service on Cloud Run that processes documents via Docling. It currently supports two input methods: base64 content in the JSON body and HTTP URLs passed to Docling directly. The service runs in the same GCP project (`gen-lang-client-0741140892`) as the master-agent, with access to GCP services via the default Compute Engine service account.

The master-agent receives files from Telegram users. These files can be multi-MB PDFs that are too large to pass as base64 in JSON. GCS provides a reliable intermediary — the master-agent uploads the file to a shared bucket, then sends the `gs://` URI to the docling-agent.

## Goals / Non-Goals

**Goals:**
- Accept `gs://bucket/path` URIs in the existing `document_url` field
- Download GCS blobs to temp files and process them through the existing Docling pipeline
- Auto-detect MIME type from GCS blob metadata when not explicitly provided
- Reuse the existing `_run_conversion` pipeline after download

**Non-Goals:**
- No GCS upload capability (the docling-agent only reads)
- No bucket creation or lifecycle management
- No signed URL generation
- No master-agent changes (that's a separate change)
- No streaming from GCS (download fully, then process)

## Decisions

### D1: Detect GCS URIs by `gs://` prefix in `document_url`

**Decision**: If `document_url` starts with `gs://`, route to GCS download logic. Otherwise, pass to Docling as an HTTP URL (existing behavior).

**Rationale**: Simple, unambiguous detection. The `gs://` scheme is well-known and not used for HTTP. No API schema changes needed — the existing `document_url` field handles both.

**Alternatives considered**:
- Separate `gcs_uri` field: Cleaner but adds API surface for a simple prefix check. Would require model changes and breaks existing API contract.

### D2: Use `google-cloud-storage` Python client

**Decision**: Use the official `google-cloud-storage` library to download blobs.

**Rationale**: Already used across the GCP ecosystem. Handles authentication via Application Default Credentials (same as other GCP services). Well-maintained, efficient, supports streaming downloads.

### D3: Download to temp file, then process

**Decision**: Download the full GCS blob to a local temp file, then pass the file path to the existing `_run_conversion` pipeline.

**Rationale**: Docling's `DocumentConverter.convert()` accepts file paths. Downloading first avoids partial-read issues and lets Docling handle the file naturally. Temp files are cleaned up after processing.

### D4: MIME type from GCS metadata with fallback

**Decision**: Use the blob's `content_type` from GCS metadata as the MIME type. Fall back to the request's `mime_type` field if GCS metadata is missing or generic (`application/octet-stream`).

**Rationale**: GCS usually stores the correct content type. This means callers don't need to specify `mime_type` when using GCS URIs — it's auto-detected. The fallback ensures the caller can always override.

### D5: Size validation before download

**Decision**: Check blob size via GCS metadata before downloading. Reject if it exceeds `MAX_DOCUMENT_SIZE_MB`.

**Rationale**: Avoids downloading a 500 MB file only to reject it. GCS blob metadata includes size without downloading content.

## Risks / Trade-offs

**[IAM permissions]** → The Cloud Run service account needs `roles/storage.objectViewer` on the bucket. **Mitigation**: Document in deploy script; use the default Compute Engine SA which typically already has project-level access.

**[Download latency]** → Downloading from GCS adds latency before processing starts. **Mitigation**: GCS-to-Cloud Run in the same region (`europe-west4`) is fast — typically <1s for files under 50 MB.

**[Temp disk space]** → Cloud Run instances have limited disk (in-memory tmpfs). **Mitigation**: The 50 MB document size limit keeps this manageable. Cloud Run provides at least 512 MB tmpfs by default.
