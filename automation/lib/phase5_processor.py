#!/usr/bin/env python3
"""Phase 5 deterministic processing bridge and Phase 4 handoff."""
from __future__ import annotations

import base64
import json
import os
import re
import secrets
import shutil
from pathlib import Path
from typing import Any

import image_pipeline
from phase5_state import RunStore, StateError

SHA40_RE = re.compile(r"^[a-f0-9]{40}$")


class ProcessorError(RuntimeError):
    pass


def _json(value: str | None, fallback: Any) -> Any:
    try:
        return json.loads(value) if value else fallback
    except Exception:
        return fallback


def _safe_local_path(store: RunStore, relative_ref: str, *, require_file: bool = True) -> Path:
    if not isinstance(relative_ref, str) or not relative_ref or relative_ref.startswith(('/', '\\')) or '..' in relative_ref or '\\' in relative_ref:
        raise ProcessorError("unsafe internal source reference")
    root = store.root.resolve()
    path = (root / relative_ref).resolve()
    if os.path.commonpath([str(root), str(path)]) != str(root):
        raise ProcessorError("internal reference escaped state root")
    original = root / relative_ref
    if original.is_symlink():
        raise ProcessorError("symlink source references are forbidden")
    if require_file and (not path.exists() or not path.is_file()):
        raise ProcessorError("required durable file is missing")
    return path


def _verify_source(store: RunStore, source: dict[str, Any]) -> Path:
    path = _safe_local_path(store, source["safeRef"])
    if image_pipeline.sha256_file(path) != source["sha256"]:
        raise ProcessorError(f"durable source hash mismatch: {source['sourceId']}")
    return path


def _verify_processed_manifest(store: RunStore, manifest: dict[str, Any]) -> None:
    for output in manifest.get("outputs", []):
        image_pipeline.validate_repo_path(output["repoPath"])
        path = _safe_local_path(store, output["localRef"])
        data = path.read_bytes()
        if image_pipeline.sha256_bytes(data) != output["sha256"]:
            raise ProcessorError(f"processed SHA-256 mismatch: {output['repoPath']}")
        if image_pipeline.git_blob_sha(data) != output["gitBlobSha"]:
            raise ProcessorError(f"processed Git blob SHA mismatch: {output['repoPath']}")


