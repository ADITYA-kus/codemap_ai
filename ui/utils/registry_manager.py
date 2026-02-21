from __future__ import annotations

import json
import os
import re
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit, urlunsplit


_LOCK = threading.RLock()
_REGISTRY_FILE = "_registry.json"
_SENSITIVE_RE = re.compile(r"(?i)(api[_-]?key|token|authorization|bearer|basic|secret|password)")


def _cache_root(base_dir: Optional[str] = None) -> str:
    if base_dir:
        return os.path.abspath(base_dir)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".codemap_cache"))


def _registry_path(base_dir: Optional[str] = None) -> str:
    return os.path.join(_cache_root(base_dir), _REGISTRY_FILE)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_registry() -> Dict[str, Any]:
    return {
        "version": 1,
        "remember_repos": False,
        "repos": [],
        "updated_at": _now_iso(),
    }


def _safe_repo_url(repo_url: str) -> str:
    value = str(repo_url or "").strip()
    if not value:
        return ""
    try:
        parts = urlsplit(value)
        hostname = parts.hostname or ""
        if not hostname:
            return value
        netloc = hostname
        if parts.port:
            netloc = f"{hostname}:{parts.port}"
        clean = urlunsplit((parts.scheme, netloc, parts.path, "", ""))
        return clean.rstrip("/")
    except Exception:
        return value


def _sanitize_repo_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    now = _now_iso()
    source = str(entry.get("source", "filesystem") or "filesystem").strip().lower()
    if source not in {"filesystem", "github"}:
        source = "filesystem"
    sanitized = {
        "repo_hash": str(entry.get("repo_hash", "") or "").strip(),
        "display_name": str(entry.get("display_name", "") or "").strip(),
        "source": source,
        "repo_path": str(entry.get("repo_path", "") or "").strip(),
        "repo_url": _safe_repo_url(str(entry.get("repo_url", "") or "")),
        "ref": str(entry.get("ref", "") or "").strip(),
        "mode": str(entry.get("mode", "") or "").strip().lower(),
        "added_at": str(entry.get("added_at", "") or now),
        "last_opened_at": str(entry.get("last_opened_at", "") or ""),
    }
    if not sanitized["display_name"]:
        candidate = sanitized["repo_path"] or sanitized["repo_url"] or sanitized["repo_hash"]
        sanitized["display_name"] = os.path.basename(str(candidate).rstrip("\\/")) or str(candidate)
    return sanitized


def _scrub_sensitive_fields(payload: Any) -> Any:
    if isinstance(payload, dict):
        clean: Dict[str, Any] = {}
        for k, v in payload.items():
            key = str(k or "")
            if _SENSITIVE_RE.search(key):
                continue
            clean[key] = _scrub_sensitive_fields(v)
        return clean
    if isinstance(payload, list):
        return [_scrub_sensitive_fields(v) for v in payload]
    return payload


def save_registry_atomic(data: Dict[str, Any], base_dir: Optional[str] = None) -> Dict[str, Any]:
    root = _cache_root(base_dir)
    os.makedirs(root, exist_ok=True)
    path = _registry_path(base_dir)

    payload = _default_registry()
    payload.update({
        "version": int(data.get("version", 1) or 1),
        "remember_repos": bool(data.get("remember_repos", False)),
        "updated_at": _now_iso(),
    })
    repos = data.get("repos", [])
    payload["repos"] = [
        _sanitize_repo_entry(r)
        for r in repos
        if isinstance(r, dict) and str(r.get("repo_hash", "") or "").strip()
    ]

    tmp_path = f"{path}.tmp"
    safe_payload = _scrub_sensitive_fields(payload)
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(safe_payload, f, indent=2)
    os.replace(tmp_path, path)
    return safe_payload


def load_registry(base_dir: Optional[str] = None) -> Dict[str, Any]:
    path = _registry_path(base_dir)
    with _LOCK:
        if not os.path.exists(path):
            return save_registry_atomic(_default_registry(), base_dir=base_dir)
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception:
            return save_registry_atomic(_default_registry(), base_dir=base_dir)
        if not isinstance(raw, dict):
            return save_registry_atomic(_default_registry(), base_dir=base_dir)
        return save_registry_atomic(raw, base_dir=base_dir)


def set_remember(remember_repos: bool, base_dir: Optional[str] = None) -> Dict[str, Any]:
    with _LOCK:
        reg = load_registry(base_dir=base_dir)
        reg["remember_repos"] = bool(remember_repos)
        return save_registry_atomic(reg, base_dir=base_dir)


def list_repos(base_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    reg = load_registry(base_dir=base_dir)
    repos = reg.get("repos", [])
    if not isinstance(repos, list):
        return []
    return [_sanitize_repo_entry(r) for r in repos if isinstance(r, dict)]


def add_repo(entry: Dict[str, Any], base_dir: Optional[str] = None) -> Dict[str, Any]:
    with _LOCK:
        reg = load_registry(base_dir=base_dir)
        repo = _sanitize_repo_entry(entry)
        repos = reg.get("repos", [])
        if not isinstance(repos, list):
            repos = []
        updated = False
        for idx, item in enumerate(repos):
            if isinstance(item, dict) and str(item.get("repo_hash", "") or "") == repo["repo_hash"]:
                merged = dict(item)
                merged.update(repo)
                repos[idx] = _sanitize_repo_entry(merged)
                updated = True
                break
        if not updated:
            repos.append(repo)
        reg["repos"] = repos
        save_registry_atomic(reg, base_dir=base_dir)
        return repo


def remove_repo(repo_hash: str, base_dir: Optional[str] = None) -> Dict[str, Any]:
    key = str(repo_hash or "").strip()
    with _LOCK:
        reg = load_registry(base_dir=base_dir)
        repos = reg.get("repos", [])
        if not isinstance(repos, list):
            repos = []
        reg["repos"] = [
            r for r in repos
            if not (isinstance(r, dict) and str(r.get("repo_hash", "") or "") == key)
        ]
        return save_registry_atomic(reg, base_dir=base_dir)


def clear_repos(base_dir: Optional[str] = None) -> Dict[str, Any]:
    with _LOCK:
        reg = load_registry(base_dir=base_dir)
        reg["repos"] = []
        return save_registry_atomic(reg, base_dir=base_dir)
