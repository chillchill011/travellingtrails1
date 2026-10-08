#!/usr/bin/env python3
import base64
import copy
import io
import json
import tempfile
from pathlib import Path

from PIL import Image

import sys
sys.dont_write_bytecode = True
LIB = Path(__file__).resolve().parents[1] / "lib"
sys.path.insert(0, str(LIB))

from phase5_ingestion import ImmutableInputError, ingest_submission, run_public_view
from phase5_processor import ProcessorError, cleanup_test_files, complete_phase4_handoff, prepare_phase4_handoff, process_run
from phase5_state import RunStore


def image_b64(size, color, fmt="JPEG"):
    b = io.BytesIO()
    Image.new("RGB", size, color).save(b, fmt, quality=91)
    return base64.b64encode(b.getvalue()).decode("ascii")


def payload(*, test=False, destination="Phase 5 Unit Test"):
    return {
        "source": "manual",
        "testRun": test,
        "trip": {
            "date": "2026-10-08",
            "author": "aniket",
            "destination": destination,
            "duration": "1 day",
            "rawNotes": "Synthetic Phase 5 notes only.",
            "routeNotes": "Synthetic route notes.",
            "costNotes": "",
            "gearNotes": "",
            "mustInclude": ["synthetic fixture"],
        },
        "files": [
            {"sourceId": "featured-1", "originalFilename": "../dup.jpg", "mimeType": "image/jpeg", "roles": ["featured", "thumbnail"], "contentBase64": image_b64((1800, 900), "red")},
            {"sourceId": "gallery-1", "originalFilename": "/absolute/dup.jpg", "mimeType": "image/jpeg", "roles": ["gallery"], "contentBase64": image_b64((1000, 1500), "green")},
            {"sourceId": "gallery-2", "originalFilename": "C:\\unsafe\\фото✨.jpg", "mimeType": "image/jpeg", "roles": ["gallery"], "contentBase64": image_b64((900, 600), "yellow")},
            {"sourceId": "route-1", "originalFilename": "dup.jpg", "mimeType": "image/jpeg", "roles": ["route"], "contentBase64": image_b64((600, 1200), "blue")},
            {"sourceId": "unused-1", "originalFilename": "dup.jpg", "mimeType": "image/jpeg", "roles": ["unused"], "contentBase64": image_b64((300, 300), "white")},
        ],
    }


