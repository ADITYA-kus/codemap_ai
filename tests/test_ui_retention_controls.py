import os
import unittest


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class TestUiRetentionControls(unittest.TestCase):
    def test_template_contains_data_privacy_controls(self):
        path = os.path.join(PROJECT_ROOT, "ui", "templates", "index.html")
        with open(path, "r", encoding="utf-8") as f:
            html = f.read()
        self.assertIn('id="repo-retention-select"', html)
        self.assertIn('id="delete-repo-cache-btn"', html)
        self.assertIn('id="delete-all-caches-btn"', html)
        self.assertIn('id="cleanup-now-btn"', html)
        self.assertIn('id="privacy-confirm"', html)

    def test_ui_uses_cache_endpoints(self):
        js_path = os.path.join(PROJECT_ROOT, "ui", "static", "app.js")
        with open(js_path, "r", encoding="utf-8") as f:
            js = f.read()
        self.assertIn('"/api/cache/list"', js)
        self.assertIn('"/api/cache/retention"', js)
        self.assertIn('"/api/cache/clear"', js)
        self.assertIn('"/api/cache/sweep"', js)
        self.assertIn("showPrivacyConfirm(", js)

    def test_backend_exposes_cache_routes(self):
        py_path = os.path.join(PROJECT_ROOT, "ui", "app.py")
        with open(py_path, "r", encoding="utf-8") as f:
            py = f.read()
        self.assertIn('@app.get("/api/cache/list")', py)
        self.assertIn('@app.post("/api/cache/clear")', py)
        self.assertIn('@app.post("/api/cache/retention")', py)
        self.assertIn('@app.post("/api/cache/sweep")', py)


if __name__ == "__main__":
    unittest.main()
