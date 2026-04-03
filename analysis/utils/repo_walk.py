"""Shared repository walking rules for source analysis."""

from __future__ import annotations

from typing import Iterable


SKIP_DIR_NAMES = {
    ".git",
    "__pycache__",
    ".codemap_cache",
    ".venv",
    "venv",
    "env",
    "ENV",
    ".env",
    "node_modules",
    "site-packages",
    "dist-packages",
    ".tox",
    ".nox",
}


def filter_skipped_dirs(dir_names: Iterable[str]) -> list[str]:
    """Return directory names that should still be traversed."""
    return [name for name in dir_names if name not in SKIP_DIR_NAMES]
