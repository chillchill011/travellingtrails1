#!/usr/bin/env python3
"""Phase 6 state extension stored on the existing Phase 5 runs row."""
from __future__ import annotations
import json, re
from typing import Any
from phase5_state import RunStore, StateError, canonical_json, utc_now

PHASE6_STATUSES={"NOT_STARTED","TEXT_GENERATING","TEXT_GENERATED","TEXT_VALIDATED","DRAFT_WRITING","DRAFT_CREATED","FAILED"}
SHA40=re.compile(r"^[a-f0-9]{40}$")

def migrate(store: RunStore) -> None:
    with store.connect() as db:
        cols={r[1] for r in db.execute("PRAGMA table_info(runs)")}
        additions=[
            ("phase6_status","TEXT NOT NULL DEFAULT 'NOT_STARTED'"),
            ("phase6_last_safe_status","TEXT"),
            ("phase6_error_message","TEXT"),
            ("draft_markdown","TEXT"),
            ("draft_commit_sha","TEXT"),
            ("deepseek_call_count","INTEGER NOT NULL DEFAULT 0"),
        ]
        for name,ddl in additions:
            if name not in cols: db.execute(f"ALTER TABLE runs ADD COLUMN {name} {ddl}")

def _run(store: RunStore, run_id: str) -> dict[str,Any]:
    migrate(store); run=store.get_run(run_id)
    if run is None: raise StateError("run not found")
    return run

def _update(store: RunStore, run_id: str, **changes) -> dict[str,Any]:
    allowed={"phase6_status","phase6_last_safe_status","phase6_error_message","generated_json","validation_errors_json","post_path","draft_markdown","draft_commit_sha"}
    bad=set(changes)-allowed
    if bad: raise StateError("invalid Phase 6 state field")
    fields=["updated_at=?"]; values=[utc_now()]
    for k,v in changes.items():
        if k=="phase6_status" and v not in PHASE6_STATUSES: raise StateError("invalid Phase 6 status")
        if k in {"phase6_error_message"} and v is not None: v=str(v)[:4000]
        if k in {"generated_json","validation_errors_json"} and not isinstance(v,str): v=canonical_json(v)
        fields.append(k+"=?"); values.append(v)
    values.append(run_id)
    with store.connect() as db:
        db.execute("UPDATE runs SET "+",".join(fields)+" WHERE run_id=?",values)
        return dict(db.execute("SELECT * FROM runs WHERE run_id=?",(run_id,)).fetchone())

def prepare(store: RunStore, run_id: str) -> dict[str,Any]:
    run=_run(store,run_id)
    if run["status"]!="GITHUB_IMAGES_COMPLETE": raise StateError("Phase 6 requires GITHUB_IMAGES_COMPLETE")
    st=run.get("phase6_status") or "NOT_STARTED"
    if st=="DRAFT_CREATED": return view(store,run_id,action="NO_DRAFT_WRITE_NEEDED",idempotent=True)
    if st in {"TEXT_VALIDATED","DRAFT_WRITING"}: return view(store,run_id,action="WRITE_DRAFT",idempotent=False)
    if st=="TEXT_GENERATED": return view(store,run_id,action="VALIDATE_PERSISTED",idempotent=False)
    if st=="FAILED":
        safe=run.get("phase6_last_safe_status")
        if safe=="TEXT_VALIDATED": return view(store,run_id,action="WRITE_DRAFT",idempotent=False)
        if safe=="TEXT_GENERATED": return view(store,run_id,action="VALIDATE_PERSISTED",idempotent=False)
    _update(store,run_id,phase6_status="TEXT_GENERATING",phase6_last_safe_status=None,phase6_error_message=None)
    return view(store,run_id,action="CALL_DEEPSEEK",idempotent=False)

def persist_generated(store: RunStore, run_id: str, generated: dict[str,Any]) -> dict[str,Any]:
    run=_run(store,run_id)
    if run["status"]!="GITHUB_IMAGES_COMPLETE": raise StateError("Phase 6 requires GITHUB_IMAGES_COMPLETE")
    with store.connect() as db:
        db.execute("UPDATE runs SET generated_json=?,validation_errors_json='[]',phase6_status='TEXT_GENERATED',phase6_last_safe_status='TEXT_GENERATED',phase6_error_message=NULL,deepseek_call_count=deepseek_call_count+1,updated_at=? WHERE run_id=?",(canonical_json(generated),utc_now(),run_id))
    return view(store,run_id,action="VALIDATE_PERSISTED")

