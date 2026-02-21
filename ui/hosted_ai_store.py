from __future__ import annotations

import os
import sqlite3
import time
from typing import Any, Dict, Optional


def _connect(db_path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS hosted_cache (
              cache_key TEXT PRIMARY KEY,
              created_at REAL NOT NULL,
              provider TEXT NOT NULL,
              model TEXT NOT NULL,
              summary_text TEXT NOT NULL,
              repo_hash TEXT NOT NULL,
              fqn TEXT,
              request_type TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS hosted_quota (
              device_id TEXT NOT NULL,
              day TEXT NOT NULL,
              request_count INTEGER NOT NULL DEFAULT 0,
              last_ts REAL NOT NULL DEFAULT 0,
              PRIMARY KEY (device_id, day)
            )
            """
        )
        conn.commit()


def get_cached(db_path: str, key: str) -> Optional[Dict[str, Any]]:
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT cache_key, created_at, provider, model, summary_text, repo_hash, fqn, request_type "
            "FROM hosted_cache WHERE cache_key = ?",
            (key,),
        ).fetchone()
    if not row:
        return None
    return dict(row)


def set_cached(
    db_path: str,
    key: str,
    provider: str,
    model: str,
    summary: str,
    repo_hash: str,
    fqn: Optional[str],
    request_type: str,
) -> None:
    now_ts = float(time.time())
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO hosted_cache (
              cache_key, created_at, provider, model, summary_text, repo_hash, fqn, request_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(cache_key) DO UPDATE SET
              created_at = excluded.created_at,
              provider = excluded.provider,
              model = excluded.model,
              summary_text = excluded.summary_text,
              repo_hash = excluded.repo_hash,
              fqn = excluded.fqn,
              request_type = excluded.request_type
            """,
            (key, now_ts, provider, model, summary, repo_hash, fqn, request_type),
        )
        conn.commit()


def get_quota_state(db_path: str, device_id: str, day: str) -> Dict[str, Any]:
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT request_count, last_ts FROM hosted_quota WHERE device_id = ? AND day = ?",
            (device_id, day),
        ).fetchone()
    if not row:
        return {"count": 0, "last_ts": 0.0}
    return {"count": int(row["request_count"]), "last_ts": float(row["last_ts"])}


def increment_quota(db_path: str, device_id: str, day: str, now_ts: float) -> Dict[str, Any]:
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO hosted_quota (device_id, day, request_count, last_ts)
            VALUES (?, ?, 1, ?)
            ON CONFLICT(device_id, day) DO UPDATE SET
              request_count = request_count + 1,
              last_ts = excluded.last_ts
            """,
            (device_id, day, float(now_ts)),
        )
        conn.commit()
        row = conn.execute(
            "SELECT request_count, last_ts FROM hosted_quota WHERE device_id = ? AND day = ?",
            (device_id, day),
        ).fetchone()
    if not row:
        return {"count": 0, "last_ts": 0.0}
    return {"count": int(row["request_count"]), "last_ts": float(row["last_ts"])}


def update_last_ts(db_path: str, device_id: str, day: str, now_ts: float) -> Dict[str, Any]:
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO hosted_quota (device_id, day, request_count, last_ts)
            VALUES (?, ?, 0, ?)
            ON CONFLICT(device_id, day) DO UPDATE SET
              last_ts = excluded.last_ts
            """,
            (device_id, day, float(now_ts)),
        )
        conn.commit()
        row = conn.execute(
            "SELECT request_count, last_ts FROM hosted_quota WHERE device_id = ? AND day = ?",
            (device_id, day),
        ).fetchone()
    if not row:
        return {"count": 0, "last_ts": 0.0}
    return {"count": int(row["request_count"]), "last_ts": float(row["last_ts"])}
