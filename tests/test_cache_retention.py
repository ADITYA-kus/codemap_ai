import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from analysis.utils import cache_manager as cm


class TestCacheRetention(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.cache_root = os.path.join(self.tmp.name, ".codemap_cache")
        os.makedirs(self.cache_root, exist_ok=True)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _write_repo_cache(self, repo_hash: str, metadata: dict) -> str:
        cache_dir = os.path.join(self.cache_root, repo_hash)
        os.makedirs(cache_dir, exist_ok=True)
        with open(os.path.join(cache_dir, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        with open(os.path.join(cache_dir, "explain.json"), "w", encoding="utf-8") as f:
            f.write("{}")
        return cache_dir

    def test_sweep_expired_dry_run_then_delete(self):
        now = datetime.now(timezone.utc)
        old = (now - timedelta(days=20)).isoformat()
        repo_hash = "deadbeefdeadbeef"
        cache_dir = self._write_repo_cache(
            repo_hash,
            {
                "repo_hash": repo_hash,
                "source": "filesystem",
                "repo_path": "demo_repo",
                "created_at": old,
                "last_accessed_at": old,
                "retention_days": 7,
                "private_mode": False,
            },
        )

        dry = cm.sweep_expired(dry_run=True, base_dir=self.cache_root, now=now)
        self.assertTrue(dry["ok"])
        self.assertTrue(dry["dry_run"])
        self.assertIn(repo_hash, dry["caches_removed"])
        self.assertTrue(os.path.isdir(cache_dir))

        real = cm.sweep_expired(dry_run=False, base_dir=self.cache_root, now=now)
        self.assertTrue(real["ok"])
        self.assertFalse(real["dry_run"])
        self.assertIn(repo_hash, real["caches_removed"])
        self.assertFalse(os.path.exists(cache_dir))

    def test_workspace_ref_count_preserves_shared_workspace(self):
        ws_root = os.path.join(self.cache_root, "workspaces")
        shared_ws = os.path.join(ws_root, "shared123")
        repo_a_path = os.path.join(shared_ws, "repoA")
        repo_b_path = os.path.join(shared_ws, "repoB")
        os.makedirs(repo_a_path, exist_ok=True)
        os.makedirs(repo_b_path, exist_ok=True)

        ws_json = {
            "active_repo_hash": "hashA",
            "repos": [
                {"repo_hash": "hashA", "path": repo_a_path},
                {"repo_hash": "hashB", "path": repo_b_path},
            ],
        }
        with open(os.path.join(self.cache_root, "workspaces.json"), "w", encoding="utf-8") as f:
            json.dump(ws_json, f, indent=2)

        now = datetime.now(timezone.utc).isoformat()
        self._write_repo_cache(
            "hashA",
            {
                "repo_hash": "hashA",
                "source": "github",
                "repo_path": repo_a_path,
                "workspace_dir": shared_ws,
                "created_at": now,
                "last_accessed_at": now,
                "retention_days": 14,
                "private_mode": False,
            },
        )
        self._write_repo_cache(
            "hashB",
            {
                "repo_hash": "hashB",
                "source": "github",
                "repo_path": repo_b_path,
                "workspace_dir": shared_ws,
                "created_at": now,
                "last_accessed_at": now,
                "retention_days": 14,
                "private_mode": False,
            },
        )

        result = cm.clear_cache("hashA", dry_run=False, base_dir=self.cache_root)
        self.assertTrue(result["ok"])
        self.assertFalse(os.path.exists(os.path.join(self.cache_root, "hashA")))
        self.assertTrue(os.path.isdir(shared_ws), "shared workspace must stay while referenced")
        self.assertTrue(any("shared123" in p for p in result.get("workspace_preserved", [])))


if __name__ == "__main__":
    unittest.main()
