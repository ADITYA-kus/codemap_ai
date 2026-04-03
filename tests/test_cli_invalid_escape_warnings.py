import os
import shutil
import subprocess
import sys
import unittest


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class TestCliInvalidEscapeWarnings(unittest.TestCase):
    def test_analyze_suppresses_invalid_escape_syntax_warnings(self):
        repo_dir = os.path.join(PROJECT_ROOT, "tests", "_tmp_invalid_escape_repo")
        shutil.rmtree(repo_dir, ignore_errors=True)
        try:
            os.makedirs(repo_dir, exist_ok=True)
            with open(os.path.join(repo_dir, "warns.py"), "w", encoding="utf-8") as f:
                f.write(
                    'PATTERNS = ["\\\\S", "\\\\[", "\\\\:", "\\\\d"]\n'
                    "def read_patterns():\n"
                    "    return PATTERNS\n"
                )

            cmd = [sys.executable, os.path.join(PROJECT_ROOT, "codemap_app.py"), "analyze", "--path", repo_dir]
            proc = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, check=False)

            self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
            self.assertNotIn("SyntaxWarning", proc.stderr)
            self.assertNotIn("invalid escape sequence", proc.stderr)
        finally:
            shutil.rmtree(repo_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
