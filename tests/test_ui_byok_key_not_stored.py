import os
import unittest


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class TestUiByokKeyNotStored(unittest.TestCase):
    def test_ai_settings_key_input_is_password(self):
        path = os.path.join(PROJECT_ROOT, "ui", "templates", "index.html")
        with open(path, "r", encoding="utf-8") as f:
            html = f.read()
        self.assertIn('id="ai-settings-key"', html)
        self.assertIn('type="password"', html)

    def test_byok_uses_header_and_not_json_key_field(self):
        js_path = os.path.join(PROJECT_ROOT, "ui", "static", "app.js")
        with open(js_path, "r", encoding="utf-8") as f:
            js = f.read()
        self.assertIn("X-CodeMap-LLM-Key", js)
        self.assertNotIn("JSON.stringify({ provider, api_key", js)
        self.assertNotIn("JSON.stringify({ provider: \"none\", api_key", js)

    def test_no_key_storage_in_local_or_session_storage(self):
        js_path = os.path.join(PROJECT_ROOT, "ui", "static", "app.js")
        with open(js_path, "r", encoding="utf-8") as f:
            js = f.read()
        self.assertNotIn("localStorage.setItem(\"api_key", js)
        self.assertNotIn("localStorage.setItem(\"token", js)
        self.assertNotIn("sessionStorage.setItem(\"api_key", js)
        self.assertNotIn("sessionStorage.setItem(\"token", js)


if __name__ == "__main__":
    unittest.main()
