#!/usr/bin/env python3
"""Durable Phase 5 run state for Travelling Trails.

Application state lives in a dedicated SQLite database. This module never touches
n8n's internal database.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

STATUSES = (
    "RECEIVED",
    "NORMALIZED",
    "FILES_STORED",
    "IMAGES_PROCESSING",
    "IMAGES_PROCESSED",
    "GITHUB_IMAGES_WRITING",
    "GITHUB_IMAGES_COMPLETE",
    "FAILED",
)

TRANSITIONS = {
    "RECEIVED": {"NORMALIZED", "FAILED"},
    "NORMALIZED": {"FILES_STORED", "FAILED"},
    "FILES_STORED": {"IMAGES_PROCESSING", "FAILED"},
    "IMAGES_PROCESSING": {"IMAGES_PROCESSED", "FAILED"},
    "IMAGES_PROCESSED": {"GITHUB_IMAGES_WRITING", "FAILED"},
    "GITHUB_IMAGES_WRITING": {"GITHUB_IMAGES_WRITING", "GITHUB_IMAGES_COMPLETE", "FAILED"},
    "GITHUB_IMAGES_COMPLETE": {"GITHUB_IMAGES_COMPLETE"},
    "FAILED": {"NORMALIZED", "FILES_STORED", "IMAGES_PROCESSING", "GITHUB_IMAGES_WRITING", "GITHUB_IMAGES_COMPLETE", "FAILED"},
}

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  status TEXT NOT NULL,
  last_safe_status TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  post_slug TEXT NOT NULL,
  post_path TEXT,
  git_commit_sha TEXT,
  raw_input_json TEXT NOT NULL,
  normalized_input_json TEXT NOT NULL,
  generated_json TEXT,
  validation_errors_json TEXT NOT NULL DEFAULT '[]',
  source_image_manifest_json TEXT NOT NULL DEFAULT '[]',
  processed_image_manifest_json TEXT NOT NULL DEFAULT '[]',
  error_message TEXT,
  input_fingerprint TEXT NOT NULL UNIQUE,
  test_run INTEGER NOT NULL DEFAULT 0,
  cleanup_at TEXT,
  CHECK (status IN ('RECEIVED','NORMALIZED','FILES_STORED','IMAGES_PROCESSING','IMAGES_PROCESSED','GITHUB_IMAGES_WRITING','GITHUB_IMAGES_COMPLETE','FAILED')),
  CHECK (test_run IN (0,1))
);
CREATE TABLE IF NOT EXISTS source_images (
  run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  source_id TEXT NOT NULL,
  original_filename TEXT NOT NULL,
  safe_ref TEXT NOT NULL,
  source_type TEXT NOT NULL,
  roles_json TEXT NOT NULL,
  mime_type TEXT NOT NULL,
  byte_length INTEGER NOT NULL,
  width INTEGER NOT NULL,
  height INTEGER NOT NULL,
  orientation TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  processing_status TEXT NOT NULL,
  PRIMARY KEY (run_id, source_id),
  UNIQUE (run_id, safe_ref)
);
CREATE TABLE IF NOT EXISTS processed_images (
  run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  repo_path TEXT NOT NULL,
  source_id TEXT NOT NULL,
  role TEXT NOT NULL,
  filename TEXT NOT NULL,
  public_path TEXT NOT NULL,
  local_ref TEXT NOT NULL,
  width INTEGER NOT NULL,
  height INTEGER NOT NULL,
  byte_length INTEGER NOT NULL,
  sha256 TEXT NOT NULL,
  git_blob_sha TEXT NOT NULL,
  status TEXT NOT NULL,
  PRIMARY KEY (run_id, repo_path)
);
CREATE TABLE IF NOT EXISTS status_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  from_status TEXT,
  to_status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  detail TEXT
);
CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
CREATE INDEX IF NOT EXISTS idx_sources_run ON source_images(run_id);
CREATE INDEX IF NOT EXISTS idx_outputs_run ON processed_images(run_id);
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class StateError(RuntimeError):
    pass


class ImmutableInputError(StateError):
    pass


class RunStore:
    def __init__(self, root: str | os.PathLike[str]):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        try:
            self.root.chmod(0o700)
        except PermissionError:
            pass
        self.db_path = self.root / "phase5.sqlite3"
        with self.connect() as db:
            db.executescript(SCHEMA)

    def connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.db_path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=30000")
        db.execute("PRAGMA journal_mode=WAL")
        return db

    @staticmethod
    def _dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
        return dict(row) if row is not None else None

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self.connect() as db:
            return self._dict(db.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone())

    def get_sources(self, run_id: str) -> list[dict[str, Any]]:
        with self.connect() as db:
            return [dict(r) for r in db.execute("SELECT * FROM source_images WHERE run_id=? ORDER BY source_id", (run_id,))]

    def get_outputs(self, run_id: str) -> list[dict[str, Any]]:
        with self.connect() as db:
            return [dict(r) for r in db.execute("SELECT * FROM processed_images WHERE run_id=? ORDER BY repo_path", (run_id,))]

    def create_or_verify_run(self, *, run_id: str, source: str, post_slug: str,
                             raw_input: dict[str, Any], normalized_input: dict[str, Any],
                             fingerprint: str, test_run: bool = False) -> tuple[dict[str, Any], bool]:
        now = utc_now()
        with self.connect() as db:
            row = db.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
            if row is not None:
                existing = dict(row)
                if existing["input_fingerprint"] != fingerprint:
                    raise ImmutableInputError("runId already exists with different immutable input")
                return existing, False
            by_fp = db.execute("SELECT * FROM runs WHERE input_fingerprint=?", (fingerprint,)).fetchone()
            if by_fp is not None:
                existing = dict(by_fp)
                if existing["run_id"] != run_id:
                    raise ImmutableInputError("immutable input fingerprint already belongs to another runId")
                return existing, False
            db.execute(
                """INSERT INTO runs
                (run_id,source,status,last_safe_status,created_at,updated_at,post_slug,post_path,git_commit_sha,
                 raw_input_json,normalized_input_json,generated_json,validation_errors_json,
                 source_image_manifest_json,processed_image_manifest_json,error_message,input_fingerprint,test_run)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (run_id, source, "RECEIVED", None, now, now, post_slug, None, None,
                 canonical_json(raw_input), canonical_json(normalized_input), None, "[]", "[]", "[]", None,
                 fingerprint, 1 if test_run else 0),
            )
            db.execute(
                "INSERT INTO status_history(run_id,from_status,to_status,created_at,detail) VALUES (?,?,?,?,?)",
                (run_id, None, "RECEIVED", now, "run created"),
            )
            row = db.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
            return dict(row), True

    def transition(self, run_id: str, new_status: str, *, last_safe_status: str | None = None,
                   error_message: str | None = None, detail: str | None = None,
                   expected: Iterable[str] | None = None) -> dict[str, Any]:
        if new_status not in STATUSES:
            raise StateError(f"unknown status: {new_status}")
        now = utc_now()
        with self.connect() as db:
            row = db.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
            if row is None:
                raise StateError("run not found")
            old = row["status"]
            if expected is not None and old not in set(expected):
                raise StateError(f"status {old} cannot perform requested operation")
            if new_status != old and new_status not in TRANSITIONS.get(old, set()):
                raise StateError(f"invalid status transition {old} -> {new_status}")
            db.execute(
                "UPDATE runs SET status=?,last_safe_status=COALESCE(?,last_safe_status),updated_at=?,error_message=? WHERE run_id=?",
                (new_status, last_safe_status, now, error_message, run_id),
            )
            if new_status != old or detail or error_message:
                db.execute(
                    "INSERT INTO status_history(run_id,from_status,to_status,created_at,detail) VALUES (?,?,?,?,?)",
                    (run_id, old, new_status, now, detail or error_message),
                )
            out = db.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
            return dict(out)

    def fail(self, run_id: str, message: str, *, last_safe_status: str | None = None) -> dict[str, Any]:
        return self.transition(run_id, "FAILED", last_safe_status=last_safe_status,
                               error_message=str(message)[:4000], detail=str(message)[:4000])

    def upsert_source(self, run_id: str, source: dict[str, Any]) -> None:
        values = (
            run_id, source["sourceId"], source["originalFilename"], source["safeRef"], source["sourceType"],
            canonical_json(source["roles"]), source["mimeType"], int(source["byteLength"]), int(source["width"]),
            int(source["height"]), source["orientation"], source["sha256"], source["processingStatus"],
        )
        with self.connect() as db:
            row = db.execute("SELECT * FROM source_images WHERE run_id=? AND source_id=?", (run_id, source["sourceId"])).fetchone()
            if row is None:
                db.execute(
                    """INSERT INTO source_images
                    (run_id,source_id,original_filename,safe_ref,source_type,roles_json,mime_type,byte_length,width,height,orientation,sha256,processing_status)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""", values,
                )
                return
            current = dict(row)
            immutable = {
                "original_filename": source["originalFilename"], "safe_ref": source["safeRef"],
                "source_type": source["sourceType"], "roles_json": canonical_json(source["roles"]),
                "mime_type": source["mimeType"], "byte_length": int(source["byteLength"]),
                "width": int(source["width"]), "height": int(source["height"]),
                "orientation": source["orientation"], "sha256": source["sha256"],
            }
            for key, expected_value in immutable.items():
                if current[key] != expected_value:
                    raise ImmutableInputError(f"source {source['sourceId']} changed immutable field {key}")
            db.execute(
                "UPDATE source_images SET processing_status=? WHERE run_id=? AND source_id=?",
                (source["processingStatus"], run_id, source["sourceId"]),
            )

    def set_source_manifest(self, run_id: str, manifest: list[dict[str, Any]]) -> None:
        now = utc_now()
        with self.connect() as db:
            db.execute(
                "UPDATE runs SET source_image_manifest_json=?,updated_at=? WHERE run_id=?",
                (canonical_json(manifest), now, run_id),
            )

    def replace_outputs(self, run_id: str, manifest: dict[str, Any], outputs: list[dict[str, Any]]) -> None:
        now = utc_now()
        with self.connect() as db:
            db.execute("DELETE FROM processed_images WHERE run_id=?", (run_id,))
            for o in outputs:
                db.execute(
                    """INSERT INTO processed_images
                    (run_id,repo_path,source_id,role,filename,public_path,local_ref,width,height,byte_length,sha256,git_blob_sha,status)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (run_id, o["repoPath"], o["sourceId"], o["role"], o["filename"], o["publicPath"], o["localRef"],
                     int(o["width"]), int(o["height"]), int(o["bytes"]), o["sha256"], o["gitBlobSha"], o["status"]),
                )
            db.execute(
                "UPDATE runs SET processed_image_manifest_json=?,updated_at=? WHERE run_id=?",
                (canonical_json(manifest), now, run_id),
            )

    def mark_sources_processed(self, run_id: str) -> None:
        with self.connect() as db:
            rows = db.execute("SELECT source_id,roles_json FROM source_images WHERE run_id=?", (run_id,)).fetchall()
            for row in rows:
                roles = json.loads(row["roles_json"])
                status = "UNUSED" if roles == ["unused"] else "PROCESSED"
                db.execute(
                    "UPDATE source_images SET processing_status=? WHERE run_id=? AND source_id=?",
                    (status, run_id, row["source_id"]),
                )

    def complete_github(self, run_id: str, commit_sha: str, outputs: list[dict[str, Any]]) -> dict[str, Any]:
        now = utc_now()
        with self.connect() as db:
            row = db.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
            if row is None:
                raise StateError("run not found")
            for o in outputs:
                db.execute(
                    "UPDATE processed_images SET status=? WHERE run_id=? AND repo_path=?",
                    (o.get("status", "GITHUB_COMPLETE"), run_id, o["repoPath"]),
                )
            old = row["status"]
            if old not in {"GITHUB_IMAGES_WRITING", "GITHUB_IMAGES_COMPLETE"}:
                raise StateError(f"cannot complete GitHub from status {old}")
            db.execute(
                "UPDATE runs SET status='GITHUB_IMAGES_COMPLETE',last_safe_status='GITHUB_IMAGES_COMPLETE',git_commit_sha=?,updated_at=?,error_message=NULL WHERE run_id=?",
                (commit_sha, now, run_id),
            )
            if old != "GITHUB_IMAGES_COMPLETE":
                db.execute(
                    "INSERT INTO status_history(run_id,from_status,to_status,created_at,detail) VALUES (?,?,?,?,?)",
                    (run_id, old, "GITHUB_IMAGES_COMPLETE", now, f"commit {commit_sha}"),
                )
            return dict(db.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone())

    def set_cleanup_at(self, run_id: str) -> None:
        with self.connect() as db:
            db.execute("UPDATE runs SET cleanup_at=?,updated_at=? WHERE run_id=?", (utc_now(), utc_now(), run_id))
            db.execute("UPDATE source_images SET processing_status='PURGED' WHERE run_id=?", (run_id,))

    def history(self, run_id: str) -> list[dict[str, Any]]:
        with self.connect() as db:
            return [dict(r) for r in db.execute("SELECT from_status,to_status,created_at,detail FROM status_history WHERE run_id=? ORDER BY id", (run_id,))]
