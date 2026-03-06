from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Dict, List, Optional, Tuple

from security_utils import redact_secrets

_LOCK = RLock()
_SENSITIVE_KEYS = ("api_key", "token", "authorization", "bearer", "basic", "secret", "password")
_SKIP_DIRS = {".git", "__pycache__", ".codemap_cache", ".venv", "venv", "node_modules"}


def _project_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def cache_root(base_dir: Optional[str] = None) -> str:
    root = os.path.abspath(base_dir or os.path.join(_project_root(), ".codemap_cache"))
    os.makedirs(root, exist_ok=True)
    return root


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def _normalize_target(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if os.path.exists(raw):
        raw = os.path.abspath(raw)
    raw = os.path.normpath(raw)
    return raw.replace("\\", "/").lower()


def compute_repo_hash(repo_target: str) -> str:
    normalized = _normalize_target(repo_target)
    if not normalized:
        normalized = "<empty>"
    return _sha256_text(normalized)[:16]


def _is_probable_repo_hash(value: str) -> bool:
    v = str(value or "").strip().lower()
    if len(v) < 8 or len(v) > 64:
        return False
    return all(ch in "0123456789abcdef" for ch in v)


def get_cache_dir(repo_target: str, base_dir: Optional[str] = None) -> str:
    root = cache_root(base_dir)
    target = str(repo_target or "").strip()
    if _is_probable_repo_hash(target) and os.path.isdir(os.path.join(root, target)):
        repo_hash = target
    else:
        repo_hash = compute_repo_hash(target)
    return os.path.join(root, repo_hash)


def _metadata_path(repo_hash: str, base_dir: Optional[str] = None) -> str:
    return os.path.join(cache_root(base_dir), repo_hash, "metadata.json")


def _manifest_path(repo_dir: str, base_dir: Optional[str] = None) -> str:
    return os.path.join(get_cache_dir(repo_dir, base_dir=base_dir), "manifest.json")


def _policy_path(base_dir: Optional[str] = None) -> str:
    return os.path.join(cache_root(base_dir), "retention.json")


def _workspaces_path(base_dir: Optional[str] = None) -> str:
    return os.path.join(cache_root(base_dir), "workspaces.json")


def _dir_size(path: str) -> int:
    total = 0
    if not os.path.isdir(path):
        return 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            fp = os.path.join(root, name)
            try:
                total += int(os.path.getsize(fp))
            except OSError:
                continue
    return int(total)


def _atomic_json_write(path: str, payload: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp_", suffix=".json", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def _load_json(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception:
        return default


def _scrub_payload(payload: Any) -> Any:
    if isinstance(payload, dict):
        out: Dict[str, Any] = {}
        for k, v in payload.items():
            key = str(k or "")
            lk = key.lower()
            if any(s in lk for s in _SENSITIVE_KEYS):
                continue
            out[key] = _scrub_payload(v)
        return out
    if isinstance(payload, list):
        return [_scrub_payload(v) for v in payload]
    if isinstance(payload, str):
        return redact_secrets(payload)
    return payload


def load_policy(base_dir: Optional[str] = None) -> Dict[str, Any]:
    default = {
        "default_ttl_days": 14,
        "workspaces_ttl_days": 7,
        "never_delete_repo_hashes": [],
        "repo_policies": {},
        "last_cleanup_iso": "",
    }
    raw = _load_json(_policy_path(base_dir), default)
    if not isinstance(raw, dict):
        return dict(default)
    merged = dict(default)
    merged.update(raw)
    merged["default_ttl_days"] = max(0, _safe_int(merged.get("default_ttl_days"), 14))
    merged["workspaces_ttl_days"] = max(0, _safe_int(merged.get("workspaces_ttl_days"), 7))
    if not isinstance(merged.get("never_delete_repo_hashes"), list):
        merged["never_delete_repo_hashes"] = []
    if not isinstance(merged.get("repo_policies"), dict):
        merged["repo_policies"] = {}
    return _scrub_payload(merged)


def save_policy(policy: Dict[str, Any], base_dir: Optional[str] = None) -> Dict[str, Any]:
    with _LOCK:
        current = load_policy(base_dir)
        merged = dict(current)
        if isinstance(policy, dict):
            merged.update(policy)
        merged["default_ttl_days"] = max(0, _safe_int(merged.get("default_ttl_days"), 14))
        merged["workspaces_ttl_days"] = max(0, _safe_int(merged.get("workspaces_ttl_days"), 7))
        merged["last_cleanup_iso"] = str(merged.get("last_cleanup_iso", "") or "")
        merged = _scrub_payload(merged)
        _atomic_json_write(_policy_path(base_dir), merged)
        return merged


def collect_fingerprints(repo_dir: str) -> Dict[str, Dict[str, int]]:
    repo_root = os.path.abspath(repo_dir)
    out: Dict[str, Dict[str, int]] = {}
    if not os.path.isdir(repo_root):
        return out
    for root, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for name in files:
            if not name.endswith(".py"):
                continue
            fp = os.path.join(root, name)
            try:
                st = os.stat(fp)
            except OSError:
                continue
            rel = os.path.relpath(fp, repo_root).replace("\\", "/")
            out[rel] = {"mtime_ns": int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))), "size": int(st.st_size)}
    return out


