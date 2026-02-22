import json
import os
import shutil
import tempfile
import unittest

from fastapi.testclient import TestClient

from analysis.utils.cache_manager import get_cache_dir
from ui.app import app


class TestSymbolInfoEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.repo_dir = tempfile.mkdtemp(prefix="codemap_symbol_info_")
        self.file_path = os.path.join(self.repo_dir, "test.py")
        with open(self.file_path, "w", encoding="utf-8") as f:
            f.write(
                "class Student:\n"
                "    \"\"\"Student class.\"\"\"\n"
                "    def info(self):\n"
                "        return self.display()\n"
                "\n"
                "    def display(self):\n"
                "        \"\"\"Show display value.\"\"\"\n"
                "        print('x')\n"
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
                        "location": {"file": self.file_path, "start_line": 6, "end_line": 8},
                        "details": ["Signature: def display(self):"],
                    },
                    "testing_repo.test.Student.info": {
                        "location": {"file": self.file_path, "start_line": 3, "end_line": 4},
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
                        "line": 4,
                    },
                    {
                        "caller_fqn": self.symbol_fqn,
                        "callee_fqn": "builtins.print",
                        "file": self.file_path,
                        "line": 8,
                    },
                ],
                f,
            )

    def tearDown(self):
        shutil.rmtree(self.repo_dir, ignore_errors=True)
        shutil.rmtree(self.cache_dir, ignore_errors=True)

    def test_symbol_info_schema(self):
        resp = self.client.get(
            "/api/symbol/info",
            params={"repo": self.repo_dir, "symbol": self.symbol_fqn},
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body.get("ok"))
        symbol = body.get("symbol", {})
        self.assertEqual(symbol.get("qualified"), self.symbol_fqn)
        self.assertEqual(symbol.get("kind"), "method")
        self.assertEqual(symbol.get("line_start"), 6)
        self.assertEqual(symbol.get("line_end"), 8)
        self.assertIn("def display", str(symbol.get("signature", "")))
        self.assertIn("Show display value", str(symbol.get("docstring", "")))
        self.assertGreaterEqual(int(symbol.get("callers_count", 0)), 1)
        self.assertGreaterEqual(int(symbol.get("callees_count", 0)), 1)
        self.assertIsInstance(symbol.get("callers", []), list)
        self.assertIsInstance(symbol.get("callees", []), list)


if __name__ == "__main__":
    unittest.main()

