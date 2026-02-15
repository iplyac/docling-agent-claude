## ADDED Requirements

### Requirement: Docker container image
The system SHALL be packaged as a Docker container image based on `python:3.11-slim`, with Docling and all dependencies installed.

#### Scenario: Successful image build
- **WHEN** `docker build` is run against the Dockerfile
- **THEN** the build SHALL produce a working container image with the application and all Docling dependencies

#### Scenario: Container starts and serves
- **WHEN** the container is started with required environment variables
- **THEN** the application SHALL start Uvicorn on the configured PORT and respond to health checks within 60 seconds

### Requirement: Cloud Build CI/CD pipeline
The system SHALL include a `cloudbuild.yaml` that builds the Docker image and deploys to Cloud Run.

#### Scenario: Cloud Build execution
- **WHEN** `gcloud builds submit` is triggered
- **THEN** the pipeline SHALL build the image, tag it with `latest` and git SHA, push to Container Registry, and deploy to Cloud Run

### Requirement: Deployment script
The system SHALL include a `deploy-agent.sh` script following the same pattern as the master-agent.

#### Scenario: Script deployment
- **WHEN** `./deploy-agent.sh` is executed
- **THEN** the script SHALL build the image via Cloud Build and deploy to Cloud Run with service name `docling-agent` in the configured region

#### Scenario: Configurable deployment parameters
- **WHEN** the script is executed
- **THEN** the following SHALL be configurable via environment variables: `PROJECT_ID` (default: same as master-agent), `SERVICE_NAME` (default: `docling-agent`), `REGION` (default: `europe-west4`), `LOG_LEVEL` (default: `INFO`)

### Requirement: Cloud Run configuration
The system SHALL be deployed on Cloud Run with appropriate resource settings for Docling processing.

#### Scenario: Resource allocation
- **WHEN** the service is deployed to Cloud Run
- **THEN** the deployment SHALL configure: memory limit of at least 2Gi, request timeout of 300 seconds, graceful shutdown timeout of 9 seconds

#### Scenario: Environment variable injection
- **WHEN** the service is deployed
- **THEN** the deployment SHALL set environment variables: `GCP_PROJECT_ID`, `GCP_LOCATION`, `LOG_LEVEL`, `GOOGLE_GENAI_USE_VERTEXAI=true`

### Requirement: Environment template
The system SHALL include a `.env.example` file documenting all configurable environment variables.

#### Scenario: Template completeness
- **WHEN** a developer checks `.env.example`
- **THEN** it SHALL list all environment variables with descriptions and default values

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
