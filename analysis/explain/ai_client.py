from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Dict, Optional, Tuple
from urllib import error as urllib_error
from urllib import request as urllib_request

from security_utils import redact_secrets


DEFAULT_MODELS = {
    "gemini": "gemini-2.5-flash-lite",
    "groq": "llama-3.1-8b-instant",
    "xai": "grok-beta",
}


def _load_json(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path: str, payload: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _provider_key_env(provider: str) -> str:
    return {
        "gemini": "GEMINI_API_KEY",
        "groq": "GROQ_API_KEY",
        "xai": "XAI_API_KEY",
    }.get(provider, "")


def _select_provider() -> Tuple[str, str, str]:
    requested = str(os.getenv("CODEMAP_LLM", "") or "").strip().lower()
    allow_fallback = str(os.getenv("CODEMAP_ALLOW_FALLBACK", "1") or "1").strip() != "0"

    providers = [requested] if requested in {"gemini", "groq", "xai"} else ["gemini", "groq", "xai"]
    if allow_fallback and requested in {"gemini", "groq", "xai"}:
        providers += [p for p in ["gemini", "groq", "xai"] if p != requested]

    for provider in providers:
        env_name = _provider_key_env(provider)
        key = str(os.getenv(env_name, "") or "").strip()
        if key:
            model = str(os.getenv(f"CODEMAP_{provider.upper()}_MODEL", DEFAULT_MODELS[provider]) or DEFAULT_MODELS[provider]).strip()
            return provider, key, model

    return "", "", ""


def _post_json(url: str, payload: Dict[str, Any], headers: Dict[str, str], timeout: int = 45) -> Dict[str, Any]:
    req = urllib_request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib_request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _invoke_provider(prompt: str, provider: str, api_key: str, model: str) -> str:
    if provider == "gemini":
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 220},
        }
        data = _post_json(url, body, {"Content-Type": "application/json"})
        cands = data.get("candidates", []) if isinstance(data, dict) else []
        if not cands:
            raise RuntimeError("Gemini returned no candidates")
        parts = cands[0].get("content", {}).get("parts", [])
        text = "".join(str(p.get("text", "")) for p in parts).strip()
        if not text:
            raise RuntimeError("Gemini returned empty content")
        return text

    if provider == "groq":
        url = "https://api.groq.com/openai/v1/chat/completions"
        body = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 220,
        }
        data = _post_json(
            url,
            body,
            {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        )
        choices = data.get("choices", []) if isinstance(data, dict) else []
        if not choices:
            raise RuntimeError("Groq returned no choices")
        text = str(choices[0].get("message", {}).get("content", "") or "").strip()
        if not text:
            raise RuntimeError("Groq returned empty content")
        return text

    if provider == "xai":
        url = "https://api.x.ai/v1/chat/completions"
        body = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 220,
        }
        data = _post_json(
            url,
            body,
            {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        )
        choices = data.get("choices", []) if isinstance(data, dict) else []
        if not choices:
            raise RuntimeError("xAI returned no choices")
        text = str(choices[0].get("message", {}).get("content", "") or "").strip()
        if not text:
            raise RuntimeError("xAI returned empty content")
        return text

    raise RuntimeError("Unsupported provider")


def _clip_lines(text: str, max_lines: int = 6) -> str:
    lines = [ln.strip() for ln in str(text or "").splitlines() if ln.strip()]
    if not lines:
        return "No summary generated."
    out = []
    for ln in lines[:max_lines]:
        if ln.startswith("###"):
            ln = ln.lstrip("# ")
        if not ln.startswith("-"):
            ln = f"- {ln}"
        out.append(ln)
    return "\n".join(out)


def _repo_cache_dir(repo_dir: str) -> str:
    from analysis.utils.cache_manager import get_cache_dir

    return get_cache_dir(repo_dir)


def _llm_cache_path(repo_dir: str) -> str:
    return os.path.join(_repo_cache_dir(repo_dir), "llm_cache.json")


def _prompt_for_symbol(fqn: str, explain_entry: Dict[str, Any]) -> str:
    one = str(explain_entry.get("one_liner", "") or "")
    details = explain_entry.get("details", []) if isinstance(explain_entry.get("details"), list) else []
    detail_text = "\n".join(str(x) for x in details[:8])
    return (
        "Return plain concise developer bullets only (max 6 bullets, no markdown headings).\n"
        "Include: purpose, key dependencies (1-hop), and any side effect/risk.\n\n"
        f"Symbol: {fqn}\n"
        f"One-liner: {one}\n"
        f"Details:\n{detail_text}"
    )


def _cache_key(parts: Dict[str, Any]) -> str:
    blob = json.dumps(parts, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def llm_explain_symbol(fqn: str, repo_dir: str, no_cache: bool = False) -> Dict[str, Any]:
    cache_dir = _repo_cache_dir(repo_dir)
    explain_path = os.path.join(cache_dir, "explain.json")
    explain = _load_json(explain_path, {})
    if not isinstance(explain, dict) or fqn not in explain:
        return {"ok": False, "error": "SYMBOL_NOT_FOUND", "summary": "", "cached": False, "provider": ""}

    provider, api_key, model = _select_provider()
    if not provider or not api_key:
        return {"ok": False, "error": "AI_DISABLED", "summary": "", "cached": False, "provider": ""}

    manifest = _load_json(os.path.join(cache_dir, "manifest.json"), {})
    analysis_version = str((manifest or {}).get("analysis_version", "") or "")
    prompt = _prompt_for_symbol(fqn, explain[fqn] if isinstance(explain.get(fqn), dict) else {})

    key = _cache_key(
        {
            "type": "symbol",
            "fqn": fqn,
            "provider": provider,
            "model": model,
            "analysis_version": analysis_version,
            "prompt": prompt,
        }
    )

    cache_path = _llm_cache_path(repo_dir)
    cache = _load_json(cache_path, {})
    if not isinstance(cache, dict):
        cache = {}

    if not no_cache and key in cache and isinstance(cache.get(key), dict):
        row = cache[key]
        return {
            "ok": True,
            "cached": True,
            "provider": row.get("provider", provider),
            "model": row.get("model", model),
            "summary": str(row.get("summary", "") or ""),
            "error": None,
        }

    try:
        text = _invoke_provider(prompt=prompt, provider=provider, api_key=api_key, model=model)
    except urllib_error.HTTPError as e:
        return {"ok": False, "cached": False, "provider": provider, "summary": "", "error": redact_secrets(f"HTTP {getattr(e, 'code', '')}: {e}")}
    except Exception as e:
        return {"ok": False, "cached": False, "provider": provider, "summary": "", "error": redact_secrets(str(e))}

    summary = _clip_lines(text)
    cache[key] = {
        "provider": provider,
        "model": model,
        "summary": summary,
        "created_at": str(manifest.get("updated_at", "") or ""),
    }
    _save_json(cache_path, cache)

    return {
        "ok": True,
        "cached": False,
        "provider": provider,
        "model": model,
        "summary": summary,
        "error": None,
    }


def complete_text(prompt: str) -> Dict[str, Any]:
    provider, api_key, model = _select_provider()
    if not provider or not api_key:
        return {"ok": False, "provider": "", "model": "", "text": "", "error": "AI_DISABLED"}
    try:
        text = _invoke_provider(prompt=prompt, provider=provider, api_key=api_key, model=model)
    except Exception as e:
        return {"ok": False, "provider": provider, "model": model, "text": "", "error": redact_secrets(str(e))}
    return {"ok": True, "provider": provider, "model": model, "text": _clip_lines(text, max_lines=7), "error": None}
