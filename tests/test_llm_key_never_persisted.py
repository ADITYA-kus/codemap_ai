import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

from fastapi.testclient import TestClient

from analysis.utils.cache_manager import get_cache_dir
from ui.app import app


class TestLlmKeyNeverPersisted(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.repo_dir = tempfile.mkdtemp(prefix="codemap_repo_key_")
        self.settings_dir = tempfile.mkdtemp(prefix="codemap_settings_key_")
        self.settings_path = os.path.join(self.settings_dir, "ai_settings.json")
        self.secret = "sk_TEST_SHOULD_NOT_PERSIST_123"
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
        shutil.rmtree(self.settings_dir, ignore_errors=True)
        shutil.rmtree(self.cache_dir, ignore_errors=True)

    def _scan_for_secret(self, root: str) -> bool:
        if not os.path.exists(root):
            return False
        for base, _dirs, files in os.walk(root):
            for name in files:
                path = os.path.join(base, name)
                try:
                    with open(path, "rb") as f:
                        data = f.read()
                except Exception:
                    continue
                if self.secret.encode("utf-8") in data:
                    return True
        return False

    def test_byok_header_not_persisted_or_returned(self):
        with mock.patch("ui.app._ai_settings_path", return_value=self.settings_path):
            save = self.client.post(
                "/api/settings/ai",
                json={"provider": "gemini", "api_key": self.secret, "model": "", "save_local": True},
            )
            self.assertEqual(save.status_code, 200)
            self.assertTrue(os.path.exists(self.settings_path))
            with open(self.settings_path, "r", encoding="utf-8") as f:
                cfg_text = f.read()
            self.assertNotIn(self.secret, cfg_text)
            self.assertNotIn("api_key", cfg_text.lower())

            def _fake_cli_json_with_input(*args, **kwargs):
                env = kwargs.get("extra_env", {}) if isinstance(kwargs, dict) else {}
                self.assertEqual(env.get("GEMINI_API_KEY"), self.secret)
                return {
                    "ok": True,
                    "provider": "gemini",
                    "model": "gemini-2.5-flash-lite",
                    "cached": False,
                    "summary": "What it does: test.\nConnections: none\nNotes:",
                }

            with mock.patch("ui.app._cli_json_with_input", side_effect=_fake_cli_json_with_input):
                resp = self.client.post(
                    "/api/ai/llm_explain",
                    json={"repo": self.repo_dir, "symbol": "tmp.a.<module>", "regenerate": True, "force": True},
                    headers={"X-CodeMap-LLM-Key": self.secret},
                )
            self.assertEqual(resp.status_code, 200)
            body_text = resp.text
            self.assertNotIn(self.secret, body_text)

            registry_text = self.client.get("/api/registry").text
            self.assertNotIn(self.secret, registry_text)

            self.assertFalse(self._scan_for_secret(self.cache_dir))
            self.assertFalse(self._scan_for_secret(self.settings_dir))


if __name__ == "__main__":
    unittest.main()
