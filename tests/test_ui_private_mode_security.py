import os
import unittest


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class TestUiPrivateModeSecurity(unittest.TestCase):
    def test_token_field_is_password_and_private_mode_text_exists(self):
        template_path = os.path.join(PROJECT_ROOT, "ui", "templates", "index.html")
        with open(template_path, "r", encoding="utf-8") as f:
            html = f.read()
        self.assertIn('id="gh-token"', html)
        self.assertIn('type="password"', html)
        self.assertIn("Private Repo Mode", html)
        self.assertIn("Tokens are used only in memory", html)

    def test_token_is_cleared_and_errors_use_redaction(self):
        js_path = os.path.join(PROJECT_ROOT, "ui", "static", "app.js")
        with open(js_path, "r", encoding="utf-8") as f:
            js = f.read()
        self.assertIn("function updatePrivateModeIndicator()", js)
        self.assertGreaterEqual(js.count("ghTokenEl.value = \"\";"), 2)
        self.assertIn("showToast(redactSecrets(", js)
        self.assertIn("repoModalErrorEl.textContent = redactSecrets(", js)

    def test_byok_env_mode_indicator_exists(self):
        template_path = os.path.join(PROJECT_ROOT, "ui", "templates", "index.html")
        with open(template_path, "r", encoding="utf-8") as f:
            html = f.read()
        self.assertIn('id="ai-mode-badge"', html)
        self.assertIn('id="ai-settings-btn"', html)
        self.assertIn('id="ai-settings-modal"', html)
        self.assertIn('id="ai-settings-provider"', html)
        self.assertIn('id="ai-settings-key"', html)
        self.assertIn("AI: OFF", html)
        self.assertNotIn("Hosted AI", html)

    def test_byok_uses_local_settings_and_cached_summary_endpoints(self):
        js_path = os.path.join(PROJECT_ROOT, "ui", "static", "app.js")
        with open(js_path, "r", encoding="utf-8") as f:
            js = f.read()
        self.assertIn('fetchJson("/api/settings/ai")', js)
        self.assertIn('fetchJson("/api/settings/ai/test"', js)
        self.assertIn('fetchJson(`/api/repo_summary?repo=', js)
        self.assertIn('fetchJson(`/api/repo_summary/generate?force=', js)
        self.assertIn('fetchJson(`/api/ai/${action}`', js)
        self.assertIn("AI summary is disabled. Open Settings -> AI to enable (optional).", js)
        self.assertNotIn("callByokProxy(", js)
        self.assertNotIn("/api/hosted/", js)


if __name__ == "__main__":
    unittest.main()
