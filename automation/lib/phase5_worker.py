#!/usr/bin/env python3
"""Internal-only Phase 5 HTTP worker.

No host port is published. Protected endpoints accept traffic only from the
configured Docker service identity (normally `n8n`) resolved on the shared
internal bridge network.
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import socket
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from phase5_ingestion import IntakeError, ingest_submission, run_public_view
from phase5_processor import (
    ProcessorError,
    cleanup_test_files,
    complete_phase4_handoff,
    mark_github_failure,
    prepare_phase4_handoff,
    process_run,
)
from phase5_state import ImmutableInputError, RunStore, StateError
from phase6_draft import Phase6Error, validate_and_assemble
from phase6_state import (
    complete as phase6_complete,
    fail as phase6_fail,
    mark_writing as phase6_mark_writing,
    migrate as migrate_phase6,
    persist_generated as phase6_persist_generated,
    persist_validation as phase6_persist_validation,
    prepare as phase6_prepare,
    view as phase6_view,
)
from phase7_review import (
    complete_notification as phase7_complete_notification,
    fail as phase7_fail,
    mark_notification_sending as phase7_mark_notification_sending,
    migrate as migrate_phase7,
    prepare as phase7_prepare,
    verify_live_deploy as phase7_verify_live_deploy,
    wait_for_live_deploy as phase7_wait_for_live_deploy,
    view as phase7_view,
)
from phase8_promotion import (
    approve_and_capture as phase8_approve_and_capture,
    complete_promotion as phase8_complete_promotion,
    fail as phase8_fail,
    mark_promoting as phase8_mark_promoting,
    mark_review_ready as phase8_mark_review_ready,
    migrate as migrate_phase8,
    verify_production_draft as phase8_verify_production_draft,
    wait_production_draft as phase8_wait_production_draft,
    verify_publication as phase8_verify_publication,
    view as phase8_view,
    waiting_run_ids as phase8_waiting_run_ids,
)


VERSION = "phase8-v1"
MAX_REQUEST_BYTES = 220 * 1024 * 1024
RUN_ROUTE_RE = re.compile(r"^/v1/runs/(tt-[0-9]{8}-[a-f0-9]{16})(/.*)?$")


class WorkerServer(ThreadingHTTPServer):
    def __init__(self, address, handler, *, store: RunStore, allowed_client: str):
        super().__init__(address, handler)
        self.store = store
        self.allowed_client = allowed_client

    def allowed_client_ips(self) -> set[str]:
        value = self.allowed_client.strip()
        try:
            return {str(ipaddress.ip_address(value))}
        except ValueError:
            pass
        ips: set[str] = set()
        for item in socket.getaddrinfo(value, None, type=socket.SOCK_STREAM):
            ips.add(item[4][0])
        return ips


class Handler(BaseHTTPRequestHandler):
    server: WorkerServer
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        sys.stderr.write("phase5-worker: " + (fmt % args) + "\n")

    def _json(self, status: int, payload: dict):
        body = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self) -> bool:
        try:
            allowed = self.server.allowed_client_ips()
        except Exception:
            return False
        return self.client_address[0] in allowed

    def _require_internal_client(self) -> bool:
        if self._authorized():
            return True
        self._json(403, {"ok": False, "error": "forbidden_client"})
        return False

    def _read_json(self) -> dict:
        length_raw = self.headers.get("Content-Length")
        if not length_raw:
            return {}
        try:
            length = int(length_raw)
        except ValueError as exc:
            raise IntakeError("invalid Content-Length") from exc
        if length < 0 or length > MAX_REQUEST_BYTES:
            raise IntakeError("request body exceeds limit")
        raw = self.rfile.read(length)
        try:
            parsed = json.loads(raw.decode("utf-8")) if raw else {}
        except Exception as exc:
            raise IntakeError("request body is not valid JSON") from exc
        if not isinstance(parsed, dict):
            raise IntakeError("request JSON must be an object")
        return parsed

    def _route(self):
        path = urlparse(self.path).path
        if path == "/health" and self.command == "GET":
            self._json(200, {"ok": True, "version": VERSION})
            return
        if not self._require_internal_client():
            return
        try:
            if path == "/v1/phase8/publish-waiting" and self.command == "GET":
                self._json(200, {"ok": True, "runIds": phase8_waiting_run_ids(self.server.store)})
                return
            if path == "/v1/ingest" and self.command == "POST":
                result = ingest_submission(self.server.store, self._read_json())
                self._json(200, {"ok": True, **result})
                return
            match = RUN_ROUTE_RE.fullmatch(path)
            if not match:
                self._json(404, {"ok": False, "error": "not found"})
                return
            run_id = match.group(1)
            suffix = match.group(2) or ""
            if suffix == "" and self.command == "GET":
                self._json(200, {"ok": True, "run": run_public_view(self.server.store, run_id)})
                return
            if suffix == "/process" and self.command == "POST":
                manifest = process_run(self.server.store, run_id)
                self._json(200, {"ok": True, "runId": run_id, "status": self.server.store.get_run(run_id)["status"], "manifest": manifest})
                return
            if suffix == "/github/prepare" and self.command == "POST":
                body = self._read_json()
                result = prepare_phase4_handoff(self.server.store, run_id, str(body.get("branch") or ""))
                self._json(200, result)
                return
            if suffix == "/github/complete" and self.command == "POST":
                result = complete_phase4_handoff(self.server.store, run_id, self._read_json())
                self._json(200, result)
                return
            if suffix == "/github/fail" and self.command == "POST":
                body = self._read_json()
                message = str(body.get("error") or "Phase 4 handoff failed")[:4000]
                run = mark_github_failure(self.server.store, run_id, message)
                self._json(200, {"ok": True, "runId": run_id, "status": run["status"]})
                return
            if suffix == "/cleanup-test-files" and self.command == "POST":
                self._json(200, cleanup_test_files(self.server.store, run_id))
                return
            if suffix == "/phase6/prepare" and self.command in {"GET", "POST"}:
                self._json(200, phase6_prepare(self.server.store, run_id))
                return
            if suffix == "/phase6" and self.command == "GET":
                self._json(200, phase6_view(self.server.store, run_id))
                return
            if suffix == "/phase6/generated" and self.command == "POST":
                body = self._read_json()
                generated = body.get("generated")
                if not isinstance(generated, dict):
                    raise Phase6Error("generated must be an object")
                self._json(200, phase6_persist_generated(self.server.store, run_id, generated))
                return
            if suffix == "/phase6/validate" and self.command == "POST":
                run = self.server.store.get_run(run_id)
                if run is None:
                    raise StateError("run not found")
                try:
                    generated = json.loads(run.get("generated_json") or "null")
                    normalized = json.loads(run.get("normalized_input_json") or "{}")
                    processed = json.loads(run.get("processed_image_manifest_json") or "{}")
                except Exception as exc:
                    raise Phase6Error("durable Phase 6 JSON is corrupt") from exc
                if not isinstance(generated, dict):
                    raise Phase6Error("durable generated_json is missing")
                result = validate_and_assemble(normalized, processed, generated)
                self._json(200, phase6_persist_validation(self.server.store, run_id, result))
                return
            if suffix == "/phase6/draft/prepare" and self.command == "POST":
                self._json(200, phase6_mark_writing(self.server.store, run_id))
                return
            if suffix == "/phase6/draft/fail" and self.command == "POST":
                body = self._read_json()
                message = str(body.get("error") or "Phase 2 handoff failed")
                self._json(200, phase6_fail(self.server.store, run_id, message))
                return
            if suffix == "/phase6/draft/complete" and self.command == "POST":
                self._json(200, phase6_complete(self.server.store, run_id, self._read_json()))
                return
            if suffix == "/phase7/prepare" and self.command in {"GET", "POST"}:
                self._json(200, phase7_prepare(self.server.store, run_id))
                return
            if suffix == "/phase7/deploy/verify" and self.command == "POST":
                self._json(200, phase7_verify_live_deploy(self.server.store, run_id))
                return
            if suffix == "/phase7/deploy/wait" and self.command == "POST":
                self._json(200, phase7_wait_for_live_deploy(self.server.store, run_id))
                return
            if suffix == "/phase7" and self.command == "GET":
                self._json(200, phase7_view(self.server.store, run_id))
                return
            if suffix == "/phase7/notification/prepare" and self.command == "POST":
                self._json(200, phase7_mark_notification_sending(self.server.store, run_id))
                return
            if suffix == "/phase7/notification/complete" and self.command == "POST":
                self._json(200, phase7_complete_notification(self.server.store, run_id))
                return
            if suffix == "/phase7/fail" and self.command == "POST":
                body = self._read_json()
                self._json(200, phase7_fail(self.server.store, run_id, str(body.get("error") or "Phase 7 failed")))
                return
            if suffix == "/phase8/review-ready" and self.command == "POST":
                self._json(200, phase8_mark_review_ready(self.server.store, run_id))
                return
            if suffix == "/phase8/approve" and self.command == "POST":
                body = self._read_json()
                self._json(200, phase8_approve_and_capture(self.server.store, run_id, body.get("approved") is True, str(body.get("expectedTitle") or "")))
                return
            if suffix == "/phase8/promote/prepare" and self.command == "POST":
                self._json(200, phase8_mark_promoting(self.server.store, run_id))
                return
            if suffix == "/phase8/promote/complete" and self.command == "POST":
                body = self._read_json()
                self._json(200, phase8_complete_promotion(self.server.store, run_id, str(body.get("commitSha") or "")))
                return
            if suffix == "/phase8/production-draft/verify" and self.command == "POST":
                self._json(200, phase8_verify_production_draft(self.server.store, run_id))
                return
            if suffix == "/phase8/production-draft/wait" and self.command == "POST":
                self._json(200, phase8_wait_production_draft(self.server.store, run_id))
                return
            if suffix == "/phase8/publication/verify" and self.command == "POST":
                self._json(200, phase8_verify_publication(self.server.store, run_id))
                return
            if suffix == "/phase8" and self.command == "GET":
                self._json(200, phase8_view(self.server.store, run_id))
                return
            if suffix == "/phase8/fail" and self.command == "POST":
                body = self._read_json()
                self._json(200, phase8_fail(self.server.store, run_id, str(body.get("error") or "Phase 8 failed")))
                return
            self._json(404, {"ok": False, "error": "not found"})
        except ImmutableInputError as exc:
            self._json(409, {"ok": False, "error": "immutable_input_mismatch", "message": str(exc)})
        except (IntakeError, ProcessorError, StateError, Phase6Error) as exc:
            status = 404 if str(exc) == "run not found" else 409
            self._json(status, {"ok": False, "error": exc.__class__.__name__, "message": str(exc)})
        except Exception as exc:
            self.log_message("unhandled error: %s", str(exc))
            self._json(500, {"ok": False, "error": "internal_error"})

    def do_GET(self):
        self._route()

    def do_POST(self):
        self._route()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--state-root", default=os.environ.get("TT_PHASE5_STATE_ROOT", "/data"))
    parser.add_argument("--allowed-client", default=os.environ.get("TT_PHASE5_ALLOWED_CLIENT", "n8n"))
    args = parser.parse_args()
    store = RunStore(args.state_root)
    migrate_phase6(store)
    migrate_phase7(store)
    migrate_phase8(store)
    server = WorkerServer((args.host, args.port), Handler, store=store, allowed_client=args.allowed_client)
    print(f"Travelling Trails Phase 5/6 worker {VERSION} listening on {args.host}:{args.port}; protected client={args.allowed_client}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
