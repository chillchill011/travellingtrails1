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

VERSION = "phase5-v1"
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
            self._json(404, {"ok": False, "error": "not found"})
        except ImmutableInputError as exc:
            self._json(409, {"ok": False, "error": "immutable_input_mismatch", "message": str(exc)})
        except (IntakeError, ProcessorError, StateError) as exc:
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
    server = WorkerServer((args.host, args.port), Handler, store=store, allowed_client=args.allowed_client)
    print(f"Travelling Trails Phase 5 worker {VERSION} listening on {args.host}:{args.port}; protected client={args.allowed_client}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
