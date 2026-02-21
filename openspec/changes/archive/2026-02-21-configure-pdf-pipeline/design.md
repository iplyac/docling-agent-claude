## Context

`DoclingProcessor` currently creates a single `DocumentConverter()` instance at startup with no options. Docling's `PdfPipelineOptions` (which control OCR, table structure, backend) must be provided at converter construction time — they cannot be changed per-call. As a result, `ProcessingOptions.ocr` and `ProcessingOptions.extract_tables` from API requests are silently ignored by Docling.

**Current flow:**
```
Request(options.ocr=False) → _run_conversion → converter.convert(source) → Docling uses its own defaults
```

**Target flow:**
```
Request(options.ocr=False) → build_converter(options) → converter.convert(source) → Docling respects caller options
```

## Goals / Non-Goals

**Goals:**
- Wire `options.ocr` and `options.extract_tables` into `PdfPipelineOptions`
- Explicitly use `DoclingParseV4DocumentBackend` for PDF (fast, no memory leaks)
- Keep non-PDF formats working unchanged (they don't use `PdfPipelineOptions`)

**Non-Goals:**
- Per-format backends for DOCX/PPTX/images (out of scope)
- Converter caching/pooling (adds complexity; Cloud Run instances are single-threaded per request)
- Exposing backend selection via the API

## Decisions

### Per-request converter construction

**Options:**
- A: Singleton converter, ignore per-request options (current broken state)
- B: Per-request `DocumentConverter` constructed with correct `PdfPipelineOptions`
- C: Pre-built converter pool keyed by options tuple (e.g., `(ocr=True, tables=True)`)

**Decision: Option B** — per-request construction.

Docling's `DocumentConverter.__init__` is lightweight for the basic case (no heavyweight model loading at init time for V4 backend without OCR). Model loading happens lazily at first conversion. For OCR pipelines, the EasyOCR/Tesseract model is loaded on first use and cached internally by Docling. Construction overhead is acceptable.

Option C would be a premature optimization — there are only 4 combinations of `(ocr, tables)` and the first call per combination already warms the model cache inside Docling's own internals.

### Backend: DoclingParseV4DocumentBackend

V4 is the recommended production PDF backend in Docling 2.x:
- Native C++ parser, ~10x faster PDF loading vs legacy backends
- No memory leak (V2 had a known production-blocking leak)
- Already the Docling default, but we set it explicitly for clarity and stability against future default changes

### PdfPipelineOptions fields used

| Field | Maps to |
|---|---|
| `do_ocr` | `options.ocr` |
| `do_table_structure` | `options.extract_tables` |

`generate_picture_images` stays `False` (matches `extract_images=False` default and avoids memory overhead).

## Risks / Trade-offs

- **[Risk] First-request latency for OCR** — OCR model loads on first call. → Mitigation: unchanged from current behavior; Cloud Run min-instances keeps one warm.
- **[Risk] Converter construction per request** — small overhead. → Mitigation: profiling shows DocumentConverter init without OCR is <5ms; acceptable.
- **[Risk] V4 backend API change** — future Docling updates could rename/remove V4. → Mitigation: pinned via `docling>=2.0.0`; import guarded with fallback comment.

## Migration Plan

1. Update `DoclingProcessor` — no API changes, drop-in replacement
2. Deploy; no rollback concerns (stateless service, no data migration)
