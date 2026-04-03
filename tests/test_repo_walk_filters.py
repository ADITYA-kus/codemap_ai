import os
import shutil
import unittest

from analysis.explain.explain_runner import collect_python_files
from analysis.utils.cache_manager import collect_fingerprints
from analysis.utils.repo_walk import filter_skipped_dirs


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class TestRepoWalkFilters(unittest.TestCase):
    def test_filter_skipped_dirs_covers_env_and_dependency_folders(self):
        kept = filter_skipped_dirs([
            "src",
            ".git",
            ".venv",
            "venv",
            "env",
            "ENV",
            ".env",
            "node_modules",
            "site-packages",
            "dist-packages",
        ])
        self.assertEqual(kept, ["src"])

    def test_collectors_skip_nested_site_packages_and_envs(self):
        repo_dir = os.path.join(PROJECT_ROOT, "tests", "_tmp_repo_walk_filters")
        shutil.rmtree(repo_dir, ignore_errors=True)
        try:
            os.makedirs(os.path.join(repo_dir, "src"), exist_ok=True)
            os.makedirs(os.path.join(repo_dir, "ci", "Lib", "site-packages", "pkg"), exist_ok=True)
            os.makedirs(os.path.join(repo_dir, "env", "Lib"), exist_ok=True)
            os.makedirs(os.path.join(repo_dir, ".env", "Lib"), exist_ok=True)

            with open(os.path.join(repo_dir, "src", "main.py"), "w", encoding="utf-8") as f:
                f.write("def ok():\n    return 1\n")
            with open(os.path.join(repo_dir, "ci", "Lib", "site-packages", "pkg", "ignored.py"), "w", encoding="utf-8") as f:
                f.write("x = 1\n")
            with open(os.path.join(repo_dir, "env", "Lib", "ignored.py"), "w", encoding="utf-8") as f:
                f.write("x = 2\n")
            with open(os.path.join(repo_dir, ".env", "Lib", "ignored.py"), "w", encoding="utf-8") as f:
                f.write("x = 3\n")

            files = [os.path.relpath(p, repo_dir).replace("\\", "/") for p in collect_python_files(repo_dir)]
            self.assertEqual(files, ["src/main.py"])

            fingerprints = collect_fingerprints(repo_dir)
            self.assertEqual(sorted(fingerprints.keys()), ["src/main.py"])
        finally:
            shutil.rmtree(repo_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
