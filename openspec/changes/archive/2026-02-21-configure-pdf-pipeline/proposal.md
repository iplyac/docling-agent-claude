## Why

`ProcessingOptions` fields `ocr` and `extract_tables` are accepted in the API but never passed to Docling — `DocumentConverter` is created without `PdfPipelineOptions`, so Docling always runs with its own hardcoded defaults regardless of what the caller requests. Fixing this also allows us to explicitly configure the fast `DoclingParseV4DocumentBackend` for PDF, ensuring consistent and correct behavior.

## What Changes

- Configure `DocumentConverter` with `PdfPipelineOptions` for PDF input, wiring `ocr` and `extract_tables` from `ProcessingOptions`
- Explicitly set `DoclingParseV4DocumentBackend` as the PDF backend (fast, production-safe, no memory leaks)
- Because `PdfPipelineOptions` are set at converter init time (not per-call), create a lightweight per-request converter that is initialized with the correct options for each request
- `DoclingParseV2DocumentBackend` is **not** used due to known memory leak in production scenarios

## Capabilities

### New Capabilities

_(none)_

### Modified Capabilities

- `document-processing`: Requirements for `options.ocr` and `options.extract_tables` now describe actual system behavior (previously the options were accepted but ignored)

## Impact

- `agent/processor.py`: `DoclingProcessor.__init__` and `_convert_sync` — replace singleton converter with per-request converter construction using `PdfPipelineOptions`
- `agent/models.py`: No model changes required
- No API contract changes — same request/response shape
