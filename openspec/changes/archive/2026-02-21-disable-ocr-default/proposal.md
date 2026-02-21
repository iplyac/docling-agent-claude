## Why

OCR is computationally expensive and unnecessary for most documents (native PDFs, DOCX, XLSX, HTML) that already contain machine-readable text. Having OCR enabled by default causes unnecessary processing overhead and slows down conversions for the common case.

## What Changes

- **BREAKING**: Change default value of `options.ocr` from `true` to `false`
- The OCR option remains available — callers can still explicitly pass `options.ocr: true` to enable it when needed (e.g. scanned PDFs, images)

## Capabilities

### New Capabilities

_(none)_

### Modified Capabilities

- `document-processing`: The requirement "OCR enabled by default" changes — OCR SHALL be **disabled** by default when `options.ocr` is not specified

## Impact

- `agent/models.py`: `ProcessingOptions.ocr` default value `True` → `False`
- `openspec/specs/document-processing/spec.md`: update OCR default scenario
- README / API docs: update example and description of `options.ocr`
