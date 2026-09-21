"""Structured JSON Logging for SolutionBridge."""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from app.utils.request_id import get_current_request_id


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs log records as structured JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": getattr(record, "service", "solutionbridge-api"),
            "customer_id": getattr(record, "customer_id", None),
            "request_id": getattr(record, "request_id", None) or get_current_request_id(),
            "endpoint": getattr(record, "endpoint", None),
            "status_code": getattr(record, "status_code", None),
            "error_code": getattr(record, "error_code", None),
            "response_time_ms": getattr(record, "response_time_ms", None),
            "message": record.getMessage(),
        }

        # Extra metadata if provided
        metadata = getattr(record, "metadata_json", None)
        if metadata:
            log_data["metadata_json"] = metadata

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Configure structured logging to console and log file."""
    logger = logging.getLogger("solutionbridge")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    logger.handlers.clear()

    formatter = JSONFormatter()

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler
    logs_dir = Path(__file__).resolve().parent.parent.parent / "logs"
    logs_dir.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(logs_dir / "app.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.propagate = False
    return logger


logger = setup_logging()
