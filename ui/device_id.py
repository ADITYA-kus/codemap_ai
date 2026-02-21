from __future__ import annotations

import os
import re
import uuid


_SAFE_ID_RE = re.compile(r"^[a-zA-Z0-9._-]{8,128}$")


def get_or_create_device_id(cache_root: str) -> str:
    root = os.path.abspath(cache_root)
    os.makedirs(root, exist_ok=True)
    path = os.path.join(root, "device_id.txt")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                value = (f.read() or "").strip()
            if _SAFE_ID_RE.match(value):
                return value
        except Exception:
            pass

    value = uuid.uuid4().hex
    with open(path, "w", encoding="utf-8") as f:
        f.write(value)
    return value
