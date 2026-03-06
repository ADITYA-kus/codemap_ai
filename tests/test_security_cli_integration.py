import os
import subprocess
import sys
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class TestCliTokenSecurity(unittest.TestCase):
    def _cache_files(self):
        cache_root = os.path.join(PROJECT_ROOT, ".codemap_cache")
        if not os.path.isdir(cache_root):
            return []
        files = []
        for root, _dirs, names in os.walk(cache_root):
            for name in names:
                files.append(os.path.join(root, name))
        return files

    def test_token_not_leaked_to_output_or_cache(self):
        token = "ghp_TESTTOKEN1234567890abcDEF"
        cmd = [
            sys.executable,
            os.path.join(PROJECT_ROOT, "cli.py"),
            "api",
            "analyze",
            "--github",
            "https://gitlab.com/x/y",
            "--ref",
            "main",
            "--mode",
            "zip",
            "--token",
            token,
        ]
        proc = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
        self.assertNotIn(token, combined)

        token_bytes = token.encode("utf-8")
        for path in self._cache_files():
            try:
                with open(path, "rb") as f:
                    data = f.read()
                self.assertNotIn(token_bytes, data, msg=f"Token leaked in file: {path}")
            except OSError:
                continue



if __name__ == "__main__":
    unittest.main()
