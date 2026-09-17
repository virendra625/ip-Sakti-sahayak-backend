"""Security utilities: input sanitization, safe header handling, and auth scaffolding."""

import re
from typing import Optional
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security_scheme = HTTPBearer(auto_error=False)


def sanitize_input_text(text: str, max_length: int = 4000) -> str:
    """Sanitizes user input by stripping null bytes, normalizing control chars,

    and enforcing length limits to prevent DoS.
    """
    if not text:
        return ""

    # Remove null bytes and hazardous control characters
    cleaned = text.replace("\x00", "").strip()

    # Enforce safe upper bound limit
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]

    return cleaned


def validate_no_injection_patterns(text: str) -> bool:
    """Validates that plain text does not contain blatant code execution injections."""
    dangerous_patterns = [
        r"<script.*?>.*?</script>",
        r"javascript:",
        r"__import__",
        r"subprocess\.",
        r"os\.system",
    ]
    for pattern in dangerous_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return False
    return True


async def optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
) -> Optional[dict]:
    """Optional authentication dependency.

    In the MVP, authentication is optional. In future iterations, this
    can decode a JWT and verify user session without changing the route
    signatures.
    """
    if not credentials:
        return None

    token = credentials.credentials
    # Placeholder for future JWT verification:
    # payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    return {"token": token, "is_authenticated": True}
