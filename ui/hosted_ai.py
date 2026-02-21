from __future__ import annotations

import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib import error, request

from analysis.utils.cache_manager import compute_analysis_fingerprint, compute_repo_hash, get_cache_dir
from security_utils import redact_secrets
from ui import hosted_ai_store


PROMPT_VERSION = "hosted-v1"
MAX_SNIPPET_LINES = 80
DB_DIR_NAME = "hosted_ai"
DB_FILE_NAME = "hosted_ai.sqlite"

_EXTRA_SECRET_PATTERNS = [
    re.compile(r"\bAIza[0-9A-Za-z\-_]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9\-_]{16,}\b"),
    re.compile(r"\bgsk_[A-Za-z0-9\-_]{16,}\b"),
    re.compile(r"\bxai-[A-Za-z0-9\-_]{16,}\b"),
]


def _now_ts() -> float:
    return float(time.time())


def _utc_day(now_ts: Optional[float] = None) -> str:
    return datetime.fromtimestamp(now_ts or _now_ts(), timezone.utc).strftime("%Y-%m-%d")


def _load_json(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _redact_value(text: str) -> str:
    value = redact_secrets(str(text or ""))
    for pattern in _EXTRA_SECRET_PATTERNS:
        value = pattern.sub("[REDACTED_SECRET]", value)
    return value


def _redact_payload(payload: Any) -> Any:
    if isinstance(payload, str):
        return _redact_value(payload)
    if isinstance(payload, list):
        return [_redact_payload(x) for x in payload]
    if isinstance(payload, dict):
        return {k: _redact_payload(v) for k, v in payload.items()}
    return payload


def _short_label(fqn: str) -> str:
    parts = str(fqn or "").split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return str(fqn or "")


def _snippet(file_path: str, start_line: int, end_line: int) -> str:
    if not file_path or not os.path.exists(file_path):
        return ""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return ""
    total = len(lines)
    start = max(1, int(start_line) - 20)
    end = min(total, int(end_line) + 20)
    if end < start:
        end = start
    selected = lines[start - 1:end]
    if len(selected) > MAX_SNIPPET_LINES:
        selected = selected[:MAX_SNIPPET_LINES]
    return "".join(selected)


def _build_symbol_context(repo_dir: str, fqn: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    cache_dir = get_cache_dir(repo_dir)
    explain_path = os.path.join(cache_dir, "explain.json")
    calls_path = os.path.join(cache_dir, "resolved_calls.json")
    explain = _load_json(explain_path, {})
    calls = _load_json(calls_path, [])
    if not isinstance(explain, dict) or not isinstance(calls, list):
        return None, "MISSING_ANALYSIS"
    symbol = explain.get(fqn)
    if not isinstance(symbol, dict):
        return None, "NOT_FOUND"

    loc = symbol.get("location", {}) if isinstance(symbol.get("location"), dict) else {}
    file_path = str(loc.get("file", "") or "")
    start_line = int(loc.get("start_line", 1) or 1)
    end_line = int(loc.get("end_line", start_line) or start_line)
    callers = sorted({str(c.get("caller_fqn")) for c in calls if c.get("callee_fqn") == fqn and c.get("caller_fqn")})
    callees = sorted({str(c.get("callee_fqn")) for c in calls if c.get("caller_fqn") == fqn and c.get("callee_fqn")})
    ctx = {
        "type": "symbol",
        "fqn": fqn,
        "summary_hint": str(symbol.get("one_liner", "") or ""),
        "details": [str(x) for x in (symbol.get("details") or [])][:6],
        "location": {"file": file_path, "start_line": start_line, "end_line": end_line},
        "snippet": _snippet(file_path, start_line, end_line),
        "callers_1hop": callers[:25],
        "callees_1hop": callees[:25],
    }
    return _redact_payload(ctx), None


def _build_repo_context(repo_dir: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    cache_dir = get_cache_dir(repo_dir)
    arch_path = os.path.join(cache_dir, "architecture_metrics.json")
    dep_path = os.path.join(cache_dir, "dependency_cycles.json")
    analysis_path = os.path.join(cache_dir, "analysis_metrics.json")
    if not os.path.exists(arch_path) or not os.path.exists(dep_path):
        return None, "MISSING_ANALYSIS"

    arch = _load_json(arch_path, {})
    dep = _load_json(dep_path, {})
    analysis = _load_json(analysis_path, {})
    repo = arch.get("repo", {}) if isinstance(arch.get("repo"), dict) else {}
    symbols = arch.get("symbols", {}) if isinstance(arch.get("symbols"), dict) else {}

    orchestrators = [str(x) for x in (repo.get("orchestrators") or [])][:5]
    critical = [str(x) for x in (repo.get("critical_symbols") or [])][:5]
    dead = [str(x) for x in (repo.get("dead_symbols") or [])][:5]
    cycles = dep.get("cycles") if isinstance(dep.get("cycles"), list) else []
    cycle_preview = [(" -> ".join([str(n) for n in c])) for c in cycles[:5] if isinstance(c, list)]

    def _shape(items: List[str]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for fqn in items:
            s = symbols.get(fqn, {}) if isinstance(symbols.get(fqn), dict) else {}
            loc = s.get("location", {}) if isinstance(s.get("location"), dict) else {}
            out.append(
                {
                    "fqn": fqn,
                    "label": _short_label(fqn),
                    "fan_in": int(s.get("fan_in", 0) or 0),
                    "fan_out": int(s.get("fan_out", 0) or 0),
                    "file": str(loc.get("file", "") or ""),
                    "line": int(loc.get("start_line", 1) or 1),
                }
            )
        return out

    ctx = {
        "type": "repo_summary",
        "repo_prefix": str(arch.get("repo_prefix", "") or ""),
        "counts": {
            "total_nodes": int(repo.get("total_nodes", 0) or 0),
            "total_files": int(analysis.get("total_files", 0) or 0),
            "total_calls": int(analysis.get("total_calls", 0) or 0),
            "unresolved_calls": int(analysis.get("unresolved_calls", 0) or 0),
            "dependency_cycles": int(dep.get("cycle_count", 0) or 0),
        },
        "orchestrators": _shape(orchestrators),
        "critical_apis": _shape(critical),
        "dead_symbols": _shape(dead),
        "cycle_preview": cycle_preview,
    }
    return _redact_payload(ctx), None


def _prompt_for_symbol(ctx: Dict[str, Any]) -> str:
    return (
        "Write plain text only (no markdown headings).\n"
        "Give 4-7 short bullet lines max, concise and developer-friendly.\n"
        "Cover: what this symbol does, key 1-hop connections, and one risk.\n"
        "Keep under 120 words.\n\n"
        f"Context JSON:\n{json.dumps(ctx, ensure_ascii=True)}"
    )


def _prompt_for_repo(ctx: Dict[str, Any]) -> str:
    return (
        "Write plain text only (no markdown headings).\n"
        "Give 4-7 short bullet lines max, concise and developer-friendly.\n"
        "Cover: code style (script/library), top orchestrators, critical APIs, cycles/hotspots, and one risk note.\n"
        "Keep under 140 words.\n\n"
        f"Context JSON:\n{json.dumps(ctx, ensure_ascii=True)}"
    )


def _normalize_summary(raw: str) -> str:
    text = _redact_value(raw)
    lines = [re.sub(r"^\s*[-*•]+\s*", "- ", ln.strip()) for ln in text.splitlines() if ln.strip()]
    if not lines:
        return "No summary generated."
    if len(lines) > 7:
        lines = lines[:7]
    return "\n".join(lines)


def _post_json(url: str, body: Dict[str, Any], headers: Dict[str, str], timeout: int = 45) -> Dict[str, Any]:
    req = request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _invoke_gemini(prompt: str) -> Tuple[str, str]:
    api_key = str(os.getenv("GEMINI_API_KEY", "") or "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY missing on hosted server")
    model = str(os.getenv("CODEMAP_GEMINI_MODEL", "gemini-2.5-flash-lite") or "gemini-2.5-flash-lite").strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.25, "maxOutputTokens": 220},
    }
    data = _post_json(url, body, {"Content-Type": "application/json"})
    candidates = data.get("candidates", [])
    if not candidates:
        raise RuntimeError("Gemini returned no candidates")
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(str(p.get("text", "")) for p in parts).strip()
    if not text:
        raise RuntimeError("Gemini returned empty content")
    return text, model


def _invoke_groq(prompt: str) -> Tuple[str, str]:
    api_key = str(os.getenv("GROQ_API_KEY", "") or "").strip()
    if not api_key:
        raise RuntimeError("GROQ_API_KEY missing on hosted server")
    model = str(os.getenv("CODEMAP_GROQ_MODEL", "llama-3.1-8b-instant") or "llama-3.1-8b-instant").strip()
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a concise software architecture assistant. Plain text only."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.25,
        "max_tokens": 220,
    }
    data = _post_json(
        "https://api.groq.com/openai/v1/chat/completions",
        body,
        {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
    )
    choices = data.get("choices", [])
    if not choices:
        raise RuntimeError("Groq returned no choices")
    text = str(choices[0].get("message", {}).get("content", "")).strip()
    if not text:
        raise RuntimeError("Groq returned empty content")
    return text, model


def _provider_order() -> List[str]:
    preferred = str(os.getenv("CODEMAP_HOSTED_PROVIDER", "gemini") or "gemini").strip().lower()
    if preferred == "groq":
        return ["groq", "gemini"]
    return ["gemini", "groq"]


def _context_hash(ctx: Dict[str, Any]) -> str:
    canonical = json.dumps(ctx, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _key_material(
    request_type: str,
    repo_hash: str,
    analysis_fingerprint: str,
    fqn: str,
    ctx_hash: str,
) -> str:
    raw = "|".join([
        PROMPT_VERSION,
        repo_hash,
        analysis_fingerprint,
        request_type,
        fqn or "",
        ctx_hash,
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _db_path(cache_root: str) -> str:
    return os.path.join(cache_root, DB_DIR_NAME, DB_FILE_NAME)


def _quota_settings() -> Tuple[int, int]:
    try:
        daily = int(str(os.getenv("CODEMAP_HOSTED_DAILY_QUOTA", "20") or "20"))
    except Exception:
        daily = 20
    try:
        min_interval = int(str(os.getenv("CODEMAP_HOSTED_MIN_INTERVAL_SEC", "5") or "5"))
    except Exception:
        min_interval = 5
    if daily < 1:
        daily = 1
    if min_interval < 0:
        min_interval = 0
    return daily, min_interval


def _remaining_quota(db_path: str, device_id: str, day: str, daily_quota: int) -> int:
    q = hosted_ai_store.get_quota_state(db_path, device_id, day)
    return max(0, daily_quota - int(q.get("count", 0)))


def _check_rate_quota(
    db_path: str,
    device_id: str,
    daily_quota: int,
    min_interval_sec: int,
) -> Tuple[bool, Optional[str], int]:
    day = _utc_day()
    now = _now_ts()
    q = hosted_ai_store.get_quota_state(db_path, device_id, day)
    count = int(q.get("count", 0))
    last_ts = float(q.get("last_ts", 0.0))
    remaining = max(0, daily_quota - count)
    if count >= daily_quota:
        return False, "QUOTA_EXCEEDED", remaining
    if min_interval_sec > 0 and last_ts > 0 and (now - last_ts) < float(min_interval_sec):
        return False, "RATE_LIMITED", remaining
    return True, None, remaining


def _invoke_provider(prompt: str) -> Tuple[str, str, str]:
    errors: List[str] = []
    for provider in _provider_order():
        try:
            if provider == "gemini":
                text, model = _invoke_gemini(prompt)
            else:
                text, model = _invoke_groq(prompt)
            return provider, model, text
        except error.HTTPError as e:
            errors.append(f"{provider} HTTP {e.code}")
        except Exception as e:
            errors.append(f"{provider} {str(e)}")
    raise RuntimeError("; ".join(errors) if errors else "Provider call failed")


def _build_request(
    request_type: str,
    repo_dir: str,
    fqn: Optional[str],
) -> Tuple[Optional[Dict[str, Any]], Optional[str], Optional[str], Optional[str]]:
    repo_dir_abs = os.path.abspath(repo_dir)
    repo_hash = compute_repo_hash(repo_dir_abs)
    if request_type == "symbol":
        ctx, err = _build_symbol_context(repo_dir_abs, str(fqn or ""))
        if err:
            return None, None, None, err
        prompt = _prompt_for_symbol(ctx or {})
        return ctx, prompt, repo_hash, None
    ctx, err = _build_repo_context(repo_dir_abs)
    if err:
        return None, None, None, err
    prompt = _prompt_for_repo(ctx or {})
    return ctx, prompt, repo_hash, None


def run_hosted_request(
    cache_root: str,
    repo_dir: str,
    device_id: str,
    request_type: str,
    fqn: Optional[str] = None,
    force: bool = False,
) -> Dict[str, Any]:
    db_path = _db_path(cache_root)
    hosted_ai_store.init_db(db_path)

    ctx, prompt, repo_hash, build_err = _build_request(request_type=request_type, repo_dir=repo_dir, fqn=fqn)
    if build_err == "MISSING_ANALYSIS":
        return {
            "ok": False,
            "summary": "",
            "provider": "",
            "cached": False,
            "remaining_quota": 0,
            "error": "MISSING_ANALYSIS",
            "message": "Run Analyze first: python cli.py api analyze --path <repo>",
        }
    if build_err == "NOT_FOUND":
        return {
            "ok": False,
            "summary": "",
            "provider": "",
            "cached": False,
            "remaining_quota": 0,
            "error": "NOT_FOUND",
            "message": f"Symbol not found: {fqn}",
        }
    if not ctx or not prompt or not repo_hash:
        return {
            "ok": False,
            "summary": "",
            "provider": "",
            "cached": False,
            "remaining_quota": 0,
            "error": "CONTEXT_BUILD_FAILED",
            "message": "Unable to build hosted AI context",
        }

    analysis_fp = compute_analysis_fingerprint(repo_dir)
    ctx_hash = _context_hash(ctx)
    cache_key = _key_material(
        request_type=request_type,
        repo_hash=repo_hash,
        analysis_fingerprint=analysis_fp,
        fqn=str(fqn or ""),
        ctx_hash=ctx_hash,
    )
    daily_quota, min_interval = _quota_settings()
    day = _utc_day()

    if not force:
        cached = hosted_ai_store.get_cached(db_path, cache_key)
        if cached:
            remaining = _remaining_quota(db_path, device_id, day, daily_quota)
            return {
                "ok": True,
                "summary": str(cached.get("summary_text", "") or ""),
                "provider": str(cached.get("provider", "") or ""),
                "model": str(cached.get("model", "") or ""),
                "cached": True,
                "remaining_quota": remaining,
                "error": None,
            }

    allowed, err_code, remaining = _check_rate_quota(
        db_path=db_path,
        device_id=device_id,
        daily_quota=daily_quota,
        min_interval_sec=min_interval,
    )
    if not allowed:
        return {
            "ok": False,
            "summary": "",
            "provider": "",
            "model": "",
            "cached": False,
            "remaining_quota": remaining,
            "error": err_code,
        }

    try:
        provider, model, raw = _invoke_provider(prompt)
        summary = _normalize_summary(raw)
    except Exception as e:
        return {
            "ok": False,
            "summary": "",
            "provider": "",
            "model": "",
            "cached": False,
            "remaining_quota": remaining,
            "error": _redact_value(str(e)),
        }

    hosted_ai_store.set_cached(
        db_path=db_path,
        key=cache_key,
        provider=provider,
        model=model,
        summary=summary,
        repo_hash=repo_hash,
        fqn=fqn,
        request_type=request_type,
    )
    quota_state = hosted_ai_store.increment_quota(
        db_path=db_path,
        device_id=device_id,
        day=day,
        now_ts=_now_ts(),
    )
    remaining_after = max(0, daily_quota - int(quota_state.get("count", 0)))
    return {
        "ok": True,
        "summary": summary,
        "provider": provider,
        "model": model,
        "cached": False,
        "remaining_quota": remaining_after,
        "error": None,
    }


def hosted_llm_explain(
    cache_root: str,
    repo_dir: str,
    fqn: str,
    device_id: str,
    force: bool = False,
) -> Dict[str, Any]:
    return run_hosted_request(
        cache_root=cache_root,
        repo_dir=repo_dir,
        device_id=device_id,
        request_type="symbol",
        fqn=fqn,
        force=force,
    )


def hosted_repo_summary(
    cache_root: str,
    repo_dir: str,
    device_id: str,
    force: bool = False,
) -> Dict[str, Any]:
    return run_hosted_request(
        cache_root=cache_root,
        repo_dir=repo_dir,
        device_id=device_id,
        request_type="repo_summary",
        fqn=None,
        force=force,
    )
