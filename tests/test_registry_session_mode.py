import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

from fastapi.testclient import TestClient

import ui.app as ui_app


class TestRegistrySessionMode(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(ui_app.app)
        self.temp_cache = tempfile.mkdtemp(prefix="codemap_registry_cache_")
        self.temp_repo = tempfile.mkdtemp(prefix="codemap_registry_repo_")
        ui_app._SESSION_WORKSPACE_READY = False
        ui_app._SESSION_WORKSPACE = {"active_repo_hash": "", "repos": []}

    def tearDown(self):
        shutil.rmtree(self.temp_repo, ignore_errors=True)
        shutil.rmtree(self.temp_cache, ignore_errors=True)
        ui_app._SESSION_WORKSPACE_READY = False
        ui_app._SESSION_WORKSPACE = {"active_repo_hash": "", "repos": []}

    def _registry_path(self) -> str:
        return os.path.join(self.temp_cache, "_registry.json")

    def _load_registry_file(self) -> dict:
        with open(self._registry_path(), "r", encoding="utf-8") as f:
            return json.load(f)

    def test_registry_created_default_session_mode(self):
        with mock.patch("ui.app.GLOBAL_CACHE_DIR", self.temp_cache):
            resp = self.client.get("/api/registry")
            self.assertEqual(resp.status_code, 200)
            payload = resp.json()
            self.assertTrue(payload.get("ok"))
            self.assertFalse(payload.get("remember_repos"))
            self.assertEqual(payload.get("repos"), [])
            self.assertTrue(os.path.exists(self._registry_path()))

    def test_add_repo_not_persisted_when_remember_disabled(self):
        with mock.patch("ui.app.GLOBAL_CACHE_DIR", self.temp_cache):
            self.client.post("/api/registry/settings", json={"remember_repos": False})
            add = self.client.post(
                "/api/registry/repos/add",
                json={"source": "filesystem", "repo_path": self.temp_repo, "display_name": "temp_repo"},
            )
            self.assertEqual(add.status_code, 200)
            self.assertFalse(add.json().get("persisted"))
            reg = self._load_registry_file()
            self.assertEqual(reg.get("repos"), [])
            repos_now = self.client.get("/api/repo_registry").json().get("repos", [])
            self.assertEqual(len(repos_now), 1)

            ui_app._SESSION_WORKSPACE_READY = False
            ui_app._SESSION_WORKSPACE = {"active_repo_hash": "", "repos": []}
            after_restart = self.client.get("/api/repo_registry").json().get("repos", [])
            self.assertEqual(after_restart, [])

    def test_add_repo_persisted_when_remember_enabled(self):
        with mock.patch("ui.app.GLOBAL_CACHE_DIR", self.temp_cache):
            self.client.post("/api/registry/settings", json={"remember_repos": True})
            add = self.client.post(
                "/api/registry/repos/add",
                json={"source": "filesystem", "repo_path": self.temp_repo, "display_name": "persisted_repo"},
            )
            self.assertEqual(add.status_code, 200)
            self.assertTrue(add.json().get("persisted"))
            reg = self._load_registry_file()
            self.assertEqual(len(reg.get("repos", [])), 1)

            ui_app._SESSION_WORKSPACE_READY = False
            ui_app._SESSION_WORKSPACE = {"active_repo_hash": "", "repos": []}
            after_restart = self.client.get("/api/repo_registry").json().get("repos", [])
            self.assertEqual(len(after_restart), 1)

    def test_clear_registry_list_keeps_cache_dirs(self):
        with mock.patch("ui.app.GLOBAL_CACHE_DIR", self.temp_cache):
            self.client.post("/api/registry/settings", json={"remember_repos": True})
            add = self.client.post(
                "/api/registry/repos/add",
                json={"source": "filesystem", "repo_path": self.temp_repo, "display_name": "clear_me"},
            )
            self.assertEqual(add.status_code, 200)
            repo_hash = str(add.json().get("repo_hash", "") or "")
            cache_dir = os.path.join(self.temp_cache, repo_hash)
            os.makedirs(cache_dir, exist_ok=True)

            clear = self.client.post("/api/registry/repos/clear", json={"session_only": False})
            self.assertEqual(clear.status_code, 200)
            reg = self._load_registry_file()
            self.assertEqual(reg.get("repos"), [])
            self.assertTrue(os.path.isdir(cache_dir))

    def test_repo_registry_does_not_enumerate_cache_dirs(self):
        with mock.patch("ui.app.GLOBAL_CACHE_DIR", self.temp_cache):
            os.makedirs(os.path.join(self.temp_cache, "deadbeefdeadbeef"), exist_ok=True)
            self.client.post("/api/registry/settings", json={"remember_repos": True})
            data = self.client.get("/api/repo_registry").json()
            self.assertTrue(data.get("ok"))
            self.assertEqual(data.get("repos"), [])


if __name__ == "__main__":
    unittest.main()
