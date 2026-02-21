## MODIFIED Requirements

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
