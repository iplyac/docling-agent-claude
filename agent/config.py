import logging
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)


def mask_token(message: str) -> str:
    """Mask API keys that appear in error messages."""
    masked = re.sub(r"AIza[A-Za-z0-9_-]{20,}", "AIza***MASKED***", message)
    masked = re.sub(r"[A-Za-z0-9_-]{30,}", "***MASKED***", masked)
    return masked


def get_port() -> int:
    """Return configured port or default 8080."""
    try:
        return int(os.getenv("PORT", "8080"))
    except (ValueError, TypeError):
        return 8080


def get_project_id() -> str:
    """Return GCP project ID from environment."""
    return os.getenv("GCP_PROJECT_ID") or os.getenv("PROJECT_ID") or ""


def get_location() -> str:
    """Return GCP location."""
    return os.getenv("GCP_LOCATION") or "europe-west4"


def get_log_level() -> str:
    """Return log level or default INFO."""
    return os.getenv("LOG_LEVEL", "INFO").upper()


def get_service_name() -> str:
    """Return service name."""
    return os.getenv("SERVICE_NAME") or "docling-agent"


def get_max_document_size() -> int:
    """Return max document size in bytes."""
    try:
        mb = int(os.getenv("MAX_DOCUMENT_SIZE_MB", "50"))
    except (ValueError, TypeError):
        mb = 50
    return mb * 1024 * 1024


def get_processing_timeout() -> int:
    """Return processing timeout in seconds."""
    try:
        return int(os.getenv("PROCESSING_TIMEOUT_SECONDS", "300"))
    except (ValueError, TypeError):
        return 300
