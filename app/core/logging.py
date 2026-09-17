"""Structured logging configuration for IP-SAKTI Sahayak.

Follows security best practices:
- Logs request IDs, endpoints, latency, document counts, and errors.
- Never logs API keys, database credentials, or sensitive personal data.
"""

import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Optional

# Context variable to hold request ID across async tasks
request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


class RequestIdFilter(logging.Filter):
    """Logging filter that attaches the current request_id to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        req_id = request_id_ctx.get()
        record.request_id = req_id if req_id else "system"
        return True


def setup_logging(log_level: int = logging.INFO) -> logging.Logger:
    """Configures the root application logger with formatting and filters."""
    logger = logging.getLogger("ipsakti")
    logger.setLevel(log_level)

    # Avoid duplicate handlers if setup_logging is called multiple times
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(log_level)

        formatter = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [req_id=%(request_id)s] [%(name)s:%(lineno)d] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        handler.addFilter(RequestIdFilter())
        logger.addHandler(handler)

    # Silence overly verbose third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    return logger


def sanitize_log_message(msg: str) -> str:
    """Masks potential sensitive tokens or keys from log messages."""
    sensitive_patterns = ["api_key", "password", "token", "secret", "authorization"]
    lower = msg.lower()
    for pattern in sensitive_patterns:
        if pattern in lower:
            # Basic redaction indicator
            return "[REDACTED - SENSITIVE VALUE PRESENT]"
    return msg


# Module-level default logger
logger = setup_logging()
