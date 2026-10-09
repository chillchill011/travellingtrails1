#!/usr/bin/env python3
"""Disk-backed, per-file form upload intake for Phase 5.

Large browser form uploads remain n8n binary data. n8n sends one raw file at a
time to this internal-only worker, which streams it to a temporary upload batch.
A small JSON finalize request then creates/verifies the deterministic durable run.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shutil
from pathlib import Path
from typing import Any, BinaryIO

from PIL import Image, ImageOps

import image_pipeline
from phase5_ingestion import (
    ALLOWED_SOURCES,
    MAX_FILE_BYTES,
    MAX_FILES,
    SAFE_RUN_ID_RE,
    SAFE_SOURCE_ID_RE,
    IntakeError,
    _safe_run_dir,
    _text,
    normalize_roles,
    normalize_trip,
)
from phase5_state import ImmutableInputError, RunStore, StateError, canonical_json

SAFE_UPLOAD_BATCH_RE = re.compile(r"^up-[0-9]{1,20}$")


def _batch_dir(root: Path, batch_id: str, *, create: bool = False) -> Path:
    if not SAFE_UPLOAD_BATCH_RE.fullmatch(str(batch_id or '')):
        raise IntakeError("unsafe upload batch id")
    root = root.resolve()
    uploads = (root / "uploads").resolve()
    uploads.mkdir(parents=True, exist_ok=True)
    try:
        uploads.chmod(0o700)
    except PermissionError:
        pass
    batch = uploads / batch_id
    if create:
        batch.mkdir(parents=True, exist_ok=True)
        try:
            batch.chmod(0o700)
        except PermissionError:
            pass
    batch = batch.resolve()
    if os.path.commonpath([str(root), str(batch)]) != str(root):
        raise IntakeError("upload batch escaped state root")
    return batch


def _inspect_image_path(path: Path) -> dict[str, Any]:
    try:
        with Image.open(path) as raw:
            actual_format = raw.format
            raw.verify()
        with Image.open(path) as raw:
            transposed = ImageOps.exif_transpose(raw)
            width, height = transposed.size
            media_type = Image.MIME.get(actual_format or "", "")
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


def _atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    data = canonical_json(value).encode("utf-8")
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
        os.replace(tmp, path)
        path.chmod(0o600)
    finally:
        if tmp.exists():
            tmp.unlink()


def store_streamed_upload(
    store: RunStore,
    *,
    batch_id: str,
    source_id: str,
    original_filename: str,
    roles_value: Any,
    claimed_mime: str,
    content_type: str,
    content_length: int,
    stream: BinaryIO,
) -> dict[str, Any]:
    """Stream one source image to disk and persist immutable batch metadata."""
    source_id = _text(source_id, name="file.sourceId", required=True, max_len=64).lower()
    if not SAFE_SOURCE_ID_RE.fullmatch(source_id):
        raise IntakeError("file.sourceId is unsafe")
    roles = normalize_roles(roles_value)
    original_filename = _text(original_filename, name="file.originalFilename", required=True, max_len=512)
    claimed_mime = _text(claimed_mime, name="file.mimeType", max_len=100).lower()
    request_mime = str(content_type or "").split(";", 1)[0].strip().lower()
    try:
        content_length = int(content_length)
    except Exception as exc:
        raise IntakeError("invalid Content-Length") from exc
    if content_length <= 0:
        raise IntakeError("empty image is not accepted")
    if content_length > MAX_FILE_BYTES:
        raise IntakeError("image exceeds maximum byte length")

    batch = _batch_dir(store.root, batch_id, create=True)
    final_path = batch / f"source-{source_id}.bin"
    meta_path = batch / f"source-{source_id}.json"
    tmp = batch / f".source-{source_id}.{os.getpid()}.{secrets.token_hex(4)}.tmp"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(tmp, flags, 0o600)
    digest = hashlib.sha256()
    remaining = content_length
    try:
        with os.fdopen(fd, "wb", closefd=True) as handle:
            while remaining:
                chunk = stream.read(min(1024 * 1024, remaining))
                if not chunk:
                    raise IntakeError("request body ended before Content-Length")
                remaining -= len(chunk)
                digest.update(chunk)
                handle.write(chunk)
            handle.flush()
            os.fsync(handle.fileno())
        image = _inspect_image_path(tmp)
        if claimed_mime and claimed_mime != image["mimeType"]:
            raise IntakeError(f"MIME type mismatch for {source_id}")
        if request_mime.startswith("image/") and request_mime != image["mimeType"]:
            raise IntakeError(f"HTTP Content-Type mismatch for {source_id}")
        descriptor = {
            "batchId": batch_id,
            "sourceId": source_id,
            "originalFilename": original_filename,
            "roles": roles,
            "sourceType": "route" if roles == ["route"] else "photo",
            "claimedMimeType": claimed_mime,
            "mimeType": image["mimeType"],
            "byteLength": content_length,
            "width": image["width"],
            "height": image["height"],
            "orientation": image["orientation"],
            "sha256": digest.hexdigest(),
        }

        if final_path.exists() or final_path.is_symlink():
            if final_path.is_symlink() or not final_path.is_file() or not meta_path.is_file():
                raise IntakeError("unsafe existing upload batch file")
            existing_sha = image_pipeline.sha256_file(final_path)
            try:
                existing_meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception as exc:
                raise IntakeError("existing upload batch metadata is corrupt") from exc
            if existing_sha != descriptor["sha256"] or existing_meta != descriptor:
                raise ImmutableInputError(f"upload batch source {source_id} changed immutable content")
            tmp.unlink()
            return {"ok": True, "idempotent": True, **descriptor}

        os.replace(tmp, final_path)
        final_path.chmod(0o600)
        _atomic_write_json(meta_path, descriptor)
        return {"ok": True, "idempotent": False, **descriptor}
    finally:
        if tmp.exists():
            tmp.unlink()


def _load_batch_files(store: RunStore, batch_id: str, file_order: list[str]) -> list[dict[str, Any]]:
    batch = _batch_dir(store.root, batch_id, create=False)
    if not batch.exists() or not batch.is_dir() or batch.is_symlink():
        raise IntakeError("upload batch does not exist")
    if not isinstance(file_order, list) or not file_order:
        raise IntakeError("fileOrder must be a non-empty array")
    if len(file_order) > MAX_FILES:
        raise IntakeError("too many source images")
    if len(file_order) != len(set(file_order)):
        raise IntakeError("fileOrder contains duplicate sourceId")

    files: list[dict[str, Any]] = []
    featured_count = thumbnail_count = 0
    for ordinal, value in enumerate(file_order):
        source_id = _text(value, name="fileOrder[]", required=True, max_len=64).lower()
        if not SAFE_SOURCE_ID_RE.fullmatch(source_id):
            raise IntakeError("fileOrder contains unsafe sourceId")
        data_path = batch / f"source-{source_id}.bin"
        meta_path = batch / f"source-{source_id}.json"
        if data_path.is_symlink() or meta_path.is_symlink() or not data_path.is_file() or not meta_path.is_file():
            raise IntakeError(f"upload batch source is incomplete: {source_id}")
        try:
            descriptor = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise IntakeError(f"upload metadata is invalid: {source_id}") from exc
        if not isinstance(descriptor, dict) or descriptor.get("sourceId") != source_id or descriptor.get("batchId") != batch_id:
            raise IntakeError(f"upload metadata mismatch: {source_id}")
        roles = normalize_roles(descriptor.get("roles"))
        featured_count += int("featured" in roles)
        thumbnail_count += int("thumbnail" in roles)
        size = data_path.stat().st_size
        sha = image_pipeline.sha256_file(data_path)
        if size != int(descriptor.get("byteLength") or -1) or sha != descriptor.get("sha256"):
            raise ImmutableInputError(f"upload batch source bytes changed: {source_id}")
        files.append({
            "ordinal": ordinal,
            "sourceId": source_id,
            "originalFilename": _text(descriptor.get("originalFilename"), name="file.originalFilename", required=True, max_len=512),
            "roles": roles,
            "sourceType": "route" if roles == ["route"] else "photo",
            "claimedMimeType": _text(descriptor.get("claimedMimeType"), name="file.mimeType", max_len=100),
            "mimeType": _text(descriptor.get("mimeType"), name="file.mimeType", required=True, max_len=100),
            "byteLength": size,
            "width": int(descriptor.get("width") or 0),
            "height": int(descriptor.get("height") or 0),
            "orientation": _text(descriptor.get("orientation"), name="file.orientation", required=True, max_len=32),
            "sha256": sha,
            "sourcePath": data_path,
        })
    if featured_count > 1:
        raise IntakeError("only one featured source is allowed")
    if thumbnail_count > 1:
        raise IntakeError("only one thumbnail source is allowed")
    return files


def _copy_or_verify_source(source: Path, target: Path, expected_sha256: str) -> None:
    if target.exists() or target.is_symlink():
        if target.is_symlink() or not target.is_file():
            raise IntakeError("unsafe existing source path")
        if image_pipeline.sha256_file(target) != expected_sha256:
            raise ImmutableInputError("existing source bytes differ from immutable source hash")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    target.parent.chmod(0o700)
    tmp = target.parent / f".{target.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(tmp, flags, 0o600)
    digest = hashlib.sha256()
    try:
        with source.open("rb") as src, os.fdopen(fd, "wb", closefd=True) as dst:
            while True:
                chunk = src.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
                dst.write(chunk)
            dst.flush()
            os.fsync(dst.fileno())
        if digest.hexdigest() != expected_sha256:
            raise IntakeError("source hash verification failed before durable rename")
        os.replace(tmp, target)
        target.chmod(0o600)
    finally:
        if tmp.exists():
            tmp.unlink()


def _cleanup_batch(store: RunStore, batch_id: str) -> None:
    batch = _batch_dir(store.root, batch_id, create=False)
    if batch.exists():
        if batch.is_symlink() or not batch.is_dir():
            raise IntakeError("unsafe upload batch path")
        shutil.rmtree(batch)


def finalize_uploaded_batch(store: RunStore, batch_id: str, payload: Any) -> dict[str, Any]:
    """Finalize a disk-backed upload batch into the existing durable run model."""
    if not isinstance(payload, dict):
        raise IntakeError("request body must be an object")
    source = _text(payload.get("source") or "form", name="source", required=True, max_len=32).lower()
    if source not in ALLOWED_SOURCES:
        raise IntakeError("source must be form or manual")
    trip = normalize_trip(payload.get("trip"))
    submission_key = _text(payload.get("submissionKey"), name="submissionKey", max_len=200)
    test_run = bool(payload.get("testRun", False))
    files = _load_batch_files(store, batch_id, payload.get("fileOrder"))

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
            for f in files
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

    all_descriptors = [descriptor(f) for f in files]
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
                "claimedMimeType": f["claimedMimeType"],
                "byteLength": f["byteLength"],
                "sha256": f["sha256"],
            }
            for f in files
        ],
    }

    run, created = store.create_or_verify_run(
        run_id=run_id,
        source=source,
        post_slug=post_slug,
        raw_input=raw_input,
        normalized_input=normalized_input,
        fingerprint=fingerprint,
        test_run=test_run,
    )
    if run["status"] not in {"RECEIVED", "NORMALIZED", "FAILED", "FILES_STORED"}:
        _cleanup_batch(store, batch_id)
        return {"runId": run_id, "created": created, "status": run["status"], "postSlug": run["post_slug"], "idempotent": True}

    if run["status"] == "RECEIVED":
        run = store.transition(run_id, "NORMALIZED", last_safe_status="NORMALIZED", detail="canonical binary-upload input normalized")
    elif run["status"] == "FAILED" and run.get("last_safe_status") in {None, "RECEIVED", "NORMALIZED"}:
        run = store.transition(run_id, "NORMALIZED", last_safe_status="NORMALIZED", error_message=None, detail="retry normalized immutable binary-upload input")

    run_dir = _safe_run_dir(store.root, run_id)
    source_dir = run_dir / "sources"
    manifest: list[dict[str, Any]] = []
    for f in files:
        target = source_dir / f"source-{f['sourceId']}.bin"
        _copy_or_verify_source(f["sourcePath"], target, f["sha256"])
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
        latest = store.transition(run_id, "FILES_STORED", last_safe_status="FILES_STORED", error_message=None, detail="all streamed immutable source files stored and hashed")
    _cleanup_batch(store, batch_id)
    return {"runId": run_id, "created": created, "status": latest["status"], "postSlug": latest["post_slug"], "idempotent": not created}