def diff_fingerprints(previous: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
    prev = previous if isinstance(previous, dict) else {}
    cur = current if isinstance(current, dict) else {}
    changed: List[str] = []
    keys = set(prev.keys()) | set(cur.keys())
    for key in sorted(keys):
        if prev.get(key) != cur.get(key):
            changed.append(key)
    return {"changed_files": changed, "changed_count": len(changed)}


def build_manifest(repo_dir: str, fingerprints: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    extra = metadata if isinstance(metadata, dict) else {}
    analysis_version = str(extra.get("analysis_version", "2.2") or "2.2")
    now = _now_iso()
    payload: Dict[str, Any] = {
        "repo_hash": compute_repo_hash(repo_dir),
        "repo_dir": os.path.abspath(repo_dir),
        "analysis_version": analysis_version,
        "updated_at": now,
        "fingerprints": fingerprints if isinstance(fingerprints, dict) else {},
    }
    payload.update(_scrub_payload(extra))
    return payload


def load_manifest(repo_dir: str, base_dir: Optional[str] = None) -> Dict[str, Any]:
    data = _load_json(_manifest_path(repo_dir, base_dir), {})
    return data if isinstance(data, dict) else {}


def save_manifest(repo_dir: str, manifest: Dict[str, Any], base_dir: Optional[str] = None) -> None:
    with _LOCK:
        payload = manifest if isinstance(manifest, dict) else {}
        _atomic_json_write(_manifest_path(repo_dir, base_dir), _scrub_payload(payload))


def should_rebuild(repo_dir: str, analysis_version: str = "2.2", base_dir: Optional[str] = None) -> bool:
    manifest = load_manifest(repo_dir, base_dir=base_dir)
    if not manifest:
        return True
    if str(manifest.get("analysis_version", "") or "") != str(analysis_version or ""):
        return True
    previous = manifest.get("fingerprints", {}) if isinstance(manifest.get("fingerprints"), dict) else {}
    current = collect_fingerprints(repo_dir)
    delta = diff_fingerprints(previous, current)
    return bool(delta.get("changed_count", 0))


def _default_metadata(repo_hash: str) -> Dict[str, Any]:
    now = _now_iso()
    return {
        "repo_hash": repo_hash,
        "source": "filesystem",
        "repo_path": "",
        "repo_url": "",
        "ref": "",
        "workspace_dir": "",
        "analysis_version": "2.2",
        "created_at": now,
        "last_accessed_at": now,
        "retention_days": 14,
        "private_mode": False,
        "ai_fingerprint_source": "",
    }


def _load_metadata(repo_hash: str, base_dir: Optional[str] = None) -> Dict[str, Any]:
    path = _metadata_path(repo_hash, base_dir=base_dir)
    raw = _load_json(path, {})
    base = _default_metadata(repo_hash)
    if isinstance(raw, dict):
        base.update(raw)
    base["repo_hash"] = repo_hash
    base["retention_days"] = max(0, _safe_int(base.get("retention_days"), 14))
    base["private_mode"] = bool(base.get("private_mode", False))
    return _scrub_payload(base)


def _save_metadata(repo_hash: str, payload: Dict[str, Any], base_dir: Optional[str] = None) -> Dict[str, Any]:
    meta = _default_metadata(repo_hash)
    if isinstance(payload, dict):
        meta.update(payload)
    meta["repo_hash"] = repo_hash
    meta["retention_days"] = max(0, _safe_int(meta.get("retention_days"), 14))
    meta["private_mode"] = bool(meta.get("private_mode", False))
    meta = _scrub_payload(meta)
    _atomic_json_write(_metadata_path(repo_hash, base_dir=base_dir), meta)
    return meta


def upsert_metadata(repo_hash: str, **fields: Any) -> Dict[str, Any]:
    with _LOCK:
        current = _load_metadata(repo_hash)
        current.update(_scrub_payload(fields))
        if not str(current.get("created_at", "") or ""):
            current["created_at"] = _now_iso()
        if not str(current.get("last_accessed_at", "") or ""):
            current["last_accessed_at"] = _now_iso()
        return _save_metadata(repo_hash, current)


def set_retention(repo_hash: str, days: int) -> Dict[str, Any]:
    with _LOCK:
        current = _load_metadata(repo_hash)
        current["retention_days"] = max(0, int(days))
        current["last_accessed_at"] = _now_iso()
        return _save_metadata(repo_hash, current)


def touch_last_accessed(repo_hash: str) -> Dict[str, Any]:
    with _LOCK:
        current = _load_metadata(repo_hash)
        current["last_accessed_at"] = _now_iso()
        return _save_metadata(repo_hash, current)


def compute_analysis_fingerprint(repo_dir: str) -> str:
    cache_dir = get_cache_dir(repo_dir)
    manifest = _load_json(os.path.join(cache_dir, "manifest.json"), {})
    analysis_version = str((manifest or {}).get("analysis_version", "") or "")
    parts: List[str] = [analysis_version]
    for name in ("resolved_calls.json", "project_tree.json", "risk_radar.json", "analysis_metrics.json"):
        path = os.path.join(cache_dir, name)
        if os.path.exists(path):
            try:
                st = os.stat(path)
                parts.append(f"{name}:{int(st.st_size)}:{int(getattr(st, 'st_mtime_ns', int(st.st_mtime*1e9)))}")
            except OSError:
                parts.append(f"{name}:missing")
        else:
            parts.append(f"{name}:missing")
    return _sha256_text("|".join(parts))


def _artifact_flags(cache_dir: str) -> Dict[str, bool]:
    return {
        "resolved_calls": os.path.exists(os.path.join(cache_dir, "resolved_calls.json")),
        "explain": os.path.exists(os.path.join(cache_dir, "explain.json")),
        "project_tree": os.path.exists(os.path.join(cache_dir, "project_tree.json")),
        "risk_radar": os.path.exists(os.path.join(cache_dir, "risk_radar.json")),
        "dependency_cycles": os.path.exists(os.path.join(cache_dir, "dependency_cycles.json")),
    }


def _compute_expiry(meta: Dict[str, Any], policy: Dict[str, Any], now: Optional[datetime] = None) -> Dict[str, Any]:
    current = now or datetime.now(timezone.utc)
    repo_hash = str(meta.get("repo_hash", "") or "")
    never = set(str(x) for x in (policy.get("never_delete_repo_hashes") or []))
    if repo_hash in never:
        return {"mode": "pinned", "days_left": None, "expired": False}

    ttl_days = _safe_int(meta.get("retention_days"), -1)
    if ttl_days < 0:
        ttl_days = _safe_int(policy.get("default_ttl_days"), 14)
    if ttl_days == 0:
        return {"mode": "pinned", "days_left": None, "expired": False}

    last = _parse_iso(str(meta.get("last_accessed_at", "") or "")) or _parse_iso(str(meta.get("created_at", "") or ""))
    if last is None:
        return {"mode": "ttl", "days_left": ttl_days, "expired": False}

    age_days = (current - last).total_seconds() / 86400.0
    days_left = int(ttl_days - age_days)
    expired = age_days >= float(ttl_days)
    return {"mode": "ttl", "days_left": days_left, "expired": bool(expired)}


def _list_repo_hash_dirs(base_dir: Optional[str] = None) -> List[str]:
    root = cache_root(base_dir)
    out: List[str] = []
    for name in sorted(os.listdir(root)):
        if name in {"workspaces", "_local"}:
            continue
        path = os.path.join(root, name)
        if not os.path.isdir(path):
            continue
        if not _is_probable_repo_hash(name):
            continue
        out.append(name)
    return out


def list_caches(base_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    root = cache_root(base_dir)
    policy = load_policy(base_dir)
    now = datetime.now(timezone.utc)
    rows: List[Dict[str, Any]] = []

    for repo_hash in _list_repo_hash_dirs(base_dir):
        cache_dir = os.path.join(root, repo_hash)
        meta = _load_metadata(repo_hash, base_dir=base_dir)
        manifest = _load_json(os.path.join(cache_dir, "manifest.json"), {})
        if isinstance(manifest, dict) and manifest.get("analysis_version") and not meta.get("analysis_version"):
            meta["analysis_version"] = manifest.get("analysis_version")

        expires = _compute_expiry(meta, policy, now=now)
        rows.append(
            {
                "repo_hash": repo_hash,
                "cache_dir": cache_dir,
                "source": str(meta.get("source", "filesystem") or "filesystem"),
                "repo_url": str(meta.get("repo_url", "") or ""),
                "repo_path": str(meta.get("repo_path", "") or ""),
                "ref": str(meta.get("ref", "") or ""),
                "workspace_dir": str(meta.get("workspace_dir", "") or ""),
                "analysis_version": str(meta.get("analysis_version", "") or manifest.get("analysis_version", "") or ""),
                "created_at": str(meta.get("created_at", "") or ""),
                "last_accessed_at": str(meta.get("last_accessed_at", "") or ""),
                "retention_days": int(meta.get("retention_days", policy.get("default_ttl_days", 14)) or 14),
                "private_mode": bool(meta.get("private_mode", False)),
                "size_bytes": _dir_size(cache_dir),
                "has": _artifact_flags(cache_dir),
                "expires": expires,
            }
        )

    return rows


def _load_workspaces(base_dir: Optional[str] = None) -> Dict[str, Any]:
    path = _workspaces_path(base_dir)
    raw = _load_json(path, {})
    if not isinstance(raw, dict):
        return {"active_repo_hash": "", "repos": []}
    repos = raw.get("repos") if isinstance(raw.get("repos"), list) else []
    return {"active_repo_hash": str(raw.get("active_repo_hash", "") or ""), "repos": repos}


def _save_workspaces(data: Dict[str, Any], base_dir: Optional[str] = None) -> None:
    payload = data if isinstance(data, dict) else {}
    repos = payload.get("repos") if isinstance(payload.get("repos"), list) else []
    payload = {
        "active_repo_hash": str(payload.get("active_repo_hash", "") or ""),
        "repos": _scrub_payload(repos),
    }
    if payload["active_repo_hash"] and not any(str((r or {}).get("repo_hash", "")) == payload["active_repo_hash"] for r in repos):
        payload["active_repo_hash"] = ""
    _atomic_json_write(_workspaces_path(base_dir), payload)


def _workspace_refcounts(base_dir: Optional[str] = None) -> Dict[str, int]:
    refs: Dict[str, int] = {}
    root = cache_root(base_dir)
    ws_root = os.path.realpath(os.path.join(root, "workspaces"))

    for item in list_caches(base_dir):
        ws = str(item.get("workspace_dir", "") or "").strip()
        if not ws:
            continue
        ws_real = os.path.realpath(ws)
        try:
            if os.path.commonpath([ws_root, ws_real]) != ws_root:
                continue
        except ValueError:
            continue
        refs[ws_real] = refs.get(ws_real, 0) + 1

    ws = _load_workspaces(base_dir)
    for repo in ws.get("repos", []):
        path = str((repo or {}).get("path", "") or "").strip()
        if not path:
            continue
        real = os.path.realpath(path)
        try:
            if os.path.commonpath([ws_root, real]) != ws_root:
                continue
        except ValueError:
            continue
        workspace_dir = os.path.dirname(real)
        refs[workspace_dir] = refs.get(workspace_dir, 0) + 1

    return refs


def _on_rm_error(func, path, exc_info):
    try:
        os.chmod(path, 0o700)
    except OSError:
        pass
    try:
        func(path)
    except Exception:
        pass


def _safe_rmtree(path: str, allowed_root: str) -> Tuple[bool, Optional[str]]:
    if not path:
        return False, None
    if not os.path.exists(path):
        return False, None
    root_real = os.path.realpath(allowed_root)
    target_real = os.path.realpath(path)
    try:
        if os.path.commonpath([root_real, target_real]) != root_real:
            return False, "TARGET_OUTSIDE_ALLOWED_ROOT"
    except ValueError:
        return False, "TARGET_OUTSIDE_ALLOWED_ROOT"
    try:
        shutil.rmtree(target_real, onerror=_on_rm_error)
        if os.path.exists(target_real):
            return False, "DELETE_INCOMPLETE"
        return True, None
    except Exception as e:
        return False, str(e)


def clear_cache(repo_hash: str, dry_run: bool = False, base_dir: Optional[str] = None) -> Dict[str, Any]:
    repo_hash = str(repo_hash or "").strip()
    root = cache_root(base_dir)
    cache_dir = os.path.join(root, repo_hash)
    meta = _load_metadata(repo_hash, base_dir=base_dir)
    workspace_dir = str(meta.get("workspace_dir", "") or "")

    would_delete: List[str] = []
    workspace_preserved: List[str] = []
    errors: List[str] = []

    if os.path.isdir(cache_dir):
        would_delete.append(os.path.abspath(cache_dir))

    ws_refs = _workspace_refcounts(base_dir)
    if workspace_dir and os.path.isdir(workspace_dir):
        ws_real = os.path.realpath(workspace_dir)
        if ws_refs.get(ws_real, 0) <= 1:
            would_delete.append(os.path.abspath(workspace_dir))
        else:
            workspace_preserved.append(os.path.abspath(workspace_dir))

    freed = sum(_dir_size(p) for p in would_delete if os.path.exists(p))

    if dry_run:
        return {
            "ok": True,
            "repo_hash": repo_hash,
            "dry_run": True,
            "deleted": False,
            "cache_dir": cache_dir,
            "workspace_dir": workspace_dir or None,
            "would_delete": would_delete,
            "workspace_preserved": workspace_preserved,
            "freed_bytes_estimate": int(freed),
            "errors": errors,
            "message": "Dry run only",
        }

    deleted_any = False
    if os.path.isdir(cache_dir):
        ok, err = _safe_rmtree(cache_dir, root)
        if ok:
            deleted_any = True
        elif err:
            errors.append(f"cache_dir:{err}")

    if workspace_dir and os.path.isdir(workspace_dir) and os.path.abspath(workspace_dir) in would_delete:
        ws_root = os.path.join(root, "workspaces")
        ok, err = _safe_rmtree(workspace_dir, ws_root)
        if ok:
            deleted_any = True
        elif err:
            errors.append(f"workspace_dir:{err}")

    ws = _load_workspaces(base_dir)
    repos = ws.get("repos", []) if isinstance(ws.get("repos"), list) else []
    repos = [r for r in repos if str((r or {}).get("repo_hash", "") or "") != repo_hash]
    ws["repos"] = repos
    active = str(ws.get("active_repo_hash", "") or "")
    if active == repo_hash:
        ws["active_repo_hash"] = ""
    _save_workspaces(ws, base_dir)

    return {
        "ok": True,
        "repo_hash": repo_hash,
        "dry_run": False,
        "deleted": bool(deleted_any and not errors),
        "cache_dir": cache_dir,
        "workspace_dir": workspace_dir or None,
        "would_delete": would_delete,
        "workspace_preserved": workspace_preserved,
        "freed_bytes_estimate": int(freed),
        "errors": errors,
        "message": "Deleted" if deleted_any and not errors else "Nothing deleted" if not would_delete else "Completed with warnings",
    }


def delete_repo(repo_hash: str, dry_run: bool = False, base_dir: Optional[str] = None) -> Dict[str, Any]:
    return clear_cache(repo_hash=repo_hash, dry_run=dry_run, base_dir=base_dir)


def sweep_expired(
    dry_run: bool = False,
    base_dir: Optional[str] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    current = now or datetime.now(timezone.utc)
    removed_hashes: List[str] = []
    workspaces_removed: List[str] = []
    would_delete: List[str] = []
    errors: List[str] = []
    freed = 0

    for item in list_caches(base_dir):
        exp = item.get("expires", {}) if isinstance(item.get("expires"), dict) else {}
        if not bool(exp.get("expired", False)):
            continue
        repo_hash = str(item.get("repo_hash", "") or "")
        if not repo_hash:
            continue
        result = clear_cache(repo_hash=repo_hash, dry_run=dry_run, base_dir=base_dir)
        paths = [str(p) for p in result.get("would_delete", []) if str(p)]
        would_delete.extend(paths)
        freed += int(result.get("freed_bytes_estimate", 0) or 0)
        if not result.get("errors"):
            removed_hashes.append(repo_hash)
        else:
            errors.extend(result.get("errors", []))
        for p in paths:
            if os.path.basename(os.path.dirname(p)) == "workspaces":
                workspaces_removed.append(p)

    policy = load_policy(base_dir)
    policy["last_cleanup_iso"] = current.isoformat()
    save_policy(policy, base_dir=base_dir)

    return {
        "ok": True,
        "dry_run": bool(dry_run),
        "deleted": bool((not dry_run) and (not errors)),
        "caches_removed": removed_hashes,
        "workspaces_removed": workspaces_removed,
        "would_delete": would_delete,
        "freed_bytes_estimate": int(freed),
        "errors": errors,
    }


def apply_retention(base_dir: Optional[str] = None, now: Optional[datetime] = None, dry_run: bool = False) -> Dict[str, Any]:
    return sweep_expired(dry_run=dry_run, base_dir=base_dir, now=now)


def cleanup(dry_run: bool = False, base_dir: Optional[str] = None) -> Dict[str, Any]:
    return sweep_expired(dry_run=dry_run, base_dir=base_dir)

