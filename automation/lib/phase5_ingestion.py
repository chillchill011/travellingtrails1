#!/usr/bin/env python3
"""Deterministic Phase 5 normalization and original-file intake."""
from __future__ import annotations

import base64
import binascii
import hashlib
import io
import json
import os
import re
import secrets
from datetime import date
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

import image_pipeline
from phase5_state import ImmutableInputError, RunStore, StateError, canonical_json

MAX_FILES = 40
MAX_FILE_BYTES = 40 * 1024 * 1024
SAFE_SOURCE_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SAFE_RUN_ID_RE = re.compile(r"^tt-[0-9]{8}-[a-f0-9]{16}$")
ALLOWED_AUTHORS = {"aniket", "gauri", "yogesh"}
ALLOWED_SOURCES = {"form", "manual"}
ROLE_ORDER = ("featured", "thumbnail", "gallery", "route", "unused")
ALLOWED_ROLE_COMBINATIONS = {
    ("featured",),
    ("thumbnail",),
    ("featured", "thumbnail"),
    ("gallery",),
    ("route",),
    ("unused",),
}


class IntakeError(ValueError):
    pass


def _text(value: Any, *, name: str, required: bool = False, max_len: int = 20000) -> str:
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise IntakeError(f"{name} must be a string")
    value = value.strip()
    if required and not value:
        raise IntakeError(f"{name} is required")
    if len(value) > max_len:
        raise IntakeError(f"{name} is too long")
    return value


def normalize_trip(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise IntakeError("trip must be an object")
    trip_date = _text(value.get("date"), name="trip.date", required=True, max_len=10)
    try:
        date.fromisoformat(trip_date)
    except ValueError as exc:
        raise IntakeError("trip.date must be YYYY-MM-DD") from exc
    author = _text(value.get("author") or "aniket", name="trip.author", required=True, max_len=32).lower()
    if author not in ALLOWED_AUTHORS:
        raise IntakeError("trip.author is not allowed")
    must_include = value.get("mustInclude") or []
    if not isinstance(must_include, list) or len(must_include) > 100:
        raise IntakeError("trip.mustInclude must be an array")
    normalized_must = [_text(v, name="trip.mustInclude[]", max_len=1000) for v in must_include]
    return {
        "date": trip_date,
        "author": author,
        "destination": _text(value.get("destination"), name="trip.destination", required=True, max_len=300),
        "duration": _text(value.get("duration"), name="trip.duration", max_len=200),
        "rawNotes": _text(value.get("rawNotes"), name="trip.rawNotes", max_len=100000),
        "routeNotes": _text(value.get("routeNotes"), name="trip.routeNotes", max_len=50000),
        "costNotes": _text(value.get("costNotes"), name="trip.costNotes", max_len=50000),
        "gearNotes": _text(value.get("gearNotes"), name="trip.gearNotes", max_len=50000),
        "mustInclude": normalized_must,
    }


def normalize_roles(value: Any) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list) or not value:
        raise IntakeError("file roles must be a non-empty array")
    roles = []
    for role in value:
        role = _text(role, name="file role", required=True, max_len=32).lower()
        if role not in ROLE_ORDER:
            raise IntakeError(f"invalid source role: {role}")
        if role not in roles:
            roles.append(role)
    roles.sort(key=ROLE_ORDER.index)
    if tuple(roles) not in ALLOWED_ROLE_COMBINATIONS:
        raise IntakeError(f"unsupported role combination: {','.join(roles)}")
    return roles


def decode_content(value: Any) -> bytes:
    if not isinstance(value, str) or not value:
        raise IntakeError("contentBase64 is required")
    if value.startswith("data:"):
        raise IntakeError("data URLs are not accepted")
    try:
        data = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise IntakeError("contentBase64 is invalid") from exc
    if not data:
        raise IntakeError("empty image is not accepted")
    if len(data) > MAX_FILE_BYTES:
        raise IntakeError("image exceeds maximum byte length")
    return data


def inspect_image_bytes(data: bytes) -> dict[str, Any]:
    try:
        with Image.open(io.BytesIO(data)) as raw:
            actual_format = raw.format
            raw.verify()
        with Image.open(io.BytesIO(data)) as raw:
            transposed = ImageOps.exif_transpose(raw)
            width, height = transposed.size
            media_type = image_pipeline.pillow_media_type(actual_format)
    except Exception as exc:
        raise IntakeError("uploaded source is not a valid supported image") from exc
    if media_type not in image_pipeline.MEDIA_EXTENSIONS:
        raise IntakeError(f"unsupported source image type: {media_type or actual_format}")
    if width <= 0 or height <= 0:
        raise IntakeError("invalid image dimensions")
    return {
        "mimeType": media_type,
        "width": width,
        "height": height,
        "orientation": image_pipeline.orientation(width, height),
    }


