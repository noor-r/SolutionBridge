"""Request ID generation and contextvars propagation."""

import uuid
from contextvars import ContextVar
from typing import Optional

_request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def generate_request_id() -> str:
    """Generate a high-visibility, unique request ID."""
    short_uuid = uuid.uuid4().hex[:8].upper()
    return f"REQ-{short_uuid}"


def get_current_request_id() -> Optional[str]:
    """Retrieve the current request ID from context."""
    return _request_id_ctx.get()


def set_current_request_id(request_id: str) -> None:
    """Set the request ID in context."""
    _request_id_ctx.set(request_id)