def persist_validation(store: RunStore, run_id: str, result: dict[str,Any]) -> dict[str,Any]:
    _run(store,run_id)
    errors=result.get("errors") or []
    if errors:
        # Schema/business-invalid model output is durable evidence, but not a safe
        # generation checkpoint. A retry may call DeepSeek again.
        _update(store,run_id,phase6_status="FAILED",phase6_last_safe_status=None,phase6_error_message="; ".join(map(str,errors)),validation_errors_json=errors)
        return view(store,run_id,action="VALIDATION_FAILED")
    _update(store,run_id,phase6_status="TEXT_VALIDATED",phase6_last_safe_status="TEXT_VALIDATED",phase6_error_message=None,validation_errors_json=[],post_path=result["postPath"],draft_markdown=result["markdown"])
    return view(store,run_id,action="WRITE_DRAFT")

def mark_writing(store: RunStore, run_id: str) -> dict[str,Any]:
    run=_run(store,run_id); st=run.get("phase6_status")
    if st=="DRAFT_CREATED": return view(store,run_id,action="NO_DRAFT_WRITE_NEEDED",idempotent=True)
    if st=="FAILED" and run.get("phase6_last_safe_status")!="TEXT_VALIDATED": raise StateError("failed Phase 6 run cannot resume draft write")
    if st not in {"TEXT_VALIDATED","DRAFT_WRITING","FAILED"}: raise StateError(f"Phase 6 draft write not ready from {st}")
    if not run.get("post_path") or not run.get("draft_markdown"): raise StateError("validated draft bytes are missing")
    _update(store,run_id,phase6_status="DRAFT_WRITING",phase6_last_safe_status="TEXT_VALIDATED",phase6_error_message=None)
    return view(store,run_id,action="WRITE_DRAFT")

def fail(store: RunStore, run_id: str, message: str) -> dict[str,Any]:
    run=_run(store,run_id); st=run.get("phase6_status") or "NOT_STARTED"
    safe=run.get("phase6_last_safe_status")
    if st in {"TEXT_GENERATED"}: safe="TEXT_GENERATED"
    elif st in {"TEXT_VALIDATED","DRAFT_WRITING"}: safe="TEXT_VALIDATED"
    _update(store,run_id,phase6_status="FAILED",phase6_last_safe_status=safe,phase6_error_message=message)
    return view(store,run_id,action="FAILED")

def complete(store: RunStore, run_id: str, result: dict[str,Any]) -> dict[str,Any]:
    run=_run(store,run_id)
    if run.get("phase6_status")=="DRAFT_CREATED": return view(store,run_id,action="NO_DRAFT_WRITE_NEEDED",idempotent=True)
    if result.get("branch")!="Staging": raise StateError("Phase 2 completion must report Staging")
    if result.get("action") not in {"CREATE","ALREADY_CREATED_SAME_CONTENT"}: raise StateError("Phase 2 completion action invalid")
    sha=str(result.get("commitSha") or "")
    if not SHA40.fullmatch(sha): raise StateError("Phase 2 completion commit SHA invalid")
    _update(store,run_id,phase6_status="DRAFT_CREATED",phase6_last_safe_status="DRAFT_CREATED",phase6_error_message=None,draft_commit_sha=sha)
    return view(store,run_id,action="DRAFT_CREATED",idempotent=result.get("action")!="CREATE")

def view(store: RunStore, run_id: str, *, action: str|None=None, idempotent: bool=False) -> dict[str,Any]:
    run=_run(store,run_id)
    def parse(name,default):
        try:return json.loads(run.get(name) or "")
        except Exception:return default
    return {"ok":True,"runId":run_id,"phase5Status":run["status"],"phase6Status":run.get("phase6_status") or "NOT_STARTED","phase6LastSafeStatus":run.get("phase6_last_safe_status"),"action":action,"idempotent":idempotent,"normalizedInput":parse("normalized_input_json",{}),"processedImageManifest":parse("processed_image_manifest_json",{}),"generated":parse("generated_json",None),"validationErrors":parse("validation_errors_json",[]),"postPath":run.get("post_path"),"markdown":run.get("draft_markdown"),"imageCommitSha":run.get("git_commit_sha"),"draftCommitSha":run.get("draft_commit_sha"),"deepseekCallCount":int(run.get("deepseek_call_count") or 0),"errorMessage":run.get("phase6_error_message")}
