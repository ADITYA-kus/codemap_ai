import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

from fastapi.testclient import TestClient

from analysis.utils.cache_manager import get_cache_dir
from ui.app import app, _symbol_explain_v1_cache_path


class TestSymbolExplainCache(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.repo_dir = tempfile.mkdtemp(prefix="codemap_symbol_explain_")
        self.file_path = os.path.join(self.repo_dir, "test.py")
        with open(self.file_path, "w", encoding="utf-8") as f:
            f.write(
                "class Student:\n"
                "    def info(self):\n"
                "        return self.display()\n"
                "\n"
                "    def display(self):\n"
                "        \"\"\"Display value.\"\"\"\n"
                "        return 1\n"
            )

        self.symbol_fqn = "testing_repo.test.Student.display"
        self.cache_dir = get_cache_dir(self.repo_dir)
        os.makedirs(self.cache_dir, exist_ok=True)
        with open(os.path.join(self.cache_dir, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump({"analysis_version": "2.2"}, f)
        with open(os.path.join(self.cache_dir, "explain.json"), "w", encoding="utf-8") as f:
            json.dump(
                {
                    self.symbol_fqn: {
                        "location": {"file": self.file_path, "start_line": 5, "end_line": 7},
                    },
                    "testing_repo.test.Student.info": {
                        "location": {"file": self.file_path, "start_line": 2, "end_line": 3},
                    },
                },
                f,
            )
        with open(os.path.join(self.cache_dir, "resolved_calls.json"), "w", encoding="utf-8") as f:
            json.dump(
                [
                    {
                        "caller_fqn": "testing_repo.test.Student.info",
                        "callee_fqn": self.symbol_fqn,
                        "file": self.file_path,
                        "line": 3,
                    }
                ],
                f,
            )

    def tearDown(self):
        shutil.rmtree(self.repo_dir, ignore_errors=True)
        shutil.rmtree(self.cache_dir, ignore_errors=True)

    def _call_explain(self, force: bool):
        return self.client.post(
            "/api/symbol/explain",
            json={"repo": self.repo_dir, "symbol": self.symbol_fqn, "force": force},
        )

    def test_symbol_explain_cache_and_force(self):
        call_counter = {"count": 0}

        def _fake_complete_text(prompt: str):
            call_counter["count"] += 1
            self.assertIn(self.symbol_fqn, prompt)
            return {
                "ok": True,
                "provider": "gemini",
                "model": "gemini-2.5-flash-lite",
                "text": "It returns a display value.",
                "error": None,
            }

        with mock.patch.dict(os.environ, {"CODEMAP_LLM": "gemini", "GEMINI_API_KEY": "AIza_TEST_ONLY_123"}, clear=False):
            with mock.patch("analysis.explain.ai_client.complete_text", side_effect=_fake_complete_text):
                first = self._call_explain(force=False)
                self.assertEqual(first.status_code, 200)
                body_first = first.json()
                self.assertTrue(body_first.get("ok"))
                self.assertFalse(body_first.get("cached"))
                self.assertEqual(call_counter["count"], 1)

                second = self._call_explain(force=False)
                self.assertEqual(second.status_code, 200)
                body_second = second.json()
                self.assertTrue(body_second.get("ok"))
                self.assertTrue(body_second.get("cached"))
                self.assertEqual(call_counter["count"], 1)

                third = self._call_explain(force=True)
                self.assertEqual(third.status_code, 200)
                body_third = third.json()
                self.assertTrue(body_third.get("ok"))
                self.assertFalse(body_third.get("cached"))
                self.assertEqual(call_counter["count"], 2)

                cache_path = _symbol_explain_v1_cache_path(
                    self.cache_dir,
                    str(body_third.get("analysis_fingerprint", "")),
                    self.symbol_fqn,
                )
                self.assertTrue(os.path.exists(cache_path))


if __name__ == "__main__":
    unittest.main()

