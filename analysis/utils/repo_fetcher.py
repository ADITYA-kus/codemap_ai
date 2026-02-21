from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from typing import Any, Dict, Optional
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from security_utils import redact_secrets

_ALLOWED_HOSTS = {"github.com", "www.github.com"}
_RE_SAFE = re.compile(r"^[A-Za-z0-9._-]+$")
_MAX_FILE_SIZE = 20 * 1024 * 1024
_MAX_FILES = 30000


def _project_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def safe_workspace_root() -> str:
    root = os.path.join(_project_root(), ".codemap_cache", "workspaces")
    os.makedirs(root, exist_ok=True)
    return root


def parse_github_url(url: str) -> Dict[str, str]:
    raw = str(url or "").strip()
    if not raw:
        raise ValueError("GitHub URL is required")
    parsed = urllib_parse.urlparse(raw)
    if parsed.scheme.lower() != "https":
        raise ValueError("Only https://github.com URLs are supported")
    host = parsed.netloc.lower().strip()
    if host not in _ALLOWED_HOSTS:
        raise ValueError("Only github.com is supported")

    path = parsed.path.strip().strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    parts = [p for p in path.split("/") if p]
    if len(parts) < 2:
        raise ValueError("GitHub URL must look like https://github.com/<owner>/<repo>")
    owner, repo = parts[0], parts[1]
    if not _RE_SAFE.match(owner) or not _RE_SAFE.match(repo):
        raise ValueError("Owner/repo contains unsupported characters")
    return {"host": host, "owner": owner, "repo": repo}


def normalize_github_url(url: str) -> str:
    parsed = parse_github_url(url)
    return f"https://github.com/{parsed['owner']}/{parsed['repo']}"


def _workspace_id(normalized_url: str, ref: Optional[str], mode: str) -> str:
    key = f"{normalized_url}|{str(ref or '').strip()}|{mode}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def resolve_workspace_paths(url: str, ref: Optional[str], mode: str = "git") -> Dict[str, str]:
    normalized = normalize_github_url(url)
    info = parse_github_url(url)
    workspace_id = _workspace_id(normalized, ref, mode)
    ws_root = safe_workspace_root()
    workspace_dir = os.path.join(ws_root, workspace_id)
    repo_dir = os.path.join(workspace_dir, info["repo"])

    ws_real = os.path.realpath(workspace_dir)
    root_real = os.path.realpath(ws_root)
    try:
        if os.path.commonpath([root_real, ws_real]) != root_real:
            raise ValueError("Unsafe workspace path")
    except ValueError as e:
        raise ValueError(str(e))

    return {
        "normalized_url": normalized,
        "workspace_id": workspace_id,
        "workspace_dir": workspace_dir,
        "repo_dir": repo_dir,
        "repo_name": info["repo"],
        "owner": info["owner"],
    }


def _safe_rmtree(path: str, allowed_root: str) -> bool:
    if not path or not os.path.exists(path):
        return False
    real_target = os.path.realpath(path)
    real_root = os.path.realpath(allowed_root)
    try:
        if os.path.commonpath([real_root, real_target]) != real_root:
            return False
    except ValueError:
        return False

    def _onerror(func, p, _exc):
        try:
            os.chmod(p, 0o700)
        except OSError:
            pass
        try:
            func(p)
        except Exception:
            pass

    shutil.rmtree(real_target, onerror=_onerror)
    return True


