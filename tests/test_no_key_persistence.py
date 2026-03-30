import json
import os
import shutil
import tempfile
import unittest
import uuid
from unittest import mock

from fastapi.testclient import TestClient

from analysis.utils.cache_manager import get_cache_dir
from ui.app import app


class TestNoKeyPersistence(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.repo_dir = tempfile.mkdtemp(prefix="codemap_key_persist_repo_")
        self.file_path = os.path.join(self.repo_dir, "test.py")
        with open(self.file_path, "w", encoding="utf-8") as f:
            f.write(
                "class Student:\n"
                "    def display(self):\n"
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
                        "location": {"file": self.file_path, "start_line": 2, "end_line": 3},
                    }
                },
                f,
            )
        with open(os.path.join(self.cache_dir, "resolved_calls.json"), "w", encoding="utf-8") as f:
            json.dump([], f)

    def tearDown(self):
        shutil.rmtree(self.repo_dir, ignore_errors=True)
        shutil.rmtree(self.cache_dir, ignore_errors=True)

    def _contains_secret(self, root: str, secret: str) -> bool:
        if not root or not os.path.exists(root):
            return False
        needle = secret.encode("utf-8")
        for base, _dirs, files in os.walk(root):
            for name in files:
                path = os.path.join(base, name)
                try:
                    with open(path, "rb") as f:
                        data = f.read()
                except Exception:
                    continue
                if needle in data:
                    return True
        return False

    @unittest.skip("AI features not yet implemented")
    def test_token_not_in_response_or_cache_files(self):
        secret = f"ghp_TESTTOKEN_{uuid.uuid4().hex}"

        def _fake_complete_text(prompt: str):
            self.assertIn(self.symbol_fqn, prompt)
            return {
                "ok": True,
                "provider": "gemini",
                "model": "gemini-2.5-flash-lite",
                "text": "Symbol explanation from fake llm.",
                "error": None,
            }

        with mock.patch.dict(
            os.environ,
            {"CODEMAP_LLM": "gemini", "GEMINI_API_KEY": secret},
            clear=False,
        ):
            with mock.patch("analysis.explain.ai_client.complete_text", side_effect=_fake_complete_text):
                resp = self.client.post(
                    "/api/symbol/explain",
                    json={"repo": self.repo_dir, "symbol": self.symbol_fqn, "force": True},
                )

        self.assertEqual(resp.status_code, 200)
        body_text = resp.text
        self.assertNotIn(secret, body_text)
        self.assertFalse(self._contains_secret(self.cache_dir, secret))
        self.assertFalse(self._contains_secret(self.repo_dir, secret))


if __name__ == "__main__":
    unittest.main()