with tempfile.TemporaryDirectory() as td:
    root = Path(td) / "state"
    store = RunStore(root)
    p = payload(test=True)

    # A. Normal ingestion and path containment.
    first = ingest_submission(store, p)
    assert first["status"] == "FILES_STORED"
    run_id = first["runId"]
    assert run_id.startswith("tt-20261008-")
    view = run_public_view(store, run_id)
    assert view["status"] == "FILES_STORED"
    assert len(view["sourceImageManifest"]) == 5
    source_refs = [x["safeRef"] for x in view["sourceImageManifest"]]
    assert len(source_refs) == len(set(source_refs))
    for ref in source_refs:
        target = (root / ref).resolve()
        assert str(target).startswith(str(root.resolve()))
        assert ".." not in ref and "\\" not in ref
    assert all("dup.jpg" not in ref and "фото" not in ref for ref in source_refs)
    assert all(len(x["sha256"]) == 64 for x in view["sourceImageManifest"])
    featured = next(x for x in view["sourceImageManifest"] if x["sourceId"] == "featured-1")
    assert featured["roles"] == ["featured", "thumbnail"]

    manifest = process_run(store, run_id)
    assert store.get_run(run_id)["status"] == "IMAGES_PROCESSED"
    names = [x["filename"] for x in manifest["outputs"]]
    assert names[0].endswith("-featured.jpg") and names[1].endswith("-thumbnail.jpg")
    assert len(names) == 5  # featured + thumbnail + two gallery + route
    assert all(x["status"] == "PROCESSED" and x["sha256"] and x["gitBlobSha"] for x in manifest["outputs"])

    # Persistence across a fresh RunStore instance (restart boundary).
    reopened = RunStore(root)
    assert reopened.get_run(run_id)["status"] == "IMAGES_PROCESSED"
    assert reopened.get_run(run_id)["input_fingerprint"] == store.get_run(run_id)["input_fingerprint"]

    # B. Exact retry reuses run and processed outputs.
    retry_ingest = ingest_submission(reopened, p)
    assert retry_ingest["runId"] == run_id and retry_ingest["idempotent"] is True
    before_files = sorted(x.relative_to(root).as_posix() for x in root.rglob("*") if x.is_file())
    retry_manifest = process_run(reopened, run_id)
    after_files = sorted(x.relative_to(root).as_posix() for x in root.rglob("*") if x.is_file())
    assert [x["sha256"] for x in retry_manifest["outputs"]] == [x["sha256"] for x in manifest["outputs"]]
    assert before_files == after_files

    # D. Same explicit runId with changed immutable source must fail.
    changed = copy.deepcopy(p)
    changed["runId"] = run_id
    changed["files"][0]["contentBase64"] = image_b64((1800, 900), "purple")
    try:
        ingest_submission(reopened, changed)
        raise AssertionError("changed immutable source accepted under same runId")
    except ImmutableInputError:
        pass

    # F. Wrong branch must fail before GitHub handoff.
    try:
        prepare_phase4_handoff(reopened, run_id, "main")
        raise AssertionError("main branch handoff accepted")
    except ProcessorError as exc:
        assert "Staging-only" in str(exc)

    # Prepare/complete the durable GitHub state using a synthetic Phase 4 result.
    handoff = prepare_phase4_handoff(reopened, run_id, "Staging")
    assert handoff["githubNeeded"] is True and all(x["contentBase64"] for x in handoff["outputs"])
    fake = {
        "ok": True,
        "runId": run_id,
        "branch": "Staging",
        "action": "COMMITTED",
        "commitSha": "a" * 40,
        "outputs": [
            {"repoPath": x["repoPath"], "sha256": x["sha256"], "gitBlobSha": x["gitBlobSha"], "status": "UPLOADED"}
            for x in handoff["outputs"]
        ],
    }
    done = complete_phase4_handoff(reopened, run_id, fake)
    assert done["status"] == "GITHUB_IMAGES_COMPLETE"
    exact = prepare_phase4_handoff(reopened, run_id, "Staging")
    assert exact["githubNeeded"] is False and exact["commitSha"] == "a" * 40

    # Test-only original/processed cleanup keeps the durable audit row/manifests.
    cleaned = cleanup_test_files(reopened, run_id)
    assert cleaned["auditRecordRetained"] is True
    assert reopened.get_run(run_id)["cleanup_at"]
    assert run_public_view(reopened, run_id)["processedImageManifest"]["outputs"]

with tempfile.TemporaryDirectory() as td:
    # C. Mid-run failure persists FAILED + last safe boundary, retry resumes cleanly.
    store = RunStore(Path(td) / "state")
    p = payload(destination="Phase 5 Recovery Test")
    result = ingest_submission(store, p)
    rid = result["runId"]
    try:
        process_run(store, rid, inject_failure_after=1)
        raise AssertionError("synthetic failure was not raised")
    except ProcessorError as exc:
        assert "synthetic" in str(exc)
    failed = store.get_run(rid)
    assert failed["status"] == "FAILED" and failed["last_safe_status"] == "FILES_STORED"
    assert not (Path(td) / "state" / "runs" / rid / "processed").exists()
    recovered = process_run(store, rid)
    assert recovered["outputs"] and store.get_run(rid)["status"] == "IMAGES_PROCESSED"
    assert len([x for x in (Path(td) / "state" / "runs" / rid / "processed").iterdir() if x.is_file()]) == len(recovered["outputs"])

with tempfile.TemporaryDirectory() as td:
    # Explicitly separate thumbnail source is supported deterministically.
    store = RunStore(Path(td) / "state")
    p = payload(destination="Separate Thumbnail Test")
    p["files"][0]["roles"] = ["featured"]
    p["files"].insert(1, {"sourceId": "thumbnail-1", "originalFilename": "thumb.jpeg", "mimeType": "image/jpeg", "roles": ["thumbnail"], "contentBase64": image_b64((500, 900), "black")})
    rid = ingest_submission(store, p)["runId"]
    m = process_run(store, rid)
    roles = [x["role"] for x in m["outputs"]]
    assert roles.count("featured") == 1 and roles.count("thumbnail") == 1
    thumb = next(x for x in m["outputs"] if x["role"] == "thumbnail")
    assert thumb["sourceId"] == "thumbnail-1"

print("PASS phase5 ingestion/state/recovery")
