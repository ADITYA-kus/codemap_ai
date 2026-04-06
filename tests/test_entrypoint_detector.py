import os
import shutil
import unittest

from analysis.graph.entrypoint_detector import detect_entry_points


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class TestEntrypointDetector(unittest.TestCase):
    def test_detects_routes_cli_and_script_starts(self):
        repo_dir = os.path.join(PROJECT_ROOT, "tests", "_tmp_entrypoint_repo")
        shutil.rmtree(repo_dir, ignore_errors=True)
        try:
            os.makedirs(os.path.join(repo_dir, "api"), exist_ok=True)
            os.makedirs(os.path.join(repo_dir, "cli"), exist_ok=True)

            with open(os.path.join(repo_dir, "api", "routes.py"), "w", encoding="utf-8") as f:
                f.write(
                    "from fastapi import APIRouter\n"
                    "router = APIRouter()\n\n"
                    "@router.get('/items')\n"
                    "def list_items():\n"
                    "    return []\n"
                )

            with open(os.path.join(repo_dir, "cli", "commands.py"), "w", encoding="utf-8") as f:
                f.write(
                    "import click\n\n"
                    "@click.command()\n"
                    "def run():\n"
                    "    return 1\n"
                )

            with open(os.path.join(repo_dir, "__main__.py"), "w", encoding="utf-8") as f:
                f.write(
                    "def main():\n"
                    "    return 42\n\n"
                    "if __name__ == '__main__':\n"
                    "    main()\n"
                )

            rows = detect_entry_points(repo_dir, repo_prefix="demo_repo")
            kinds = [row["kind"] for row in rows]
            titles = [row["title"] for row in rows]

            self.assertIn("api_route", kinds)
            self.assertIn("cli_command", kinds)
            self.assertIn("script_start", kinds)
            self.assertIn("GET /items", titles)
            self.assertIn("CLI command: run", titles)
            self.assertIn("Run this file directly", titles)
            self.assertIn("Script start: main()", titles)
        finally:
            shutil.rmtree(repo_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
