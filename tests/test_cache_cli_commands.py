import json
import os
import subprocess
import sys
import tempfile
import unittest


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class TestCacheCliCommands(unittest.TestCase):
    def _run_cli(self, *args):
        cmd = [sys.executable, os.path.join(PROJECT_ROOT, "cli.py"), "api", *args]
        proc = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, check=False)
        try:
            payload = json.loads((proc.stdout or "").strip() or "{}")
        except Exception:
            payload = {"ok": False, "stdout": proc.stdout, "stderr": proc.stderr}
        return proc.returncode, payload

    def test_cache_commands_schema(self):
        with tempfile.TemporaryDirectory() as td:
            repo_dir = os.path.join(td, "repo")
            os.makedirs(repo_dir, exist_ok=True)
            with open(os.path.join(repo_dir, "a.py"), "w", encoding="utf-8") as f:
                f.write("def x():\n    return 1\n")

            rc_an, out_an = self._run_cli("analyze", "--path", repo_dir)
            self.assertEqual(rc_an, 0, msg=out_an)
            self.assertTrue(out_an.get("ok"))

            rc_list, out_list = self._run_cli("cache", "list")
            self.assertEqual(rc_list, 0, msg=out_list)
            self.assertTrue(out_list.get("ok"))
            self.assertIn("count", out_list)
            self.assertIn("caches", out_list)

            rc_ret, out_ret = self._run_cli("cache", "retention", "--path", repo_dir, "--days", "7", "--yes")
            self.assertEqual(rc_ret, 0, msg=out_ret)
            self.assertTrue(out_ret.get("ok"))
            self.assertEqual(out_ret.get("days"), 7)

            rc_sweep, out_sweep = self._run_cli("cache", "sweep", "--dry-run")
            self.assertEqual(rc_sweep, 0, msg=out_sweep)
            self.assertTrue(out_sweep.get("ok"))
            self.assertTrue(out_sweep.get("dry_run"))
            self.assertIn("would_delete", out_sweep)

            rc_clear_dry, out_clear_dry = self._run_cli("cache", "clear", "--path", repo_dir, "--dry-run")
            self.assertEqual(rc_clear_dry, 0, msg=out_clear_dry)
            self.assertTrue(out_clear_dry.get("ok"))
            self.assertTrue(out_clear_dry.get("dry_run"))
            self.assertIn("would_delete", out_clear_dry)

            rc_clear, out_clear = self._run_cli("cache", "clear", "--path", repo_dir, "--yes")
            self.assertEqual(rc_clear, 0, msg=out_clear)
            self.assertTrue(out_clear.get("ok"))
            self.assertIn("deleted", out_clear)
            self.assertIn("freed_bytes_estimate", out_clear)


if __name__ == "__main__":
    unittest.main()