def prepare_submission(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise IntakeError("request body must be an object")
    source = _text(payload.get("source") or "form", name="source", required=True, max_len=32).lower()
    if source not in ALLOWED_SOURCES:
        raise IntakeError("source must be form or manual")
    trip = normalize_trip(payload.get("trip"))
    files = payload.get("files") or []
    if not isinstance(files, list) or not files:
        raise IntakeError("at least one source image is required")
    if len(files) > MAX_FILES:
        raise IntakeError("too many source images")
    test_run = bool(payload.get("testRun", False))
    submission_key = _text(payload.get("submissionKey"), name="submissionKey", max_len=200)

    prepared_files = []
    seen_ids: set[str] = set()
    featured_count = thumbnail_count = 0
    for index, item in enumerate(files):
        if not isinstance(item, dict):
            raise IntakeError("each file must be an object")
        source_id = _text(item.get("sourceId"), name="file.sourceId", required=True, max_len=64).lower()
        if not SAFE_SOURCE_ID_RE.fullmatch(source_id):
            raise IntakeError("file.sourceId is unsafe")
        if source_id in seen_ids:
            raise IntakeError(f"duplicate sourceId: {source_id}")
        seen_ids.add(source_id)
        roles = normalize_roles(item.get("roles") or item.get("role"))
        featured_count += int("featured" in roles)
        thumbnail_count += int("thumbnail" in roles)
        original_filename = _text(item.get("originalFilename") or "unnamed-image", name="file.originalFilename", required=True, max_len=512)
        data = decode_content(item.get("contentBase64"))
        image = inspect_image_bytes(data)
        claimed_mime = _text(item.get("mimeType"), name="file.mimeType", max_len=100).lower()
        if claimed_mime and claimed_mime != image["mimeType"]:
            raise IntakeError(f"MIME type mismatch for {source_id}")
        prepared_files.append({
            "ordinal": index,
            "sourceId": source_id,
            "originalFilename": original_filename,
            "roles": roles,
            "sourceType": "route" if roles == ["route"] else "photo",
            "content": data,
            "byteLength": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            **image,
        })
    if featured_count > 1:
        raise IntakeError("only one featured source is allowed")
    if thumbnail_count > 1:
        raise IntakeError("only one thumbnail source is allowed")

    fingerprint_input = {
        "source": source,
        "trip": trip,
        "submissionKey": submission_key,
        "testRun": test_run,
        "files": [
            {
                "ordinal": f["ordinal"],
                "sourceId": f["sourceId"],
                "originalFilename": f["originalFilename"],
                "roles": f["roles"],
                "mimeType": f["mimeType"],
                "byteLength": f["byteLength"],
                "sha256": f["sha256"],
            }
            for f in prepared_files
        ],
    }
    fingerprint = hashlib.sha256(canonical_json(fingerprint_input).encode("utf-8")).hexdigest()
    run_id = f"tt-{trip['date'].replace('-', '')}-{fingerprint[:16]}"
    supplied_run_id = _text(payload.get("runId"), name="runId", max_len=64)
    if supplied_run_id:
        if not SAFE_RUN_ID_RE.fullmatch(supplied_run_id):
            raise IntakeError("supplied runId has invalid format")
        if supplied_run_id != run_id:
            raise ImmutableInputError("supplied runId does not match immutable payload")
    post_slug = image_pipeline.sanitize_slug(f"{trip['date']}-{trip['destination']}-{fingerprint[:8]}")

    def descriptor(f: dict[str, Any]) -> dict[str, Any]:
        return {
            "sourceId": f["sourceId"],
            "originalFilename": f["originalFilename"],
            "roles": f["roles"],
            "sourceType": f["sourceType"],
            "mimeType": f["mimeType"],
            "byteLength": f["byteLength"],
            "width": f["width"],
            "height": f["height"],
            "orientation": f["orientation"],
            "sha256": f["sha256"],
            "processingStatus": "PENDING",
        }

    all_descriptors = [descriptor(f) for f in prepared_files]
    normalized_input = {
        "runId": run_id,
        "source": source,
        "trip": trip,
        "photos": [d for d in all_descriptors if d["sourceType"] == "photo"],
        "routeImages": [d for d in all_descriptors if d["sourceType"] == "route"],
        "testRun": test_run,
    }
    raw_input = {
        "source": source,
        "trip": payload.get("trip"),
        "submissionKey": submission_key,
        "testRun": test_run,
        "files": [
            {
                "sourceId": f["sourceId"],
                "originalFilename": f["originalFilename"],
                "roles": f["roles"],
                "claimedMimeType": _text(files[f["ordinal"]].get("mimeType"), name="file.mimeType", max_len=100),
                "byteLength": f["byteLength"],
                "sha256": f["sha256"],
            }
            for f in prepared_files
        ],
    }
    return {
        "runId": run_id,
        "postSlug": post_slug,
        "source": source,
        "trip": trip,
        "files": prepared_files,
        "fingerprint": fingerprint,
        "rawInput": raw_input,
        "normalizedInput": normalized_input,
        "testRun": test_run,
    }


def _safe_run_dir(root: Path, run_id: str) -> Path:
    if not SAFE_RUN_ID_RE.fullmatch(run_id):
        raise IntakeError("unsafe runId")
    root = root.resolve()
    run_dir = root / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    run_dir = run_dir.resolve()
    if os.path.commonpath([str(root), str(run_dir)]) != str(root):
        raise IntakeError("run path escaped state root")
    return run_dir


def _write_source(path: Path, data: bytes, expected_sha256: str) -> None:
    if path.exists() or path.is_symlink():
        if path.is_symlink() or not path.is_file():
            raise IntakeError("unsafe existing source path")
        current = image_pipeline.sha256_file(path)
        if current != expected_sha256:
            raise ImmutableInputError("existing source bytes differ from immutable source hash")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    tmp = path.parent / f".{path.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(tmp, flags, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=True) as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if hashlib.sha256(tmp.read_bytes()).hexdigest() != expected_sha256:
            raise IntakeError("source hash verification failed before durable rename")
        os.replace(tmp, path)
        path.chmod(0o600)
    finally:
        if tmp.exists():
            tmp.unlink()


def ingest_submission(store: RunStore, payload: Any) -> dict[str, Any]:
    prepared = prepare_submission(payload)
    run_id = prepared["runId"]
    run, created = store.create_or_verify_run(
        run_id=run_id,
        source=prepared["source"],
        post_slug=prepared["postSlug"],
        raw_input=prepared["rawInput"],
        normalized_input=prepared["normalizedInput"],
        fingerprint=prepared["fingerprint"],
        test_run=prepared["testRun"],
    )
    if run["status"] == "GITHUB_IMAGES_COMPLETE":
        return {"runId": run_id, "created": created, "status": run["status"], "postSlug": run["post_slug"], "idempotent": True}

    if run["status"] == "RECEIVED":
        run = store.transition(run_id, "NORMALIZED", last_safe_status="NORMALIZED", detail="canonical input normalized")
    elif run["status"] == "FAILED" and run.get("last_safe_status") in {None, "RECEIVED", "NORMALIZED"}:
        run = store.transition(run_id, "NORMALIZED", last_safe_status="NORMALIZED", error_message=None, detail="retry normalized immutable input")

    run_dir = _safe_run_dir(store.root, run_id)
    source_dir = run_dir / "sources"
    manifest: list[dict[str, Any]] = []
    for f in prepared["files"]:
        internal_name = f"source-{f['sourceId']}.bin"
        target = source_dir / internal_name
        _write_source(target, f["content"], f["sha256"])
        safe_ref = target.relative_to(store.root).as_posix()
        record = {
            "sourceId": f["sourceId"],
            "originalFilename": f["originalFilename"],
            "safeRef": safe_ref,
            "sourceType": f["sourceType"],
            "roles": f["roles"],
            "mimeType": f["mimeType"],
            "byteLength": f["byteLength"],
            "width": f["width"],
            "height": f["height"],
            "orientation": f["orientation"],
            "sha256": f["sha256"],
            "processingStatus": "STORED",
        }
        store.upsert_source(run_id, record)
        manifest.append(record)
    store.set_source_manifest(run_id, manifest)
    latest = store.get_run(run_id)
    if latest is None:
        raise StateError("run disappeared")
    if latest["status"] in {"NORMALIZED", "FAILED"}:
        if latest["status"] == "FAILED" and latest.get("last_safe_status") not in {"NORMALIZED", "FILES_STORED"}:
            return {"runId": run_id, "created": created, "status": latest["status"], "postSlug": latest["post_slug"], "idempotent": not created}
        latest = store.transition(run_id, "FILES_STORED", last_safe_status="FILES_STORED", error_message=None, detail="all immutable source files stored and hashed")
    return {"runId": run_id, "created": created, "status": latest["status"], "postSlug": latest["post_slug"], "idempotent": not created}


def run_public_view(store: RunStore, run_id: str) -> dict[str, Any]:
    run = store.get_run(run_id)
    if run is None:
        raise StateError("run not found")
    def parse(name: str, fallback: Any) -> Any:
        try:
            return json.loads(run[name]) if run.get(name) else fallback
        except Exception:
            return fallback
    return {
        "runId": run["run_id"],
        "source": run["source"],
        "status": run["status"],
        "lastSafeStatus": run["last_safe_status"],
        "createdAt": run["created_at"],
        "updatedAt": run["updated_at"],
        "postSlug": run["post_slug"],
        "postPath": run["post_path"],
        "gitCommitSha": run["git_commit_sha"],
        "normalizedInput": parse("normalized_input_json", {}),
        "validationErrors": parse("validation_errors_json", []),
        "sourceImageManifest": parse("source_image_manifest_json", []),
        "processedImageManifest": parse("processed_image_manifest_json", []),
        "errorMessage": run["error_message"],
        "testRun": bool(run["test_run"]),
        "cleanupAt": run["cleanup_at"],
        "history": store.history(run_id),
    }
