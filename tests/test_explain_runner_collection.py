import os
import shutil
import unittest

from analysis.explain.explain_runner import collect_python_files


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class TestExplainRunnerCollection(unittest.TestCase):
    def test_collect_python_files_skips_heavy_non_source_dirs(self):
        repo_dir = os.path.join(PROJECT_ROOT, "tests", "_tmp_explain_collection_repo")
        shutil.rmtree(repo_dir, ignore_errors=True)
        try:
            os.makedirs(os.path.join(repo_dir, "pkg"), exist_ok=True)
            os.makedirs(os.path.join(repo_dir, ".venv", "lib"), exist_ok=True)
            os.makedirs(os.path.join(repo_dir, "node_modules", "pkg"), exist_ok=True)
            os.makedirs(os.path.join(repo_dir, ".codemap_cache", "x"), exist_ok=True)

            with open(os.path.join(repo_dir, "pkg", "main.py"), "w", encoding="utf-8") as f:
                f.write("def ok():\n    return 1\n")
            with open(os.path.join(repo_dir, ".venv", "lib", "ignored.py"), "w", encoding="utf-8") as f:
                f.write("x = 1\n")
            with open(os.path.join(repo_dir, "node_modules", "pkg", "ignored.py"), "w", encoding="utf-8") as f:
                f.write("x = 2\n")
            with open(os.path.join(repo_dir, ".codemap_cache", "x", "ignored.py"), "w", encoding="utf-8") as f:
                f.write("x = 3\n")

            files = [os.path.relpath(p, repo_dir).replace("\\", "/") for p in collect_python_files(repo_dir)]
            self.assertEqual(files, ["pkg/main.py"])
        finally:
            shutil.rmtree(repo_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
