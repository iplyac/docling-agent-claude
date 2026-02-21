## 1. Processor Refactor

- [x] 1.1 Add imports to `agent/processor.py`: `PdfFormatOption`, `PdfPipelineOptions`, `InputFormat` from docling, `DoclingParseV4DocumentBackend`
- [x] 1.2 Add helper method `_build_converter(options: ProcessingOptions) -> DocumentConverter` that constructs a `DocumentConverter` with `PdfPipelineOptions(do_ocr=options.ocr, do_table_structure=options.extract_tables)` and `backend=DoclingParseV4DocumentBackend`
- [x] 1.3 Remove the singleton `self.converter` from `DoclingProcessor.__init__`
- [x] 1.4 Update `_convert_sync` to accept `options: ProcessingOptions` and call `_build_converter(options).convert(source, ...)` instead of `self.converter.convert(...)`
- [x] 1.5 Update all callers of `_convert_sync` in `_run_conversion` to pass `options` through

## 2. Verification

- [x] 2.1 Run existing tests (`pytest tests/`) and confirm they pass