def process_run(store: RunStore, run_id: str, *, inject_failure_after: int | None = None) -> dict[str, Any]:
    run = store.get_run(run_id)
    if run is None:
        raise StateError("run not found")
    persisted = _json(run.get("processed_image_manifest_json"), {})
    if run["status"] in {"IMAGES_PROCESSED", "GITHUB_IMAGES_WRITING", "GITHUB_IMAGES_COMPLETE"} and persisted.get("outputs"):
        if run["status"] != "GITHUB_IMAGES_COMPLETE":
            _verify_processed_manifest(store, persisted)
        return persisted
    if run["status"] == "FAILED" and run.get("last_safe_status") in {"IMAGES_PROCESSED", "GITHUB_IMAGES_WRITING"} and persisted.get("outputs"):
        _verify_processed_manifest(store, persisted)
        return persisted
    if run["status"] == "FAILED" and run.get("last_safe_status") != "FILES_STORED":
        raise StateError(f"failed run cannot resume image processing from {run.get('last_safe_status')}")
    if run["status"] not in {"FILES_STORED", "FAILED"}:
        raise StateError(f"run is not ready for image processing: {run['status']}")

    store.transition(run_id, "IMAGES_PROCESSING", last_safe_status="FILES_STORED", error_message=None,
                     detail="deterministic Pillow processing started")
    run_dir = (store.root / "runs" / run_id).resolve()
    tmp_dir = run_dir / f".processing-{secrets.token_hex(6)}"
    processed_dir = run_dir / "processed"
    try:
        source_manifest = _json(store.get_run(run_id).get("source_image_manifest_json"), [])
        if not source_manifest:
            raise ProcessorError("source image manifest is empty")
        sources = []
        for source in source_manifest:
            src_path = _verify_source(store, source)
            sources.append({
                "sourceId": source["sourceId"],
                "sourcePath": str(src_path),
                "sourceFilename": source["originalFilename"],
                "role": source["roles"][0],
                "derivativeRoles": source["roles"],
            })
        tmp_dir.mkdir(parents=True, exist_ok=False)
        tmp_dir.chmod(0o700)
        manifest = image_pipeline.build_manifest(run_id, run["post_slug"], sources, tmp_dir)
        processed_count = 0
        for output in manifest["outputs"]:
            info = image_pipeline.process_derivative(output["_sourcePath"], output["_localPath"], output["role"])
            output.update(info)
            output["status"] = "PROCESSED"
            processed_count += 1
            if inject_failure_after is not None and processed_count >= inject_failure_after:
                raise ProcessorError("synthetic mid-run processing failure")

        if processed_dir.exists():
            if processed_dir.is_symlink() or not processed_dir.is_dir():
                raise ProcessorError("unsafe existing processed directory")
            for output in manifest["outputs"]:
                existing = processed_dir / output["filename"]
                if not existing.is_file() or existing.is_symlink() or image_pipeline.sha256_file(existing) != output["sha256"]:
                    raise ProcessorError("existing processed output differs from deterministic retry")
            shutil.rmtree(tmp_dir)
        else:
            os.replace(tmp_dir, processed_dir)
            processed_dir.chmod(0o700)
            for child in processed_dir.iterdir():
                if child.is_file():
                    child.chmod(0o600)

        public = image_pipeline.public_manifest(manifest)
        stored_outputs = []
        for output in public["outputs"]:
            local_path = processed_dir / output["filename"]
            local_ref = local_path.relative_to(store.root).as_posix()
            output["localRef"] = local_ref
            stored_outputs.append(output)
        store.replace_outputs(run_id, public, stored_outputs)
        store.mark_sources_processed(run_id)
        store.transition(run_id, "IMAGES_PROCESSED", last_safe_status="IMAGES_PROCESSED", error_message=None,
                         detail="deterministic processed manifest persisted")
        return public
    except Exception as exc:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)
        try:
            store.fail(run_id, str(exc), last_safe_status="FILES_STORED")
        except Exception:
            pass
        raise


def prepare_phase4_handoff(store: RunStore, run_id: str, branch: str) -> dict[str, Any]:
    if branch != "Staging":
        raise ProcessorError("Phase 5 GitHub handoff is Staging-only")
    run = store.get_run(run_id)
    if run is None:
        raise StateError("run not found")
    manifest = _json(run.get("processed_image_manifest_json"), {})
    if run["status"] == "GITHUB_IMAGES_COMPLETE":
        return {
            "ok": True,
            "runId": run_id,
            "branch": "Staging",
            "githubNeeded": False,
            "commitSha": run["git_commit_sha"],
            "outputs": manifest.get("outputs", []),
        }
    if not manifest.get("outputs"):
        raise ProcessorError("processed manifest is not available")
    if run["status"] == "FAILED":
        if run.get("last_safe_status") not in {"IMAGES_PROCESSED", "GITHUB_IMAGES_WRITING"}:
            raise StateError(f"failed run cannot resume GitHub handoff from {run.get('last_safe_status')}")
        store.transition(run_id, "GITHUB_IMAGES_WRITING", last_safe_status="IMAGES_PROCESSED", error_message=None,
                         detail="retrying Phase 4 handoff")
    elif run["status"] == "IMAGES_PROCESSED":
        store.transition(run_id, "GITHUB_IMAGES_WRITING", last_safe_status="IMAGES_PROCESSED",
                         detail="Phase 4 handoff prepared")
    elif run["status"] != "GITHUB_IMAGES_WRITING":
        raise StateError(f"run is not ready for GitHub handoff: {run['status']}")

    _verify_processed_manifest(store, manifest)
    outputs = []
    for output in manifest["outputs"]:
        path = _safe_local_path(store, output["localRef"])
        outputs.append({
            "sourceId": output["sourceId"],
            "role": output["role"],
            "filename": output["filename"],
            "repoPath": output["repoPath"],
            "publicPath": output["publicPath"],
            "width": output["width"],
            "height": output["height"],
            "bytes": output["bytes"],
            "sha256": output["sha256"],
            "gitBlobSha": output["gitBlobSha"],
            "contentBase64": base64.b64encode(path.read_bytes()).decode("ascii"),
        })
    return {"ok": True, "runId": run_id, "branch": "Staging", "githubNeeded": True, "outputs": outputs}


