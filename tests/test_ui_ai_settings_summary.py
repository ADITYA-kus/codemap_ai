import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

from fastapi.testclient import TestClient

from analysis.utils.cache_manager import get_cache_dir
from ui.app import (
    app,
    _repo_fingerprint,
    _repo_summary_cache_path,
    _symbol_summary_cache_path,
)


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class TestUiAiSettingsAndSummaryCache(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.repo_dir = tempfile.mkdtemp(prefix="codemap_repo_")
        with open(os.path.join(self.repo_dir, "a.py"), "w", encoding="utf-8") as f:
            f.write("print('x')\n")
        self.cache_dir = get_cache_dir(self.repo_dir)
        os.makedirs(self.cache_dir, exist_ok=True)
        with open(os.path.join(self.cache_dir, "explain.json"), "w", encoding="utf-8") as f:
            json.dump({"tmp.a.<module>": {"location": {"file": os.path.join(self.repo_dir, "a.py"), "start_line": 1, "end_line": 1}}}, f)
        with open(os.path.join(self.cache_dir, "resolved_calls.json"), "w", encoding="utf-8") as f:
            json.dump([], f)
        with open(os.path.join(self.cache_dir, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump({"analysis_version": "2.2"}, f)

    def tearDown(self):
        shutil.rmtree(self.repo_dir, ignore_errors=True)
        shutil.rmtree(self.cache_dir, ignore_errors=True)

    def test_repo_summary_stale_when_fingerprint_changes(self):
        fp = _repo_fingerprint(self.repo_dir, self.cache_dir)
        payload = {
            "repo_hash": "x",
            "analysis_version": "2.2",
            "fingerprint": fp,
            "provider": "gemini",
            "model": "",
            "generated_at": "2026-01-01T00:00:00Z",
            "content_markdown": "one",
        }
        summary_path = _repo_summary_cache_path(self.cache_dir)
        os.makedirs(os.path.dirname(summary_path), exist_ok=True)
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(payload, f)

        res_fresh = self.client.get("/api/repo_summary", params={"repo": self.repo_dir})
        self.assertEqual(res_fresh.status_code, 200)
        data_fresh = res_fresh.json()
        self.assertTrue(data_fresh.get("exists"))
        self.assertTrue(data_fresh.get("cached"))

        with open(os.path.join(self.cache_dir, "resolved_calls.json"), "w", encoding="utf-8") as f:
            json.dump([{"caller_fqn": "x", "callee_fqn": "y", "file": "a.py", "line": 1}], f)

        res_stale = self.client.get("/api/repo_summary", params={"repo": self.repo_dir})
        self.assertEqual(res_stale.status_code, 200)
        data_stale = res_stale.json()
        self.assertFalse(data_stale.get("exists"))
        self.assertEqual(data_stale.get("reason"), "STALE_OR_MISSING")
        self.assertTrue(data_stale.get("outdated"))

    def test_repo_summary_legacy_cli_cache_is_migrated_and_visible(self):
        legacy_path = os.path.join(self.cache_dir, "repo_summary.json")
        legacy_payload = {
            "ok": True,
            "repo": "tmp",
            "repo_hash": "legacy",
            "cached": False,
            "provider": "gemini",
            "summary": {
                "one_liner": "Legacy summary line.",
                "bullets": ["A", "B"],
                "notes": [],
            },
            "error": None,
        }
        with open(legacy_path, "w", encoding="utf-8") as f:
            json.dump(legacy_payload, f)

        res = self.client.get("/api/repo_summary", params={"repo": self.repo_dir})
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body.get("ok"))
        self.assertTrue(body.get("exists"))
        self.assertTrue(body.get("cached"))
        repo_summary = body.get("repo_summary", {})
        self.assertIn("Legacy summary line.", str(repo_summary.get("content_markdown", "")))
        self.assertTrue(os.path.exists(_repo_summary_cache_path(self.cache_dir)))

    def test_generate_uses_cache_on_second_call(self):
        self.client.post(
            "/api/settings/ai",
            json={"provider": "gemini", "api_key": "AIzaFakeToken123456", "model": "", "save_local": False},
        )

        call_counter = {"count": 0}

        def _fake_cli_json_with_input(*args, **kwargs):
            call_counter["count"] += 1
            return {
                "ok": True,
                "provider": "gemini",
                "cached": False,
                "summary": {"one_liner": "Repo purpose.", "bullets": ["A", "B"], "notes": []},
            }

        with mock.patch("ui.app._cli_json_with_input", side_effect=_fake_cli_json_with_input):
            first = self.client.post(
                "/api/repo_summary/generate?force=0",
                json={"repo": self.repo_dir},
                headers={"X-CodeMap-LLM-Key": "AIza_TEST_ONLY_123"},
            )
            self.assertEqual(first.status_code, 200)
            self.assertFalse(first.json().get("cached"))
            second = self.client.post(
                "/api/repo_summary/generate?force=0",
                json={"repo": self.repo_dir},
                headers={"X-CodeMap-LLM-Key": "AIza_TEST_ONLY_123"},
            )
            self.assertEqual(second.status_code, 200)
            self.assertTrue(second.json().get("cached"))
            self.assertEqual(call_counter["count"], 1)

    def test_symbol_cached_view_does_not_call_llm(self):
        symbol = "tmp.a.<module>"
        fp = _repo_fingerprint(self.repo_dir, self.cache_dir)
        symbol_payload = {
            "repo_hash": "x",
            "fqn": symbol,
            "analysis_version": "2.2",
            "fingerprint": fp,
            "provider": "gemini",
            "model": "gemini-2.5-flash-lite",
            "cached_at": "2026-01-01T00:00:00Z",
            "summary": "What it does: test.\nConnections: none\nNotes:",
        }
        symbol_path = _symbol_summary_cache_path(self.cache_dir, symbol)
        os.makedirs(os.path.dirname(symbol_path), exist_ok=True)
        with open(symbol_path, "w", encoding="utf-8") as f:
            json.dump(symbol_payload, f)

        with mock.patch("ui.app._cli_json_with_input", side_effect=AssertionError("LLM should not be called")):
            resp = self.client.post(
                "/api/ai/llm_explain",
                json={"repo": self.repo_dir, "symbol": symbol, "regenerate": False, "force": False},
            )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body.get("ok"))
        self.assertTrue(body.get("cached"))
        self.assertTrue(body.get("exists"))
        self.assertIn("What it does", body.get("explain_text", ""))

    def test_symbol_cached_view_reports_stale_without_regeneration(self):
        symbol = "tmp.a.<module>"
        symbol_payload = {
            "repo_hash": "x",
            "fqn": symbol,
            "analysis_version": "2.2",
            "fingerprint": "stale-fingerprint",
            "provider": "gemini",
            "model": "gemini-2.5-flash-lite",
            "cached_at": "2026-01-01T00:00:00Z",
            "summary": "What it does: stale.",
        }
        symbol_path = _symbol_summary_cache_path(self.cache_dir, symbol)
        os.makedirs(os.path.dirname(symbol_path), exist_ok=True)
        with open(symbol_path, "w", encoding="utf-8") as f:
            json.dump(symbol_payload, f)

        with mock.patch("ui.app._cli_json_with_input", side_effect=AssertionError("LLM should not be called")):
            resp = self.client.post(
                "/api/ai/llm_explain",
                json={"repo": self.repo_dir, "symbol": symbol, "regenerate": False, "force": False},
            )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body.get("ok"))
        self.assertFalse(body.get("exists"))
        self.assertTrue(body.get("stale"))
        self.assertIn("No cached summary", body.get("message", ""))

    def test_symbol_regenerate_writes_fingerprint_cache(self):
        symbol = "tmp.a.<module>"
        self.client.post(
            "/api/settings/ai",
            json={"provider": "gemini", "api_key": "AIzaFakeToken123456", "model": "", "save_local": False},
        )
        call_counter = {"count": 0}

        def _fake_cli_json_with_input(*args, **kwargs):
            call_counter["count"] += 1
            return {
                "ok": True,
                "provider": "gemini",
                "model": "gemini-2.5-flash-lite",
                "cached": False,
                "summary": "What it does: regenerated.\nConnections: none\nNotes:",
            }

        with mock.patch("ui.app._cli_json_with_input", side_effect=_fake_cli_json_with_input):
            resp = self.client.post(
                "/api/ai/llm_explain",
                json={"repo": self.repo_dir, "symbol": symbol, "regenerate": True, "force": True},
                headers={"X-CodeMap-LLM-Key": "AIza_TEST_ONLY_123"},
            )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(call_counter["count"], 1)
        symbol_path = _symbol_summary_cache_path(self.cache_dir, symbol)
        self.assertTrue(os.path.exists(symbol_path))
        with open(symbol_path, "r", encoding="utf-8") as f:
            cached = json.load(f)
        self.assertEqual(cached.get("fqn"), symbol)
        self.assertTrue(str(cached.get("fingerprint", "")))
        self.assertIn("What it does", str(cached.get("summary", "")))

    def test_settings_get_does_not_leak_api_key(self):
        temp_cfg_dir = tempfile.mkdtemp(prefix="codemap_cfg_")
        cfg_file = os.path.join(temp_cfg_dir, "secrets.json")
        key_value = "gsk_SENSITIVE_TEST_KEY_123456"
        try:
            with mock.patch("ui.app._ai_settings_path", return_value=cfg_file):
                save = self.client.post(
                    "/api/settings/ai",
                    json={"provider": "groq", "api_key": key_value, "model": "", "save_local": True},
                )
                self.assertEqual(save.status_code, 200)
                self.assertTrue(os.path.exists(cfg_file))
                with open(cfg_file, "r", encoding="utf-8") as f:
                    cfg_text = f.read()
                self.assertNotIn(key_value, cfg_text)
                self.assertNotIn("api_key", cfg_text.lower())
                get_resp = self.client.get("/api/settings/ai")
                self.assertEqual(get_resp.status_code, 200)
                body = get_resp.text
                self.assertNotIn(key_value, body)
                self.assertNotIn("api_key", body)
        finally:
            shutil.rmtree(temp_cfg_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
