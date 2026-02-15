## ADDED Requirements

### Requirement: GCS client library dependency
The system SHALL include `google-cloud-storage` in its Python dependencies.

#### Scenario: Dependency installed
- **WHEN** `pip install -r requirements.txt` is run
- **THEN** the `google-cloud-storage` library SHALL be installed and importable

### Requirement: GCS read permissions
The Cloud Run service account SHALL have read access to GCS buckets used for document storage.

#### Scenario: Service account permissions documented
- **WHEN** a developer reads the deployment script or README
- **THEN** the required IAM role (`roles/storage.objectViewer`) SHALL be documented
