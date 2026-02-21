import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from security_utils import redact_payload, redact_secrets

def print_json(obj) -> None:
    safe_obj = redact_payload(obj)
    sys.stdout.write(json.dumps(safe_obj, indent=2))
    sys.stdout.write("\n")

MISSING_ANALYSIS_MESSAGE = "Run: python cli.py api analyze --path <repo>"
ANALYSIS_VERSION = "2.2"



def _analysis_root() -> str:
    # cli.py is at project root; analysis/ is sibling
    return os.path.join(os.path.dirname(__file__), "analysis")


def _global_cache_root() -> str:
    return os.path.join(os.path.dirname(__file__), ".codemap_cache")


def _safe_delete_dir(path: str, allowed_root: str) -> bool:
    if not path:
        return False
    if not os.path.exists(path):
        return False
    real_root = os.path.realpath(allowed_root)
    real_target = os.path.realpath(path)
    try:
        common = os.path.commonpath([real_root, real_target])
    except ValueError:
        return False
    if common != real_root:
        return False
    shutil.rmtree(real_target)
    return True


def _dir_size_bytes(path: str) -> int:
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


def _cache_root() -> str:
    root = _global_cache_root()
    os.makedirs(root, exist_ok=True)
    return root


def _load_workspace_registry() -> Dict[str, Any]:
    path = os.path.join(_cache_root(), "workspaces.json")
    if not os.path.exists(path):
        return {"active_repo_hash": "", "repos": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data.setdefault("repos", [])
            data.setdefault("active_repo_hash", "")
            return data
    except Exception:
        pass
    return {"active_repo_hash": "", "repos": []}


def _parse_iso_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_duration_days(spec: str) -> Optional[float]:
    raw = str(spec or "").strip().lower()
    if not raw:
        return None
    try:
        if raw.endswith("d"):
            return float(raw[:-1])
        if raw.endswith("h"):
            return float(raw[:-1]) / 24.0
        return float(raw)
    except Exception:
        return None


def _touch_repo_access_by_dir(repo_dir: Optional[str]) -> None:
    if not repo_dir:
        return
    try:
        from analysis.utils.cache_manager import compute_repo_hash, touch_last_accessed
        touch_last_accessed(compute_repo_hash(repo_dir))
    except Exception:
        pass


def _resolve_runtime_github_token(args) -> Tuple[Optional[str], str]:
    token_arg = str(getattr(args, "token", "") or "").strip()
    token_stdin = bool(getattr(args, "token_stdin", False))
    env_token = str(os.getenv("GITHUB_TOKEN", "") or "").strip()

    if token_arg:
        return token_arg, "arg"

    if token_stdin:
        try:
            stdin_token = str(sys.stdin.readline() or "").strip()
        except Exception:
            stdin_token = ""
        if stdin_token:
            return stdin_token, "stdin"

    if env_token:
        return env_token, "env"
    return None, "none"


def _save_workspace_registry(data: Dict[str, Any]) -> None:
    path = os.path.join(_cache_root(), "workspaces.json")
    data = dict(data or {})
    repos = data.get("repos")
    if not isinstance(repos, list):
        repos = []
    data["repos"] = repos
    if not repos:
        data["active_repo_hash"] = ""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _cache_artifact_map(cache_dir: str) -> Dict[str, bool]:
    return {
        "resolved_calls": os.path.exists(os.path.join(cache_dir, "resolved_calls.json")),
        "explain": os.path.exists(os.path.join(cache_dir, "explain.json")),
        "project_tree": os.path.exists(os.path.join(cache_dir, "project_tree.json")),
        "risk_radar": os.path.exists(os.path.join(cache_dir, "risk_radar.json")),
        "dependency_cycles": os.path.exists(os.path.join(cache_dir, "dependency_cycles.json")),
    }


def _read_manifest(cache_dir: str) -> Dict[str, Any]:
    path = os.path.join(cache_dir, "manifest.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _resolve_cache_target(args) -> Dict[str, Any]:
    from analysis.utils.cache_manager import compute_repo_hash, get_cache_dir
    from analysis.utils.repo_fetcher import resolve_workspace_paths

    path_value = str(getattr(args, "path", "") or "").strip()
    github_value = str(getattr(args, "github", "") or "").strip()
    ref_value = str(getattr(args, "ref", "") or "").strip() or None
    mode_value = str(getattr(args, "mode", "git") or "git").strip().lower() or "git"

    if path_value and github_value:
        return {"ok": False, "error": "INVALID_ARGS", "message": "Use either --path or --github, not both."}
    if not path_value and not github_value:
        return {"ok": False, "error": "INVALID_ARGS", "message": "Provide --path <repo> or --github <url>."}
    if mode_value not in {"git", "zip"}:
        return {"ok": False, "error": "INVALID_ARGS", "message": "--mode must be one of: git, zip"}

    if github_value:
        try:
            ws = resolve_workspace_paths(github_value, ref_value, mode_value)
        except Exception as e:
            return {"ok": False, "error": "INVALID_GITHUB_URL", "message": str(e)}
        repo_dir = ws["repo_dir"]
        cache_dir = get_cache_dir(repo_dir)
        return {
            "ok": True,
            "source": "github",
            "repo_dir": repo_dir,
            "repo_hash": compute_repo_hash(repo_dir),
            "cache_dir": cache_dir,
            "workspace_dir": ws["workspace_dir"],
            "repo_url": ws["normalized_url"],
            "ref": ref_value,
            "mode": mode_value,
        }

    repo_dir = resolve_repo_paths(path_value)["repo_dir"]
    cache_dir = get_cache_dir(repo_dir)
    return {
        "ok": True,
        "source": "filesystem",
        "repo_dir": repo_dir,
        "repo_hash": compute_repo_hash(repo_dir),
        "cache_dir": cache_dir,
        "workspace_dir": None,
        "repo_url": None,
        "ref": None,
        "mode": None,
    }


def _retention_from_manifest(manifest: Dict[str, Any]) -> Dict[str, Any]:
    data = manifest if isinstance(manifest, dict) else {}
    if "retention_days" in data:
        days = int(data.get("retention_days", 14) or 14)
        mode = "pinned" if days == 0 else "ttl"
        return {
            "mode": mode,
            "ttl_days": days,
            "created_at": str(data.get("created_at", "") or ""),
            "last_accessed_at": str(data.get("last_accessed_at", "") or ""),
        }
    retention = data.get("retention", {}) if isinstance(data.get("retention"), dict) else {}
    mode = str(retention.get("mode", "ttl") or "ttl")
    if mode not in {"ttl", "session_only", "pinned"}:
        mode = "ttl"
    ttl_days = int(retention.get("ttl_days", 14) or 14)
    if ttl_days < 0:
        ttl_days = 0
    created_at = str(retention.get("created_at") or data.get("updated_at") or "")
    last_accessed_at = str(retention.get("last_accessed_at") or created_at)
    return {"mode": mode, "ttl_days": ttl_days, "created_at": created_at, "last_accessed_at": last_accessed_at}


def api_cache_help(_args) -> int:
    print_json({
        "ok": True,
        "commands": [
            "python cli.py api cache list",
            "python cli.py api cache info --path <repo>",
            "python cli.py api cache info --github <url> --ref <ref> --mode <git|zip>",
            "python cli.py api cache clear --path <repo> [--dry-run] [--yes]",
            "python cli.py api cache clear --repo-hash <hash> [--dry-run] [--yes]",
            "python cli.py api cache clear --all [--dry-run] --yes",
            "python cli.py api cache retention --path <repo> --days 7 --yes",
            "python cli.py api cache retention --repo-hash <hash> --days 30 --yes",
            "python cli.py api cache sweep --dry-run",
            "python cli.py api cache sweep --yes",
        ],
    })
    return 0


def api_cache_policy_get(_args) -> int:
    from analysis.utils.cache_manager import load_policy

    print_json({"ok": True, "policy": load_policy()})
    return 0


def api_cache_policy_set(args) -> int:
    from analysis.utils.cache_manager import load_policy, save_policy

    current = load_policy()
    default_ttl = getattr(args, "default_ttl_days", None)
    ws_ttl = getattr(args, "workspaces_ttl_days", None)

    if default_ttl is not None and int(default_ttl) < 0:
        print_json({"ok": False, "error": "INVALID_ARGS", "message": "--default-ttl-days must be >= 0"})
        return 1
    if ws_ttl is not None and int(ws_ttl) < 0:
        print_json({"ok": False, "error": "INVALID_ARGS", "message": "--workspaces-ttl-days must be >= 0"})
        return 1

    updated = {
        "default_ttl_days": int(default_ttl) if default_ttl is not None else int(current.get("default_ttl_days", 30)),
        "workspaces_ttl_days": int(ws_ttl) if ws_ttl is not None else int(current.get("workspaces_ttl_days", 7)),
        "never_delete_repo_hashes": current.get("never_delete_repo_hashes", []),
        "repo_policies": current.get("repo_policies", {}),
        "last_cleanup_iso": current.get("last_cleanup_iso", ""),
    }
    policy = save_policy(updated)
    print_json({"ok": True, "policy": policy})
    return 0


def api_cache_list(_args) -> int:
    from analysis.utils.cache_manager import list_caches

    raw = list_caches()
    caches: List[Dict[str, Any]] = []
    for item in raw:
        expires = item.get("expires", {}) if isinstance(item.get("expires"), dict) else {}
        caches.append({
            "repo_hash": item.get("repo_hash"),
            "cache_dir": item.get("cache_dir"),
            "source": item.get("source", "filesystem"),
            "repo_url": item.get("repo_url") or None,
            "repo_path": item.get("repo_path") or None,
            "ref": item.get("ref") or None,
            "workspace_dir": item.get("workspace_dir") or None,
            "analysis_version": item.get("analysis_version") or None,
            "last_updated": item.get("last_accessed_at") or None,
            "retention": {
                "mode": expires.get("mode", "ttl"),
                "ttl_days": int(item.get("retention_days", 14) or 14),
                "created_at": item.get("created_at"),
                "last_accessed_at": item.get("last_accessed_at"),
                "days_left": expires.get("days_left"),
                "expired": bool(expires.get("expired", False)),
            },
            "private_mode": bool(item.get("private_mode", False)),
            "size_bytes": int(item.get("size_bytes", 0)),
            "has": item.get("has", {}),
        })

    print_json({"ok": True, "count": len(caches), "caches": caches})
    return 0


def api_cache_info(args) -> int:
    from analysis.utils.cache_manager import list_caches, touch_last_accessed

    target = _resolve_cache_target(args)
    if not target.get("ok"):
        print_json({"ok": False, "error": target.get("error"), "message": target.get("message"), "hint": "Use: python cli.py api cache help"})
        return 1

    cache_item = next((c for c in list_caches() if str(c.get("repo_hash")) == str(target["repo_hash"])), None)
    if not cache_item:
        print_json({
            "ok": False,
            "error": "CACHE_NOT_FOUND",
            "message": f"Cache directory not found: {target['cache_dir']}",
            "hint": "Run: python cli.py api analyze --path <repo>",
        })
        return 1

    cache_dir = str(cache_item.get("cache_dir", target["cache_dir"]))
    expires = cache_item.get("expires", {}) if isinstance(cache_item.get("expires"), dict) else {}
    retention = {
        "mode": expires.get("mode", "ttl"),
        "ttl_days": int(cache_item.get("retention_days", 14) or 14),
        "created_at": cache_item.get("created_at"),
        "last_accessed_at": cache_item.get("last_accessed_at"),
        "days_left": expires.get("days_left"),
        "expired": bool(expires.get("expired", False)),
    }
    files = {
        "resolved_calls_path": os.path.join(cache_dir, "resolved_calls.json") if os.path.exists(os.path.join(cache_dir, "resolved_calls.json")) else None,
        "explain_path": os.path.join(cache_dir, "explain.json") if os.path.exists(os.path.join(cache_dir, "explain.json")) else None,
        "project_tree_path": os.path.join(cache_dir, "project_tree.json") if os.path.exists(os.path.join(cache_dir, "project_tree.json")) else None,
        "risk_radar_path": os.path.join(cache_dir, "risk_radar.json") if os.path.exists(os.path.join(cache_dir, "risk_radar.json")) else None,
    }
    notes = []
    if files["explain_path"] is None:
        notes.append("missing explain.json; run: python cli.py api analyze --path <repo>")
    if files["resolved_calls_path"] is None:
        notes.append("missing resolved_calls.json; run: python cli.py api analyze --path <repo>")

    print_json({
        "ok": True,
        "repo_hash": target["repo_hash"],
        "cache_dir": os.path.abspath(cache_dir),
        "workspace_dir": cache_item.get("workspace_dir") or target.get("workspace_dir"),
        "source": cache_item.get("source", target["source"]),
        "analysis_version": cache_item.get("analysis_version"),
        "last_updated": cache_item.get("last_accessed_at"),
        "retention": retention,
        "files": files,
        "size_bytes": int(cache_item.get("size_bytes", 0)),
        "private_mode": bool(cache_item.get("private_mode", False)),
        "notes": notes,
    })
    touch_last_accessed(target["repo_hash"])
    return 0


def api_cache_clear(args) -> int:
    from analysis.utils.cache_manager import clear_cache, list_caches

    dry_run = bool(getattr(args, "dry_run", False))
    yes = bool(getattr(args, "yes", False))
    clear_all = bool(getattr(args, "all", False))
    repo_hash_arg = str(getattr(args, "repo_hash", "") or "").strip()

    if not dry_run and not yes:
        print_json({
            "ok": False,
            "error": "CONFIRM_REQUIRED",
            "message": "Pass --yes for destructive cache clear.",
            "hint": "Use --dry-run to preview deletion.",
        })
        return 1

    if clear_all:
        targets = [str(c.get("repo_hash", "")) for c in list_caches() if c.get("repo_hash")]
        results = [clear_cache(repo_hash=t, dry_run=dry_run) for t in targets]
        would_delete = [p for r in results for p in r.get("would_delete", [])]
        errors = [e for r in results for e in r.get("errors", [])]
        freed = sum(int(r.get("freed_bytes_estimate", 0)) for r in results)
        print_json({
            "ok": True,
            "all": True,
            "dry_run": dry_run,
            "deleted": bool(False if dry_run else not errors),
            "cache_count": len(targets),
            "would_delete": would_delete,
            "freed_bytes_estimate": int(freed),
            "errors": errors,
            "results": results,
        })
        return 0 if not errors else 1

    if not repo_hash_arg:
        target = _resolve_cache_target(args)
        if not target.get("ok"):
            print_json({"ok": False, "error": target.get("error"), "message": target.get("message"), "hint": "Use: python cli.py api cache help"})
            return 1
        repo_hash_arg = str(target["repo_hash"])

    result = clear_cache(repo_hash=repo_hash_arg, dry_run=dry_run)
    print_json(result)
    return 0 if not result.get("errors") else 1


def api_cache_retention(args) -> int:
    from analysis.utils.cache_manager import set_retention

    yes = bool(getattr(args, "yes", False))
    if not yes:
        print_json({
            "ok": False,
            "error": "CONFIRM_REQUIRED",
            "message": "Pass --yes to update retention.",
        })
        return 1

    days = int(getattr(args, "days", 14) or 14)
    if days < 0:
        print_json({"ok": False, "error": "INVALID_ARGS", "message": "--days must be >= 0"})
        return 1

    repo_hash_arg = str(getattr(args, "repo_hash", "") or "").strip()
    if not repo_hash_arg:
        target = _resolve_cache_target(args)
        if not target.get("ok"):
            print_json({"ok": False, "error": target.get("error"), "message": target.get("message"), "hint": "Use: python cli.py api cache help"})
            return 1
        repo_hash_arg = str(target["repo_hash"])

    metadata = set_retention(repo_hash=repo_hash_arg, days=days)
    print_json({
        "ok": True,
        "repo_hash": repo_hash_arg,
        "days": int(metadata.get("retention_days", days)),
        "metadata_path": os.path.join(_cache_root(), repo_hash_arg, "metadata.json"),
    })
    return 0


def api_cache_delete(args) -> int:
    repo_hash_arg = str(getattr(args, "repo_hash", "") or "").strip()
    if repo_hash_arg:
        from analysis.utils.cache_manager import delete_repo as cm_delete_repo

        dry_run = bool(getattr(args, "dry_run", False))
        yes = bool(getattr(args, "yes", False))
        if not dry_run and not yes:
            confirm = input(f"This will delete all cache artifacts for repo_hash={repo_hash_arg}. Continue? [y/N] ").strip().lower()
            if confirm not in {"y", "yes"}:
                print_json({"ok": False, "error": "ABORTED", "message": "Operation cancelled by user.", "hint": "Pass --yes to skip confirmation."})
                return 1
        result = cm_delete_repo(repo_hash=repo_hash_arg, dry_run=dry_run)
        print_json(result)
        return 0

    target = _resolve_cache_target(args)
    if not target.get("ok"):
        print_json({"ok": False, "error": target.get("error"), "message": target.get("message"), "hint": "Use: python cli.py api cache help"})
        return 1

    dry_run = bool(getattr(args, "dry_run", False))
    yes = bool(getattr(args, "yes", False))
    cache_root = _cache_root()
    cache_dir = target["cache_dir"]
    workspace_dir = target.get("workspace_dir")

    would_delete: List[str] = []
    if os.path.isdir(cache_dir):
        would_delete.append(os.path.abspath(cache_dir))
    if workspace_dir and os.path.isdir(workspace_dir):
        would_delete.append(os.path.abspath(workspace_dir))

    freed = sum(_dir_size_bytes(p) for p in would_delete if os.path.isdir(p))
    if dry_run:
        print_json({
            "ok": True,
            "dry_run": True,
            "repo_hash": target["repo_hash"],
            "deleted": False,
            "would_delete": would_delete,
            "freed_bytes_estimate": int(freed),
        })
        return 0

    if not yes:
        confirm = input(f"This will delete all cache artifacts for repo_hash={target['repo_hash']}. Continue? [y/N] ").strip().lower()
        if confirm not in {"y", "yes"}:
            print_json({"ok": False, "error": "ABORTED", "message": "Operation cancelled by user.", "hint": "Pass --yes to skip confirmation."})
            return 1

    deleted_any = False
    for path in would_delete:
        if _safe_delete_dir(path, cache_root):
            deleted_any = True

    ws = _load_workspace_registry()
    repos = ws.get("repos", []) if isinstance(ws, dict) else []
    if workspace_dir:
        ws_real = os.path.realpath(workspace_dir)
        repos = [
            r for r in repos
            if not os.path.realpath(str((r or {}).get("path", "") or "")).startswith(ws_real)
        ]
        ws["repos"] = repos
        active = str(ws.get("active_repo_hash", "") or "")
        if active and not any(str((r or {}).get("repo_hash", "")) == active for r in repos):
            ws["active_repo_hash"] = ""
        _save_workspace_registry(ws)

    print_json({
        "ok": True,
        "dry_run": False,
        "repo_hash": target["repo_hash"],
        "deleted": bool(deleted_any),
        "would_delete": would_delete,
        "freed_bytes_estimate": int(freed),
    })
    return 0


def api_cache_cleanup(args) -> int:
    from analysis.utils.cache_manager import sweep_expired

    apply_flag = bool(getattr(args, "apply", False))
    dry_run = bool(getattr(args, "dry_run", False)) and not apply_flag
    yes = bool(getattr(args, "yes", False)) or apply_flag
    if not dry_run and not yes:
        print_json({
            "ok": False,
            "error": "CONFIRM_REQUIRED",
            "message": "Pass --yes (or --apply) for cleanup deletion.",
            "hint": "Use --dry-run to preview deletion.",
        })
        return 1

    result = sweep_expired(dry_run=dry_run)
    print_json(result)
    return 0 if not result.get("errors") else 1


def api_cache_prune(args) -> int:
    dry_run = bool(getattr(args, "dry_run", False))
    yes = bool(getattr(args, "yes", False))
    older_than_days = _parse_duration_days(str(getattr(args, "older_than", "") or ""))
    if older_than_days is None:
        older_than_days = 0.0

    cache_root = _cache_root()
    now = _now_utc()
    candidates: List[Dict[str, Any]] = []

    for name in sorted(os.listdir(cache_root)):
        if name in {"workspaces", "workspaces.json"}:
            continue
        cache_dir = os.path.join(cache_root, name)
        if not os.path.isdir(cache_dir):
            continue
        manifest = _read_manifest(cache_dir)
        retention = _retention_from_manifest(manifest)
        mode = retention["mode"]
        if mode == "pinned":
            continue
        last_access = _parse_iso_dt(retention.get("last_accessed_at")) or _parse_iso_dt(retention.get("created_at")) or _parse_iso_dt(manifest.get("updated_at"))
        if last_access is None:
            last_access = now
        age_days = (now - last_access).total_seconds() / 86400.0
        policy_days = 1.0 if mode == "session_only" else float(retention.get("ttl_days", 14))
        eligible_policy = age_days > policy_days
        eligible_older_than = age_days > older_than_days
        if eligible_policy and eligible_older_than:
            candidates.append({
                "repo_hash": name,
                "cache_dir": os.path.abspath(cache_dir),
                "age_days": round(age_days, 3),
                "retention_mode": mode,
                "ttl_days": policy_days,
                "size_bytes": _dir_size_bytes(cache_dir),
            })

    would_delete = [c["cache_dir"] for c in candidates]
    freed = sum(int(c["size_bytes"]) for c in candidates)
    if dry_run:
        print_json({
            "ok": True,
            "dry_run": True,
            "deleted": False,
            "count": len(candidates),
            "candidates": candidates,
            "would_delete": would_delete,
            "freed_bytes_estimate": int(freed),
        })
        return 0

    if not yes:
        confirm = input(f"This will prune {len(candidates)} cache directories. Continue? [y/N] ").strip().lower()
        if confirm not in {"y", "yes"}:
            print_json({"ok": False, "error": "ABORTED", "message": "Operation cancelled by user.", "hint": "Pass --yes to skip confirmation."})
            return 1

    deleted = []
    for c in candidates:
        if _safe_delete_dir(c["cache_dir"], cache_root):
            deleted.append(c["cache_dir"])

    print_json({
        "ok": True,
        "dry_run": False,
        "deleted": True,
        "count": len(deleted),
        "would_delete": deleted,
        "freed_bytes_estimate": int(freed),
    })
    return 0


def api_cache_sweep(args) -> int:
    # Backward-compatible implementation path routed to cleanup behavior.
    return api_cache_cleanup(args)


def _build_project_tree_snapshot(repo_dir: str) -> Dict[str, Any]:
    repo_dir = os.path.abspath(repo_dir)
    ignore_dirs = {".git", ".codemap_cache", "__pycache__", ".venv", "venv", "node_modules"}
    root = {
        "name": os.path.basename(repo_dir.rstrip("\\/")) or repo_dir,
        "type": "directory",
        "path": "",
        "children": [],
    }
    nodes: Dict[str, Dict[str, Any]] = {"": root}

    for current_root, dirs, files in os.walk(repo_dir):
        dirs[:] = sorted([d for d in dirs if d not in ignore_dirs and not d.startswith(".")])
        files = sorted([f for f in files if not f.startswith(".")])

        rel_root = os.path.relpath(current_root, repo_dir)
        rel_root = "" if rel_root == "." else rel_root.replace("\\", "/")
        parent = nodes[rel_root]

        for d in dirs:
            rel_path = f"{rel_root}/{d}" if rel_root else d
            node = {"name": d, "type": "directory", "path": rel_path, "children": []}
            parent["children"].append(node)
            nodes[rel_path] = node

        for f in files:
            rel_path = f"{rel_root}/{f}" if rel_root else f
            parent["children"].append({"name": f, "type": "file", "path": rel_path})

    return root


def resolve_repo_paths(repo_dir: Optional[str]) -> Dict[str, str]:
    if not repo_dir:
        output_dir = os.path.join(_analysis_root(), "output")
        return {
            "repo_dir": "",
            "cache_dir": output_dir,
            "explain_path": os.path.join(output_dir, "explain.json"),
            "resolved_calls_path": os.path.join(output_dir, "resolved_calls.json"),
            "llm_cache_path": os.path.join(output_dir, "llm_cache.json"),
        }

    repo_candidate = os.path.abspath(repo_dir)
    if not os.path.exists(repo_candidate):
        alt_candidate = os.path.abspath(os.path.join(_analysis_root(), repo_dir))
        if os.path.exists(alt_candidate):
            repo_candidate = alt_candidate

    from analysis.utils.cache_manager import get_cache_dir
    cache_dir = get_cache_dir(repo_candidate)
    return {
        "repo_dir": repo_candidate,
        "cache_dir": cache_dir,
        "explain_path": os.path.join(cache_dir, "explain.json"),
        "resolved_calls_path": os.path.join(cache_dir, "resolved_calls.json"),
        "llm_cache_path": os.path.join(cache_dir, "llm_cache.json"),
    }


def load_explain_db(repo: Optional[str] = None) -> Dict[str, Any]:
    paths = resolve_repo_paths(repo)
    path = paths["explain_path"]
    if not os.path.exists(path):
        hint = (
            "Run:\n  python cli.py api analyze --path <repo>\n"
            "to build repo-scoped cache before querying with --repo."
            if repo else
            "Run:\n  python -m analysis.explain.explain_runner\n"
            "after generating resolved_calls.json from Phase-4 runner."
        )
        raise FileNotFoundError(
            f"explain.json not found at:\n  {path}\n\n"
            f"{hint}"
        )
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _symbol_payload(item: Dict[str, Any], fallback_fqn: str) -> Dict[str, Any]:
    location = item.get("location") or {}
    return {
        "fqn": item.get("fqn", fallback_fqn),
        "one_liner": item.get("one_liner", ""),
        "details": item.get("details", []),
        "tags": item.get("tags", []),
        "location": {
            "file": location.get("file", ""),
            "start_line": location.get("start_line", -1),
            "end_line": location.get("end_line", -1),
        },
    }


def suggest_keys(db: Dict[str, Any], query: str, k: int = 5) -> List[str]:
    q = query.lower()
    # simple scoring: substring + shared suffix parts
    scored: List[Tuple[int, str]] = []
    for key in db.keys():
        kl = key.lower()
        score = 0
        if q in kl:
            score += 10
        # bonus for matching last segment(s)
        q_parts = q.split(".")
        k_parts = kl.split(".")
        common_suffix = 0
        while common_suffix < min(len(q_parts), len(k_parts)):
            if q_parts[-1 - common_suffix] == k_parts[-1 - common_suffix]:
                common_suffix += 1
            else:
                break
        score += common_suffix * 3
        if score > 0:
            scored.append((score, key))
    scored.sort(reverse=True, key=lambda x: x[0])
    return [s[1] for s in scored[:k]]


def cmd_explain(args) -> int:
    db = load_explain_db(args.repo)
    fqn = args.fqn

    if fqn not in db:
        print(f"\n❌ Not found: {fqn}\n")
        suggestions = suggest_keys(db, fqn, k=8)
        if suggestions:
            print("Did you mean:")
            for s in suggestions:
                print(f"  - {s}")
        else:
            print("No similar symbols found. Try: python cli.py search <keyword>")
        print()
        return 1

    item = db[fqn]

    print("\n" + "=" * 80)
    print(f"{item.get('fqn', fqn)}")
    print("-" * 80)
    print(item.get("one_liner", ""))
    print()

    details = item.get("details", [])
    if details:
        for d in details:
            print(f"- {d}")

    tags = item.get("tags", [])
    if tags:
        print("\nTags: " + ", ".join(tags))

    print("=" * 80 + "\n")
    if args.repo:
        _touch_repo_access_by_dir(resolve_repo_paths(args.repo)["repo_dir"])
    return 0


def cmd_search(args) -> int:
    db = load_explain_db(args.repo)
    q = args.query.lower()

    matches = [k for k in db.keys() if q in k.lower()]
    matches.sort()

    limit = args.limit
    print(f"\nFound {len(matches)} matches for '{args.query}':\n")
    for k in matches[:limit]:
        print(f"- {k}")

    if len(matches) > limit:
        print(f"\n...and {len(matches) - limit} more. Use --limit to increase.")
    print()
    if args.repo:
        _touch_repo_access_by_dir(resolve_repo_paths(args.repo)["repo_dir"])
    return 0


def cmd_list(args) -> int:
    db = load_explain_db(args.repo)
    keys = sorted(db.keys())

    if args.module:
        prefix = args.module.strip()
        keys = [k for k in keys if k.startswith(prefix)]

    limit = args.limit
    print(f"\nListing {min(len(keys), limit)} of {len(keys)} symbols:\n")
    for k in keys[:limit]:
        print(f"- {k}")

    if len(keys) > limit:
        print(f"\n...and {len(keys) - limit} more. Use --limit to increase.")
    print()
    if args.repo:
        _touch_repo_access_by_dir(resolve_repo_paths(args.repo)["repo_dir"])
    return 0


def api_explain(args) -> int:
    paths = resolve_repo_paths(args.repo)
    if args.repo and not os.path.exists(paths["explain_path"]):
        print_json({
            "ok": False,
            "error": "MISSING_ANALYSIS",
            "message": MISSING_ANALYSIS_MESSAGE,
        })
        return 1

    db = load_explain_db(args.repo)
    fqn = args.fqn

    if fqn not in db:
        print_json({
            "ok": False,
            "error": "NOT_FOUND",
            "fqn": fqn,
        })
        return 1

    print_json({
        "ok": True,
        "result": _symbol_payload(db[fqn], fqn)
    })
    if args.repo:
        _touch_repo_access_by_dir(paths["repo_dir"])
    return 0


def api_search(args) -> int:
    paths = resolve_repo_paths(args.repo)
    if args.repo and not os.path.exists(paths["explain_path"]):
        print_json({
            "ok": False,
            "error": "MISSING_ANALYSIS",
            "message": MISSING_ANALYSIS_MESSAGE,
        })
        return 1

    db = load_explain_db(args.repo)
    q = args.query.lower()
    matches = [k for k in db.keys() if q in k.lower()]
    matches.sort()
    results = matches[:args.limit]
    print_json({
        "ok": True,
        "query": args.query,
        "count": len(matches),
        "results": results,
        "truncated": len(matches) > args.limit
    })
    if args.repo:
        _touch_repo_access_by_dir(paths["repo_dir"])
    return 0


def api_list(args) -> int:
    paths = resolve_repo_paths(args.repo)
    if args.repo and not os.path.exists(paths["explain_path"]):
        print_json({
            "ok": False,
            "error": "MISSING_ANALYSIS",
            "message": MISSING_ANALYSIS_MESSAGE,
        })
        return 1

    db = load_explain_db(args.repo)
    keys = sorted(db.keys())

    if args.module:
        prefix = args.module.strip()
        keys = [k for k in keys if k.startswith(prefix)]

    results = keys[:args.limit]
    print_json({
        "ok": True,
        "module": args.module,
        "count": len(keys),
        "results": results,
        "truncated": len(keys) > args.limit
    })
    if args.repo:
        _touch_repo_access_by_dir(paths["repo_dir"])
    return 0


def api_status(args) -> int:
    path = resolve_repo_paths(args.repo)["explain_path"]
    if not os.path.exists(path):
        print_json({
            "ok": False,
            "error": "EXPLAIN_JSON_MISSING",
            "path": path
        })
        return 1

    # lightweight stats (no full load needed, but we can load safely)
    db = load_explain_db(args.repo)
    print_json({
        "ok": True,
        "path": path,
        "symbols": len(db)
    })
    if args.repo:
        _touch_repo_access_by_dir(resolve_repo_paths(args.repo)["repo_dir"])
    return 0


def api_llm_explain(args) -> int:
    from analysis.explain.ai_client import llm_explain_symbol

    paths = resolve_repo_paths(args.repo)
    if not os.path.exists(paths["explain_path"]):
        print_json({
            "ok": False,
            "error": "MISSING_ANALYSIS",
            "message": MISSING_ANALYSIS_MESSAGE,
        })
        return 1

    force = bool(getattr(args, "force", False) or getattr(args, "no_cache", False))

    result = llm_explain_symbol(fqn=args.fqn, repo_dir=paths["repo_dir"], no_cache=force)
    print_json(result)
    _touch_repo_access_by_dir(paths["repo_dir"])
    return 0 if result.get("ok") else 1


def api_repo_summary(args) -> int:
    from analysis.explain import ai_client
    from analysis.explain.repo_summary_generator import generate_repo_summary
    from analysis.utils.cache_manager import compute_repo_hash

    paths = resolve_repo_paths(args.repo)
    repo_dir = paths["repo_dir"]
    cache_dir = paths["cache_dir"]

    architecture_metrics_path = os.path.join(cache_dir, "architecture_metrics.json")
    dependency_cycles_path = os.path.join(cache_dir, "dependency_cycles.json")
    if not os.path.exists(architecture_metrics_path) or not os.path.exists(dependency_cycles_path):
        print_json({
            "ok": False,
            "repo": os.path.basename(os.path.abspath(repo_dir).rstrip("\\/")),
            "repo_hash": compute_repo_hash(repo_dir),
            "cached": False,
            "provider": None,
            "summary": {},
            "error": "Missing architecture cache. Run: python cli.py api analyze --path <repo>",
        })
        return 1

    force = bool(getattr(args, "force", False))

    result = generate_repo_summary(repo_cache_dir=cache_dir, llm_client=ai_client)
    if not result.get("ok"):
        print_json({
            "ok": False,
            "repo": os.path.basename(os.path.abspath(repo_dir).rstrip("\\/")),
            "repo_hash": compute_repo_hash(repo_dir),
            "cached": bool(result.get("cached", False)),
            "provider": result.get("provider"),
            "summary": {},
            "error": result.get("error"),
        })
        return 1

    final = {
        "ok": True,
        "repo": os.path.basename(os.path.abspath(repo_dir).rstrip("\\/")),
        "repo_hash": compute_repo_hash(repo_dir),
        "cached": bool(result.get("cached", False)),
        "provider": result.get("provider"),
        "summary": result.get("summary", {}),
        "error": None,
    }

    repo_summary_path = os.path.join(cache_dir, "repo_summary.json")
    with open(repo_summary_path, "w", encoding="utf-8") as f:
        json.dump(final, f, indent=2)

    print_json(final)
    _touch_repo_access_by_dir(repo_dir)
    return 0


def api_risk_radar(args) -> int:
    from analysis.architecture.risk_radar import compute_risk_radar
    from analysis.utils.cache_manager import compute_repo_hash

    paths = resolve_repo_paths(args.repo)
    repo_dir = paths["repo_dir"]
    cache_dir = paths["cache_dir"]

    architecture_metrics_path = os.path.join(cache_dir, "architecture_metrics.json")
    dependency_cycles_path = os.path.join(cache_dir, "dependency_cycles.json")
    analysis_metrics_path = os.path.join(cache_dir, "analysis_metrics.json")
    if (
        not os.path.exists(architecture_metrics_path)
        or not os.path.exists(dependency_cycles_path)
        or not os.path.exists(analysis_metrics_path)
    ):
        print_json({
            "ok": False,
            "cached": False,
            "repo": os.path.basename(os.path.abspath(repo_dir).rstrip("\\/")),
            "repo_hash": compute_repo_hash(repo_dir),
            "error": "Run analyze first",
        })
        return 1

    try:
        radar = compute_risk_radar(cache_dir=cache_dir, top_k=25)
    except Exception as e:
        print_json({"ok": False, "cached": False, "error": str(e)})
        return 1

    risk_radar_path = os.path.join(cache_dir, "risk_radar.json")
    with open(risk_radar_path, "w", encoding="utf-8") as f:
        json.dump(radar, f, indent=2)

    health = radar.get("repo_health", {})
    print_json({
        "ok": True,
        "cached": False,
        "risk_radar_path": risk_radar_path,
        "summary": {
            "hotspot_symbols": int(health.get("hotspot_symbols", 0)),
            "risky_files": int(health.get("risky_files", 0)),
            "dead_symbols": int(health.get("dead_symbols", 0)),
            "dependency_cycles": int(health.get("dependency_cycles", 0)),
            "unresolved_ratio": float(health.get("unresolved_ratio", 0.0)),
        },
    })
    _touch_repo_access_by_dir(repo_dir)
    return 0


def api_impact(args) -> int:
    from analysis.graph.impact_analyzer import compute_impact

    paths = resolve_repo_paths(args.repo)
    cache_dir = paths["cache_dir"]

    resolved_calls_path = os.path.join(cache_dir, "resolved_calls.json")
    architecture_metrics_path = os.path.join(cache_dir, "architecture_metrics.json")
    if not os.path.exists(resolved_calls_path) or not os.path.exists(architecture_metrics_path):
        print_json({
            "ok": False,
            "error": "MISSING_ANALYSIS",
            "message": MISSING_ANALYSIS_MESSAGE,
        })
        return 1

    try:
        payload = compute_impact(
            cache_dir=cache_dir,
            target=args.target,
            depth=args.depth,
            max_nodes=args.max_nodes,
        )
    except Exception as e:
        print_json({"ok": False, "error": "IMPACT_FAILED", "message": str(e)})
        return 1

    print_json(payload)
    _touch_repo_access_by_dir(paths["repo_dir"])
    return 0


def api_analyze(args) -> int:
    from analysis.runners.phase4_runner import run as run_phase4
    from analysis.explain.explain_runner import run as run_explain
    from analysis.graph.callgraph_index import CallGraphIndex, CallSite, write_hub_metrics_from_resolved_calls
    from analysis.indexing.symbol_index import SymbolIndex
    from analysis.architecture.architecture_engine import compute_architecture_metrics
    from analysis.architecture.dependency_cycles import compute_dependency_cycle_metrics
    from analysis.architecture.risk_radar import compute_risk_radar
    from analysis.utils.repo_fetcher import fetch_public_repo, fetch_public_repo_zip
    from analysis.utils.cache_manager import (
        build_manifest,
        collect_fingerprints,
        compute_repo_hash,
        diff_fingerprints,
        get_cache_dir,
        load_manifest,
        upsert_metadata,
        save_manifest,
        set_retention,
        should_rebuild,
        touch_last_accessed,
    )

    path_arg = getattr(args, "path", None)
    github_arg = getattr(args, "github", None)
    ref_arg = getattr(args, "ref", None)
    mode_arg = str(getattr(args, "mode", "git") or "git").strip().lower()
    retention_mode = str(getattr(args, "retention", "ttl") or "ttl").strip().lower()
    ttl_days_input = getattr(args, "ttl_days", None)
    ttl_days_arg = int(ttl_days_input) if ttl_days_input is not None else 14
    refresh_flag = bool(getattr(args, "refresh", False))
    rebuild_flag = bool(getattr(args, "rebuild", False))
    clear_cache_flag = bool(getattr(args, "clear_cache", False))
    force_full_rebuild = bool(rebuild_flag or refresh_flag or retention_mode == "session_only")
    path_value = str(path_arg).strip() if path_arg is not None else ""
    github_value = str(github_arg).strip() if github_arg is not None else ""

    if path_value and github_value:
        print_json({
            "ok": False,
            "error": "INVALID_ARGS",
            "message": "Use either --path <dir> or --github <url>, not both.",
        })
        return 1
    if refresh_flag and not github_value:
        print_json({
            "ok": False,
            "error": "INVALID_ARGS",
            "message": "--refresh is supported only with --github.",
        })
        return 1
    if mode_arg not in {"git", "zip"}:
        print_json({
            "ok": False,
            "error": "INVALID_ARGS",
            "message": "--mode must be one of: git, zip",
        })
        return 1
    if mode_arg == "zip" and not github_value:
        print_json({
            "ok": False,
            "error": "INVALID_ARGS",
            "message": "--mode zip requires --github.",
        })
        return 1
    if retention_mode not in {"ttl", "session_only", "pinned"}:
        print_json({
            "ok": False,
            "error": "INVALID_ARGS",
            "message": "--retention must be one of: ttl, session_only, pinned",
        })
        return 1
    if ttl_days_arg < 0:
        print_json({
            "ok": False,
            "error": "INVALID_ARGS",
            "message": "--ttl-days must be >= 0",
        })
        return 1

    source = "filesystem"
    mode = "filesystem"
    auth = "none"
    repo_url = None
    workspace_dir = None
    fetched = None
    refreshed = False
    resolved_ref = None
    cache_cleared = False
    downloaded = None
    zip_url = None
    token_value: Optional[str] = None
    private_repo_mode = False

    if github_value:
        source = "github"
        token_value, auth = _resolve_runtime_github_token(args)
        private_repo_mode = bool(token_value)
        mode = mode_arg
        if mode_arg == "zip":
            fetch_result = fetch_public_repo_zip(
                github_value,
                ref=str(ref_arg or ""),
                refresh=refresh_flag,
                token=token_value,
                auth=auth,
            )
        else:
            fetch_result = fetch_public_repo(
                github_value,
                ref=ref_arg,
                refresh=refresh_flag,
                token=token_value,
                auth=auth,
            )
        if not fetch_result.get("ok"):
            err_code = fetch_result.get("error_code")
            print_json({
                "ok": False,
                "error": err_code or "GITHUB_FETCH_FAILED",
                "message": redact_secrets(fetch_result.get("error", "Failed to fetch GitHub repository"), extra_secrets=[token_value] if token_value else None),
                "source": source,
                "mode": mode,
                "auth": auth,
                "repo_url": github_value,
                "ref": ref_arg,
            })
            return 1
        repo_dir = fetch_result["repo_dir"]
        repo_url = fetch_result.get("normalized_url")
        workspace_dir = fetch_result.get("workspace_dir")
        fetched = bool(fetch_result.get("fetched"))
        refreshed = bool(fetch_result.get("refreshed", False))
        resolved_ref = fetch_result.get("ref")
        downloaded = fetch_result.get("downloaded")
        zip_url = fetch_result.get("zip_url")
        token_value = None
    else:
        mode = "filesystem"
        repo_dir_input = path_value or "."
        repo_dir = resolve_repo_paths(repo_dir_input)["repo_dir"]

    if retention_mode == "pinned":
        retention_days_effective = 0
    elif retention_mode == "session_only":
        retention_days_effective = 1
    else:
        retention_days_effective = 7 if (ttl_days_input is None and private_repo_mode) else ttl_days_arg
    if retention_days_effective < 0:
        retention_days_effective = 0

    cache_dir = get_cache_dir(repo_dir)
    if clear_cache_flag:
        cache_cleared = _safe_delete_dir(cache_dir, _global_cache_root())
    os.makedirs(cache_dir, exist_ok=True)

    resolved_calls_path = os.path.join(cache_dir, "resolved_calls.json")
    explain_path = os.path.join(cache_dir, "explain.json")
    analysis_metrics_path = os.path.join(cache_dir, "analysis_metrics.json")
    architecture_metrics_path = os.path.join(cache_dir, "architecture_metrics.json")
    dependency_cycles_path = os.path.join(cache_dir, "dependency_cycles.json")
    risk_radar_path = os.path.join(cache_dir, "risk_radar.json")
    llm_cache_path = os.path.join(cache_dir, "llm_cache.json")
    project_tree_path = os.path.join(cache_dir, "project_tree.json")

    previous_manifest = load_manifest(repo_dir)
    previous_fingerprints = previous_manifest.get("fingerprints", {})
    current_fingerprints = collect_fingerprints(repo_dir)
    delta = diff_fingerprints(previous_fingerprints, current_fingerprints)
    version_mismatch = previous_manifest.get("analysis_version") != ANALYSIS_VERSION

    rebuild_required = bool(force_full_rebuild or should_rebuild(repo_dir, analysis_version=ANALYSIS_VERSION))
    architecture_missing = not os.path.exists(architecture_metrics_path)
    dependency_missing = not os.path.exists(dependency_cycles_path)
    risk_missing = not os.path.exists(risk_radar_path)
    r1 = {}
    r2 = {}
    metrics = {}

    try:
        if rebuild_required:
            r1 = run_phase4(
                repo_dir=repo_dir,
                output_dir=cache_dir,
                force_rebuild=bool(version_mismatch or force_full_rebuild),
            )
            r2 = run_explain(repo_dir=repo_dir, output_dir=cache_dir)
            resolved_calls_path = r1.get("resolved_calls_path", resolved_calls_path)
            metrics = write_hub_metrics_from_resolved_calls(
                resolved_calls_path=resolved_calls_path,
                output_path=analysis_metrics_path,
            )
            save_manifest(
                repo_dir,
                build_manifest(
                    repo_dir,
                    current_fingerprints,
                    metadata={
                        "analysis_version": ANALYSIS_VERSION,
                        "retention": {
                            "mode": retention_mode,
                            "ttl_days": int(retention_days_effective),
                            "created_at": datetime.now(timezone.utc).isoformat(),
                            "last_accessed_at": datetime.now(timezone.utc).isoformat(),
                        },
                        "symbol_snapshot": r1.get("symbol_snapshot", []),
                        "imports_snapshot": r1.get("imports_snapshot", {}),
                        "file_module_map": r1.get("file_module_map", {}),
                        "metrics_summary": {
                            "critical_apis": len(metrics.get("critical_apis", [])),
                            "orchestrators": len(metrics.get("orchestrators", [])),
                        },
                    },
                ),
            )
            tree_snapshot = _build_project_tree_snapshot(repo_dir)
            with open(project_tree_path, "w", encoding="utf-8") as f:
                json.dump(tree_snapshot, f, indent=2)
        elif os.path.exists(resolved_calls_path):
            metrics = write_hub_metrics_from_resolved_calls(
                resolved_calls_path=resolved_calls_path,
                output_path=analysis_metrics_path,
            )
            if not os.path.exists(project_tree_path):
                tree_snapshot = _build_project_tree_snapshot(repo_dir)
                with open(project_tree_path, "w", encoding="utf-8") as f:
                    json.dump(tree_snapshot, f, indent=2)

        # Derived architecture outputs:
        # - regenerate on rebuild
        # - regenerate if architecture/dependency artifacts are missing
        if rebuild_required or architecture_missing or dependency_missing:
            with open(resolved_calls_path, "r", encoding="utf-8") as f:
                resolved_calls = json.load(f)

            callgraph = CallGraphIndex()
            for c in resolved_calls:
                caller_fqn = c.get("caller_fqn")
                if not caller_fqn:
                    continue
                callgraph.add_call(
                    CallSite(
                        caller_fqn=caller_fqn,
                        callee_fqn=c.get("callee_fqn"),
                        callee_name=c.get("callee", "<unknown>"),
                        file=c.get("file", ""),
                        line=int(c.get("line", -1)),
                    )
                )

            symbol_index = SymbolIndex()
            symbol_snapshot = r1.get("symbol_snapshot") or previous_manifest.get("symbol_snapshot", [])
            if symbol_snapshot:
                symbol_index.load_snapshot(symbol_snapshot)

            repo_prefix = os.path.basename(os.path.abspath(repo_dir).rstrip("\\/"))
            arch_payload = compute_architecture_metrics(
                callgraph=callgraph,
                symbol_index=symbol_index,
                repo_prefix=repo_prefix,
            )
            dep_payload = compute_dependency_cycle_metrics(
                resolved_calls=resolved_calls,
                repo_prefix=repo_prefix,
            )

            with open(architecture_metrics_path, "w", encoding="utf-8") as f:
                json.dump(arch_payload, f, indent=2)
            with open(dependency_cycles_path, "w", encoding="utf-8") as f:
                json.dump(dep_payload, f, indent=2)

        # Risk radar derived output:
        # - regenerate on rebuild
        # - regenerate when missing (cached analyze run)
        # - regenerate when architecture/dependency were regenerated
        if rebuild_required or risk_missing or architecture_missing or dependency_missing:
            risk_payload = compute_risk_radar(cache_dir=cache_dir, top_k=25)
            with open(risk_radar_path, "w", encoding="utf-8") as f:
                json.dump(risk_payload, f, indent=2)
        repo_hash = compute_repo_hash(repo_dir)
        upsert_metadata(
            repo_hash=repo_hash,
            source=source,
            repo_path=os.path.abspath(repo_dir),
            repo_url=repo_url or "",
            ref=str(resolved_ref or ref_arg or ""),
            workspace_dir=workspace_dir or "",
            analysis_version=ANALYSIS_VERSION,
            private_mode=bool(private_repo_mode),
        )
        set_retention(
            repo_hash=repo_hash,
            days=int(retention_days_effective),
        )
        touch_last_accessed(repo_hash)
    except Exception as e:
        print_json({"ok": False, "error": "ANALYZE_FAILED", "message": redact_secrets(str(e))})
        return 1

    print_json({
        "ok": True,
        "source": source,
        "mode": mode,
        "auth": auth,
        "private_repo_mode": private_repo_mode,
        "cached": not rebuild_required,
        "rebuilt": rebuild_flag,
        "cache_cleared": cache_cleared,
        "refreshed": refreshed,
        "changed_files": delta["changed_files"],
        "incremental": False if version_mismatch else r1.get("incremental", False),
        "reindexed_files": r1.get("reindexed_files", 0),
        "impacted_files": r1.get("impacted_files", 0),
        "analysis_version": ANALYSIS_VERSION,
        "version_mismatch_rebuild": bool(version_mismatch and rebuild_required),
        "cache_dir": cache_dir,
        "resolved_calls_path": r1.get("resolved_calls_path", resolved_calls_path),
        "explain_path": r2.get("explain_path", explain_path),
        "analysis_metrics_path": analysis_metrics_path,
        "architecture_metrics_path": architecture_metrics_path,
        "dependency_cycles_path": dependency_cycles_path,
        "risk_radar_path": risk_radar_path,
        "llm_cache_path": llm_cache_path,
        "project_tree_path": project_tree_path,
        "critical_apis": len(metrics.get("critical_apis", [])),
        "orchestrators": len(metrics.get("orchestrators", [])),
        "repo_url": repo_url,
        "ref": resolved_ref,
        "workspace_dir": workspace_dir,
        "fetched": fetched,
        "downloaded": downloaded,
        "zip_url": zip_url,
        "repo_dir": repo_dir,
        "retention": {
            "mode": retention_mode,
            "ttl_days": int(retention_days_effective),
        },
    })
    return 0



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codemap-ai",
        description="CodeMap AI CLI (Phase-5): query explain.json"
    )

    sub = parser.add_subparsers(dest="command", required=True)

    p_explain = sub.add_parser("explain", help="Explain a symbol by fully-qualified name")
    p_explain.add_argument("fqn", help="Fully-qualified symbol name (e.g. testing_repo.test.Student.display)")
    p_explain.add_argument("--repo", default=None, help="Repository directory to read repo-scoped cached explain.json")
    p_explain.set_defaults(func=cmd_explain)

    p_search = sub.add_parser("search", help="Search symbols by substring")
    p_search.add_argument("query", help="Search keyword (case-insensitive)")
    p_search.add_argument("--repo", default=None, help="Repository directory to read repo-scoped cached explain.json")
    p_search.add_argument("--limit", type=int, default=30, help="Max results to show")
    p_search.set_defaults(func=cmd_search)

    p_list = sub.add_parser("list", help="List all symbols (optionally filter by module prefix)")
    p_list.add_argument("--module", default=None, help="Module prefix filter (e.g. testing_repo.test)")
    p_list.add_argument("--repo", default=None, help="Repository directory to read repo-scoped cached explain.json")
    p_list.add_argument("--limit", type=int, default=50, help="Max results to show")
    p_list.set_defaults(func=cmd_list)



    # -------------------------
    # API (JSON stdout) commands
    # -------------------------
    p_api = sub.add_parser("api", help="Machine-readable JSON API over explain.json")
    api_sub = p_api.add_subparsers(dest="api_command", required=True)

    p_api_help = api_sub.add_parser("help", help="Show API command help (JSON)")
    p_api_help.set_defaults(func=api_cache_help)

    p_api_explain = api_sub.add_parser("explain", help="Return JSON explanation for one symbol")
    p_api_explain.add_argument("fqn", help="Fully-qualified symbol name")
    p_api_explain.add_argument("--repo", default=None, help="Repository directory to read repo-scoped cached explain.json")
    p_api_explain.set_defaults(func=api_explain)

    p_api_search = api_sub.add_parser("search", help="Search symbols by substring (JSON)")
    p_api_search.add_argument("query", help="Search keyword")
    p_api_search.add_argument("--repo", default=None, help="Repository directory to read repo-scoped cached explain.json")
    p_api_search.add_argument("--limit", type=int, default=50)
    p_api_search.set_defaults(func=api_search)

    p_api_list = api_sub.add_parser("list", help="List all symbols (JSON)")
    p_api_list.add_argument("--module", default=None)
    p_api_list.add_argument("--repo", default=None, help="Repository directory to read repo-scoped cached explain.json")
    p_api_list.add_argument("--limit", type=int, default=200)
    p_api_list.set_defaults(func=api_list)

    p_api_status = api_sub.add_parser("status", help="Explain DB status (JSON)")
    p_api_status.add_argument("--repo", default=None, help="Repository directory to read repo-scoped cached explain.json")
    p_api_status.set_defaults(func=api_status)

    p_api_llm_explain = api_sub.add_parser("llm_explain", help="LLM-enhanced architecture explanation for one symbol")
    p_api_llm_explain.add_argument("fqn", help="Fully-qualified symbol name")
    p_api_llm_explain.add_argument("--repo", required=True, help="Repository directory to analyze")
    p_api_llm_explain.add_argument("--no-cache", action="store_true", help="Bypass read-cache for this request")
    p_api_llm_explain.add_argument("--mode", choices=["byok"], default="byok", help="AI mode selection")
    p_api_llm_explain.add_argument("--byok", action="store_true", help="Force BYOK mode")
    p_api_llm_explain.add_argument("--force", action="store_true", help="Force regenerate (bypass cache)")
    p_api_llm_explain.set_defaults(func=api_llm_explain)

    p_api_repo_summary = api_sub.add_parser("repo_summary", help="LLM repo-level architectural summary")
    p_api_repo_summary.add_argument("--repo", required=True, help="Repository directory to summarize")
    p_api_repo_summary.add_argument("--mode", choices=["byok"], default="byok", help="AI mode selection")
    p_api_repo_summary.add_argument("--byok", action="store_true", help="Force BYOK mode")
    p_api_repo_summary.add_argument("--force", action="store_true", help="Force regenerate (bypass cache)")
    p_api_repo_summary.set_defaults(func=api_repo_summary)

    p_api_risk_radar = api_sub.add_parser("risk_radar", help="Repo-level risk radar from cached architecture artifacts")
    p_api_risk_radar.add_argument("--repo", required=True, help="Repository directory")
    p_api_risk_radar.set_defaults(func=api_risk_radar)

    p_api_impact = api_sub.add_parser("impact", help="Change impact preview for symbol or file target")
    p_api_impact.add_argument("target", help="Symbol FQN or repo-relative file path")
    p_api_impact.add_argument("--repo", required=True, help="Repository directory")
    p_api_impact.add_argument("--depth", type=int, default=2, help="Traversal depth")
    p_api_impact.add_argument("--max_nodes", type=int, default=200, help="Node cap per direction")
    p_api_impact.set_defaults(func=api_impact)

    p_api_cache = api_sub.add_parser("cache", help="Manage analysis caches")
    cache_sub = p_api_cache.add_subparsers(dest="cache_command", required=True)

    p_api_cache_list = cache_sub.add_parser("list", help="List cache directories")
    p_api_cache_list.set_defaults(func=api_cache_list)

    p_api_cache_policy = cache_sub.add_parser("policy", help="Get or set cache retention policy")
    cache_policy_sub = p_api_cache_policy.add_subparsers(dest="cache_policy_command", required=True)
    p_api_cache_policy_get = cache_policy_sub.add_parser("get", help="Show retention policy")
    p_api_cache_policy_get.set_defaults(func=api_cache_policy_get)
    p_api_cache_policy_set = cache_policy_sub.add_parser("set", help="Update retention policy")
    p_api_cache_policy_set.add_argument("--default-ttl-days", type=int, default=None, help="Default TTL for repo cache dirs")
    p_api_cache_policy_set.add_argument("--workspaces-ttl-days", type=int, default=None, help="Default TTL for unreferenced workspaces")
    p_api_cache_policy_set.set_defaults(func=api_cache_policy_set)

    p_api_cache_info = cache_sub.add_parser("info", help="Inspect one cache target")
    p_api_cache_info.add_argument("--path", default=None, help="Local repository path")
    p_api_cache_info.add_argument("--github", default=None, help="GitHub repository URL")
    p_api_cache_info.add_argument("--ref", default=None, help="GitHub ref")
    p_api_cache_info.add_argument("--mode", default="git", choices=["git", "zip"], help="GitHub mode")
    p_api_cache_info.set_defaults(func=api_cache_info)

    p_api_cache_clear = cache_sub.add_parser("clear", help="Clear one cache target safely")
    p_api_cache_clear.add_argument("--all", action="store_true", help="Clear every known cache")
    p_api_cache_clear.add_argument("--repo_hash", "--repo-hash", default=None, help="Direct repo hash target")
    p_api_cache_clear.add_argument("--path", default=None, help="Local repository path")
    p_api_cache_clear.add_argument("--github", default=None, help="GitHub repository URL")
    p_api_cache_clear.add_argument("--ref", default=None, help="GitHub ref")
    p_api_cache_clear.add_argument("--mode", default="git", choices=["git", "zip"], help="GitHub mode")
    p_api_cache_clear.add_argument("--dry-run", action="store_true", help="Show what would be deleted")
    p_api_cache_clear.add_argument("--yes", action="store_true", help="Skip confirmation prompt")
    p_api_cache_clear.add_argument("--include-workspace", action="store_true", help="Also remove workspace even if shared")
    p_api_cache_clear.set_defaults(func=api_cache_clear)

    p_api_cache_retention = cache_sub.add_parser("retention", help="Set per-repo retention in days")
    p_api_cache_retention.add_argument("--repo_hash", "--repo-hash", default=None, help="Direct repo hash target")
    p_api_cache_retention.add_argument("--path", default=None, help="Local repository path")
    p_api_cache_retention.add_argument("--github", default=None, help="GitHub repository URL")
    p_api_cache_retention.add_argument("--ref", default=None, help="GitHub ref")
    p_api_cache_retention.add_argument("--mode", default="git", choices=["git", "zip"], help="GitHub mode")
    p_api_cache_retention.add_argument("--days", type=int, required=True, help="Retention days (0 means never auto-delete)")
    p_api_cache_retention.add_argument("--yes", action="store_true", help="Confirm retention update")
    p_api_cache_retention.set_defaults(func=api_cache_retention)

    p_api_cache_cleanup = cache_sub.add_parser("cleanup", help="Delete expired cache/workspace data using retention policy")
    p_api_cache_cleanup.add_argument("--apply", action="store_true", help="Apply cleanup immediately (alias for --yes)")
    p_api_cache_cleanup.add_argument("--dry-run", action="store_true", help="Show what would be deleted")
    p_api_cache_cleanup.add_argument("--yes", action="store_true", help="Skip confirmation prompt")
    p_api_cache_cleanup.set_defaults(func=api_cache_cleanup)

    p_api_cache_sweep = cache_sub.add_parser("sweep", help="Sweep expired caches by per-repo retention metadata")
    p_api_cache_sweep.add_argument("--dry-run", action="store_true", help="Show what would be deleted")
    p_api_cache_sweep.add_argument("--yes", action="store_true", help="Confirm deletion")
    p_api_cache_sweep.set_defaults(func=api_cache_sweep)

    p_api_cache_delete = cache_sub.add_parser("delete", help="Delete all artifacts for one repo cache target")
    p_api_cache_delete.add_argument("--repo_hash", "--repo-hash", default=None, help="Direct repo hash target")
    p_api_cache_delete.add_argument("--path", default=None, help="Local repository path")
    p_api_cache_delete.add_argument("--github", default=None, help="GitHub repository URL")
    p_api_cache_delete.add_argument("--ref", default=None, help="GitHub ref")
    p_api_cache_delete.add_argument("--mode", default="git", choices=["git", "zip"], help="GitHub mode")
    p_api_cache_delete.add_argument("--dry-run", action="store_true", help="Show what would be deleted")
    p_api_cache_delete.add_argument("--yes", action="store_true", help="Skip confirmation prompt")
    p_api_cache_delete.set_defaults(func=api_cache_delete)

    p_api_cache_prune = cache_sub.add_parser("prune", help="Prune stale caches by retention policy")
    p_api_cache_prune.add_argument("--older-than", default="0d", help="Additional age filter (e.g. 14d, 36h)")
    p_api_cache_prune.add_argument("--dry-run", action="store_true", help="Show what would be deleted")
    p_api_cache_prune.add_argument("--yes", action="store_true", help="Skip confirmation prompt")
    p_api_cache_prune.set_defaults(func=api_cache_prune)

    p_api_analyze = api_sub.add_parser("analyze", help="Run Phase-4 and explain generation")
    p_api_analyze.add_argument("--path", default=None, help="Repository directory to analyze")
    p_api_analyze.add_argument("--github", default=None, help="Public GitHub repository URL (https://github.com/<org>/<repo>)")
    p_api_analyze.add_argument("--ref", default=None, help="Optional Git branch or tag when using --github")
    p_api_analyze.add_argument("--mode", default="git", choices=["git", "zip"], help="GitHub fetch mode")
    p_api_analyze.add_argument("--token", default=None, help="GitHub personal access token (optional)")
    p_api_analyze.add_argument("--token-stdin", action="store_true", help="Read GitHub token from stdin")
    p_api_analyze.add_argument("--refresh", action="store_true", help="GitHub only: delete workspace clone and fetch again")
    p_api_analyze.add_argument("--rebuild", action="store_true", help="Force full analysis rebuild even if cache is valid")
    p_api_analyze.add_argument("--clear-cache", action="store_true", help="Delete analysis cache directory before analyze")
    p_api_analyze.add_argument("--retention", default="ttl", choices=["ttl", "session_only", "pinned"], help="Retention policy mode")
    p_api_analyze.add_argument("--ttl-days", type=int, default=None, help="TTL in days when retention mode is ttl (0 = never)")
    p_api_analyze.set_defaults(func=api_analyze)


    return parser
def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