def _git_branch(repo_dir: str) -> Optional[str]:
    try:
        proc = subprocess.run(
            ["git", "-C", repo_dir, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        branch = str(proc.stdout or "").strip()
        return branch or None
    except Exception:
        return None


def _git_available() -> bool:
    try:
        subprocess.run(["git", "--version"], capture_output=True, text=True, timeout=10, check=False)
        return True
    except Exception:
        return False


def fetch_public_repo(
    url: str,
    ref: Optional[str] = None,
    refresh: bool = False,
    token: Optional[str] = None,
    auth: str = "none",
) -> Dict[str, Any]:
    try:
        resolved = resolve_workspace_paths(url, ref, mode="git")
    except Exception as e:
        return {"ok": False, "error": str(e), "error_code": "INVALID_GITHUB_URL", "auth": auth, "mode": "git"}

    ws_root = safe_workspace_root()
    workspace_dir = resolved["workspace_dir"]
    repo_dir = resolved["repo_dir"]
    normalized_url = resolved["normalized_url"]

    if refresh:
        _safe_rmtree(workspace_dir, ws_root)

    os.makedirs(workspace_dir, exist_ok=True)

    if os.path.isdir(repo_dir) and os.path.exists(os.path.join(repo_dir, ".git")):
        return {
            "ok": True,
            "workspace_dir": workspace_dir,
            "repo_dir": repo_dir,
            "normalized_url": normalized_url,
            "ref": ref or _git_branch(repo_dir),
            "fetched": False,
            "refreshed": bool(refresh),
            "mode": "git",
            "auth": auth,
            "error": None,
        }

    if not _git_available():
        return {
            "ok": False,
            "workspace_dir": workspace_dir,
            "repo_dir": repo_dir,
            "normalized_url": normalized_url,
            "ref": ref,
            "fetched": False,
            "refreshed": bool(refresh),
            "mode": "git",
            "auth": auth,
            "error": "git not found",
            "error_code": "GIT_NOT_FOUND",
        }

    remote = f"{normalized_url}.git"
    cmd = ["git"]
    if token:
        cmd += ["-c", f"http.extraheader=AUTHORIZATION: bearer {token}"]
    cmd += ["clone", "--depth", "1", "--no-tags", "--single-branch"]
    if ref:
        cmd += ["--branch", str(ref)]
    cmd += [remote, repo_dir]

    try:
        proc = subprocess.run(
            cmd,
            cwd=workspace_dir,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "workspace_dir": workspace_dir,
            "repo_dir": repo_dir,
            "normalized_url": normalized_url,
            "ref": ref,
            "fetched": False,
            "refreshed": bool(refresh),
            "mode": "git",
            "auth": auth,
            "error": "Git clone timed out",
            "error_code": "GITHUB_FETCH_FAILED",
        }

    stderr = redact_secrets(str(proc.stderr or ""), extra_secrets=[token] if token else None)
    if proc.returncode != 0:
        msg = stderr.strip() or "Git clone failed"
        code = "GITHUB_FETCH_FAILED"
        if ("404" in msg or "401" in msg or "403" in msg) and not token:
            code = "GITHUB_AUTH_REQUIRED"
            msg = "Repo may be private. Provide --token or set GITHUB_TOKEN."
        return {
            "ok": False,
            "workspace_dir": workspace_dir,
            "repo_dir": repo_dir,
            "normalized_url": normalized_url,
            "ref": ref,
            "fetched": False,
            "refreshed": bool(refresh),
            "mode": "git",
            "auth": auth,
            "error": msg,
            "error_code": code,
        }

    return {
        "ok": True,
        "workspace_dir": workspace_dir,
        "repo_dir": repo_dir,
        "normalized_url": normalized_url,
        "ref": ref or _git_branch(repo_dir),
        "fetched": True,
        "refreshed": bool(refresh),
        "mode": "git",
        "auth": auth,
        "error": None,
    }


def _download_zip(url: str, token: Optional[str]) -> bytes:
    headers = {"User-Agent": "codemap-ai"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib_request.Request(url, headers=headers, method="GET")
    with urllib_request.urlopen(req, timeout=90) as resp:
        return resp.read()


def _safe_extract_zip(zip_path: str, workspace_dir: str) -> str:
    with zipfile.ZipFile(zip_path, "r") as zf:
        members = zf.infolist()
        if len(members) > _MAX_FILES:
            raise RuntimeError("Archive has too many files")

        extracted_top: Optional[str] = None
        count = 0
        for info in members:
            count += 1
            if info.is_dir():
                continue
            if info.file_size > _MAX_FILE_SIZE:
                raise RuntimeError("Archive contains oversized file")
            target = os.path.realpath(os.path.join(workspace_dir, info.filename))
            ws_real = os.path.realpath(workspace_dir)
            try:
                if os.path.commonpath([ws_real, target]) != ws_real:
                    raise RuntimeError("Unsafe zip entry path")
            except ValueError:
                raise RuntimeError("Unsafe zip entry path")
            zf.extract(info, workspace_dir)
            if extracted_top is None:
                parts = info.filename.replace("\\", "/").split("/")
                if parts:
                    extracted_top = parts[0]

        if count > _MAX_FILES:
            raise RuntimeError("Archive has too many files")

    if extracted_top:
        top_dir = os.path.join(workspace_dir, extracted_top)
        if os.path.isdir(top_dir):
            return top_dir

    dirs = [d for d in os.listdir(workspace_dir) if os.path.isdir(os.path.join(workspace_dir, d))]
    if len(dirs) == 1:
        return os.path.join(workspace_dir, dirs[0])
    return workspace_dir


def fetch_public_repo_zip(
    url: str,
    ref: Optional[str],
    refresh: bool = False,
    token: Optional[str] = None,
    auth: str = "none",
) -> Dict[str, Any]:
    ref_value = str(ref or "").strip() or "main"
    try:
        resolved = resolve_workspace_paths(url, ref_value, mode="zip")
    except Exception as e:
        return {"ok": False, "error": str(e), "error_code": "INVALID_GITHUB_URL", "auth": auth, "mode": "zip"}

    ws_root = safe_workspace_root()
    workspace_dir = resolved["workspace_dir"]
    repo_dir = resolved["repo_dir"]
    normalized_url = resolved["normalized_url"]

    if refresh:
        _safe_rmtree(workspace_dir, ws_root)

    os.makedirs(workspace_dir, exist_ok=True)

    if os.path.isdir(repo_dir):
        return {
            "ok": True,
            "workspace_dir": workspace_dir,
            "repo_dir": repo_dir,
            "normalized_url": normalized_url,
            "ref": ref_value,
            "downloaded": False,
            "zip_url": "",
            "fetched": False,
            "refreshed": bool(refresh),
            "mode": "zip",
            "auth": auth,
            "error": None,
        }

    info = parse_github_url(url)
    base = f"https://github.com/{info['owner']}/{info['repo']}/archive/refs"
    urls = [
        f"{base}/heads/{urllib_parse.quote(ref_value)}.zip",
        f"{base}/tags/{urllib_parse.quote(ref_value)}.zip",
    ]

    zip_data: Optional[bytes] = None
    zip_url = ""
    last_error = ""

    for candidate in urls:
        try:
            zip_data = _download_zip(candidate, token=token)
            zip_url = candidate
            break
        except urllib_error.HTTPError as e:
            last_error = f"HTTP {getattr(e, 'code', '')}"
            if int(getattr(e, "code", 0) or 0) == 404:
                continue
            msg = redact_secrets(str(e), extra_secrets=[token] if token else None)
            if int(getattr(e, "code", 0) or 0) in {401, 403, 404} and not token:
                return {
                    "ok": False,
                    "workspace_dir": workspace_dir,
                    "repo_dir": repo_dir,
                    "normalized_url": normalized_url,
                    "ref": ref_value,
                    "downloaded": False,
                    "zip_url": candidate,
                    "fetched": False,
                    "refreshed": bool(refresh),
                    "mode": "zip",
                    "auth": auth,
                    "error": "Repo may be private. Provide --token or set GITHUB_TOKEN.",
                    "error_code": "GITHUB_AUTH_REQUIRED",
                }
            return {
                "ok": False,
                "workspace_dir": workspace_dir,
                "repo_dir": repo_dir,
                "normalized_url": normalized_url,
                "ref": ref_value,
                "downloaded": False,
                "zip_url": candidate,
                "fetched": False,
                "refreshed": bool(refresh),
                "mode": "zip",
                "auth": auth,
                "error": msg,
                "error_code": "GITHUB_FETCH_FAILED",
            }
        except Exception as e:
            last_error = redact_secrets(str(e), extra_secrets=[token] if token else None)
            continue

    if zip_data is None:
        return {
            "ok": False,
            "workspace_dir": workspace_dir,
            "repo_dir": repo_dir,
            "normalized_url": normalized_url,
            "ref": ref_value,
            "downloaded": False,
            "zip_url": zip_url,
            "fetched": False,
            "refreshed": bool(refresh),
            "mode": "zip",
            "auth": auth,
            "error": last_error or "Zip download failed",
            "error_code": "GITHUB_FETCH_FAILED",
        }

    fd, tmp_zip = tempfile.mkstemp(prefix="codemap_", suffix=".zip", dir=workspace_dir)
    os.close(fd)
    try:
        with open(tmp_zip, "wb") as f:
            f.write(zip_data)
        extracted = _safe_extract_zip(tmp_zip, workspace_dir)
        if os.path.isdir(repo_dir) and extracted != repo_dir:
            pass
        elif os.path.isdir(extracted) and extracted != repo_dir:
            if os.path.exists(repo_dir):
                _safe_rmtree(repo_dir, workspace_dir)
            os.replace(extracted, repo_dir)
    except Exception as e:
        return {
            "ok": False,
            "workspace_dir": workspace_dir,
            "repo_dir": repo_dir,
            "normalized_url": normalized_url,
            "ref": ref_value,
            "downloaded": False,
            "zip_url": zip_url,
            "fetched": False,
            "refreshed": bool(refresh),
            "mode": "zip",
            "auth": auth,
            "error": redact_secrets(str(e), extra_secrets=[token] if token else None),
            "error_code": "GITHUB_FETCH_FAILED",
        }
    finally:
        if os.path.exists(tmp_zip):
            try:
                os.remove(tmp_zip)
            except OSError:
                pass

    return {
        "ok": True,
        "workspace_dir": workspace_dir,
        "repo_dir": repo_dir,
        "normalized_url": normalized_url,
        "ref": ref_value,
        "downloaded": True,
        "zip_url": zip_url,
        "fetched": True,
        "refreshed": bool(refresh),
        "mode": "zip",
        "auth": auth,
        "error": None,
    }
