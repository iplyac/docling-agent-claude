## Context

Currently `ProcessingOptions.ocr` defaults to `True` in `agent/models.py`. This means every document — including native PDFs and Office files that contain selectable text — goes through the OCR pipeline, adding latency and CPU load for no benefit.

The change is minimal: a one-line default value change with a spec update to reflect the new contract.

## Goals / Non-Goals

**Goals:**
- Change `ocr` default from `True` to `False` in `ProcessingOptions`
- Update spec requirement "OCR enabled by default" to "OCR disabled by default"
- Update README to reflect the new default

**Non-Goals:**
- Removing OCR support entirely
- Adding auto-detection of whether a document needs OCR
- Changing any other processing option defaults

## Decisions

**Change the model default, not a config env var**

Option A: Change `ProcessingOptions.ocr = False` in `models.py`
Option B: Read default from an environment variable

Chose **Option A** — the default is part of the API contract and should be explicit in the model. An env var would hide the default from callers and make behavior environment-dependent.

## Risks / Trade-offs

- **BREAKING change for callers relying on implicit OCR**: Callers who send scanned PDFs or images without `options.ocr: true` will get empty or degraded output. → Mitigation: document as breaking in the proposal and changelog.
- **No auto-detection**: We don't attempt to detect whether the document needs OCR. Callers must opt in explicitly. This is acceptable given the performance benefit for the common case.

## Migration Plan

1. Deploy updated service
2. Callers processing scanned documents must add `"options": {"ocr": true}` to their requests
3. No data migration required — stateless API change
