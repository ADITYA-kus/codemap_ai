from __future__ import annotations

import re
from typing import Any, Iterable, Optional


_GITHUB_TOKEN_RE = re.compile(r"\b(gh[pousr]_[A-Za-z0-9_]{8,})\b")
_BEARER_RE = re.compile(r"(?i)\bBearer\s+([A-Za-z0-9\-._~+/]+=*)")
_BASIC_RE = re.compile(r"(?i)\bBasic\s+([A-Za-z0-9\-._~+/]+=*)")
_URL_CREDENTIALS_RE = re.compile(r"(https?://)([^/\s:@]+):([^@\s/]+)@")
_API_KEY_RE = re.compile(r"(?i)\b(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?([^\s'\";]{6,})")


def _mask_token(value: str) -> str:
    token = str(value or "")
    if token.startswith("gh") and "_" in token:
        prefix, _ = token.split("_", 1)
        return f"{prefix}_************"
    return "********"


def redact_secrets(text: str, extra_secrets: Optional[Iterable[str]] = None) -> str:
    value = str(text or "")

    for secret in (extra_secrets or []):
        s = str(secret or "").strip()
        if s:
            value = value.replace(s, "********")

    value = _GITHUB_TOKEN_RE.sub(lambda m: _mask_token(m.group(1)), value)
    value = _BEARER_RE.sub("Bearer ********", value)
    value = _BASIC_RE.sub("Basic ********", value)
    value = _URL_CREDENTIALS_RE.sub(r"\1***:***@", value)

    def _api_key_sub(match: re.Match) -> str:
        return f"{match.group(1)}=[REDACTED]"

    value = _API_KEY_RE.sub(_api_key_sub, value)
    return value


def redact_payload(payload: Any, extra_secrets: Optional[Iterable[str]] = None) -> Any:
    if isinstance(payload, str):
        return redact_secrets(payload, extra_secrets=extra_secrets)
    if isinstance(payload, list):
        return [redact_payload(v, extra_secrets=extra_secrets) for v in payload]
    if isinstance(payload, tuple):
        return [redact_payload(v, extra_secrets=extra_secrets) for v in payload]
    if isinstance(payload, dict):
        return {k: redact_payload(v, extra_secrets=extra_secrets) for k, v in payload.items()}
    return payload