def mark_github_failure(store: RunStore, run_id: str, message: str) -> dict[str, Any]:
    run = store.get_run(run_id)
    if run is None:
        raise StateError("run not found")
    if run["status"] == "GITHUB_IMAGES_COMPLETE":
        return run
    if run["status"] not in {"GITHUB_IMAGES_WRITING", "FAILED"}:
        raise StateError(f"cannot record GitHub failure from status {run['status']}")
    return store.fail(run_id, message, last_safe_status="IMAGES_PROCESSED")


def complete_phase4_handoff(store: RunStore, run_id: str, result: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(result, dict) or result.get("branch") != "Staging":
        raise ProcessorError("Phase 4 completion must report exact Staging branch")
    if result.get("action") not in {"COMMITTED", "ALREADY_EXISTS_SAME_CONTENT"}:
        raise ProcessorError("Phase 4 completion action is not successful")
    commit_sha = str(result.get("commitSha") or "")
    if not SHA40_RE.fullmatch(commit_sha):
        raise ProcessorError("Phase 4 completion commit SHA is invalid")
    run = store.get_run(run_id)
    if run is None:
        raise StateError("run not found")
    manifest = _json(run.get("processed_image_manifest_json"), {})
    expected = {o["repoPath"]: o for o in manifest.get("outputs", [])}
    reported = result.get("outputs")
    if not isinstance(reported, list) or len(reported) != len(expected):
        raise ProcessorError("Phase 4 completion output count mismatch")
    normalized = []
    for output in reported:
        if not isinstance(output, dict) or output.get("repoPath") not in expected:
            raise ProcessorError("Phase 4 completion contains unknown repo path")
        planned = expected[output["repoPath"]]
        if output.get("sha256") != planned["sha256"] or output.get("gitBlobSha") != planned["gitBlobSha"]:
            raise ProcessorError(f"Phase 4 completion hash mismatch: {output.get('repoPath')}")
        normalized.append({
            "repoPath": planned["repoPath"],
            "status": output.get("status") or "GITHUB_COMPLETE",
        })
    if run["status"] == "GITHUB_IMAGES_COMPLETE":
        return {"ok": True, "idempotent": True, "runId": run_id, "status": run["status"], "commitSha": run["git_commit_sha"]}
    updated = store.complete_github(run_id, commit_sha, normalized)
    return {"ok": True, "idempotent": False, "runId": run_id, "status": updated["status"], "commitSha": updated["git_commit_sha"]}


def cleanup_test_files(store: RunStore, run_id: str) -> dict[str, Any]:
    run = store.get_run(run_id)
    if run is None:
        raise StateError("run not found")
    if not bool(run["test_run"]):
        raise ProcessorError("cleanup endpoint is restricted to runs explicitly marked testRun")
    if run["status"] != "GITHUB_IMAGES_COMPLETE":
        raise ProcessorError("test files may only be purged after durable GitHub completion")
    run_dir = (store.root / "runs" / run_id).resolve()
    if os.path.commonpath([str(store.root.resolve()), str(run_dir)]) != str(store.root.resolve()):
        raise ProcessorError("unsafe run directory")
    for name in ("sources", "processed"):
        target = run_dir / name
        if target.exists():
            if target.is_symlink():
                raise ProcessorError("refusing to clean symlink directory")
            shutil.rmtree(target)
    store.set_cleanup_at(run_id)
    return {"ok": True, "runId": run_id, "filesPurged": True, "auditRecordRetained": True}
