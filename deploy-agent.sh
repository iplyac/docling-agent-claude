#!/usr/bin/env bash
set -euo pipefail

# --- Configuration ---
PROJECT_ID="${PROJECT_ID:-gen-lang-client-0741140892}"
SERVICE_NAME="${SERVICE_NAME:-docling-agent}"
REGION="${REGION:-europe-west4}"
DOCKER_REGISTRY="${DOCKER_REGISTRY:-gcr.io}"
LOG_LEVEL="${LOG_LEVEL:-INFO}"

# --- Timestamped log ---
LOG_FILE="deploy-agent-$(date +%Y%m%d-%H%M%S).log"
exec > >(tee -a "${LOG_FILE}") 2>&1
echo "=== Deploy log: ${LOG_FILE} ==="
echo "=== Started: $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

# --- PORT guard ---
unset PORT
if echo "${ENV_VARS:-}" | grep -q "PORT="; then
    echo "ERROR: ENV_VARS must not contain PORT. Cloud Run injects PORT automatically."
    exit 1
fi

# --- --no-cache support ---
BUILD_EXTRA_ARGS=""
if [[ "${1:-}" == "--no-cache" ]]; then
    BUILD_EXTRA_ARGS="--no-cache"
    echo "Build: --no-cache enabled"
fi

# --- GIT_SHA ---
GIT_SHA="${GIT_SHA:-$(git rev-parse --short HEAD 2>/dev/null || echo '')}"

# --- Image base ---
if [[ "${DOCKER_REGISTRY}" == *"pkg.dev" ]]; then
    if [[ -z "${AR_REPO_NAME:-}" ]]; then
        echo "ERROR: AR_REPO_NAME is required when DOCKER_REGISTRY ends with pkg.dev"
        exit 1
    fi
    IMAGE_BASE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO_NAME}/${SERVICE_NAME}"
else
    IMAGE_BASE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"
fi

IMAGE_LATEST="${IMAGE_BASE}:latest"
echo "Image: ${IMAGE_LATEST}"

# --- Build ---
echo "=== Building with Cloud Build ==="
gcloud builds submit \
    --project="${PROJECT_ID}" \
    --tag="${IMAGE_LATEST}" \
    ${BUILD_EXTRA_ARGS} \
    --quiet

# Tag with GIT_SHA if available
if [[ -n "${GIT_SHA}" ]]; then
    IMAGE_SHA="${IMAGE_BASE}:${GIT_SHA}"
    echo "Tagging: ${IMAGE_SHA}"
    gcloud container images add-tag "${IMAGE_LATEST}" "${IMAGE_SHA}" \
        --project="${PROJECT_ID}" \
        --quiet
fi

# --- Deploy ---
echo "=== Deploying to Cloud Run ==="

GCS_RESULT_BUCKET="${GCS_RESULT_BUCKET:-docling-documents}"

ENV_VARS="GCP_PROJECT_ID=${PROJECT_ID}"
ENV_VARS="${ENV_VARS},GCP_LOCATION=${REGION}"
ENV_VARS="${ENV_VARS},LOG_LEVEL=${LOG_LEVEL}"
ENV_VARS="${ENV_VARS},GCS_RESULT_BUCKET=${GCS_RESULT_BUCKET}"

gcloud run deploy "${SERVICE_NAME}" \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --image="${IMAGE_LATEST}" \
    --platform=managed \
    --ingress=internal \
    --no-allow-unauthenticated \
    --memory=4Gi \
    --cpu=2 \
    --timeout=600 \
    --min-instances=1 \
    --set-env-vars="${ENV_VARS}" \
    --quiet

echo "=== Deploy complete: $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --format="value(status.url)" \
    --quiet)
echo "Service URL: ${SERVICE_URL}"

# Grant master-agent service account invoker rights (idempotent)
# master-agent uses the default Compute Engine SA
MASTER_AGENT_SA="${MASTER_AGENT_SA:-298607833444-compute@developer.gserviceaccount.com}"
echo "=== Granting invoker role to master-agent SA: ${MASTER_AGENT_SA} ==="
gcloud run services add-iam-policy-binding "${SERVICE_NAME}" \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --member="serviceAccount:${MASTER_AGENT_SA}" \
    --role=roles/run.invoker \
    --quiet
