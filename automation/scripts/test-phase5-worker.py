#!/usr/bin/env python3
import base64
import io
import json
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
WORKER = ROOT / "automation" / "lib" / "phase5_worker.py"


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def jpg_b64():
    b = io.BytesIO()
    Image.new("RGB", (900, 600), "orange").save(b, "JPEG", quality=90)
    return base64.b64encode(b.getvalue()).decode("ascii")


def request(url, *, payload=None):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(url, data=body, headers=headers, method="GET" if payload is None else "POST")
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.status, json.loads(r.read())


def wait_health(base):
    for _ in range(50):
        try:
            status, health = request(base + "/health")
            if status == 200 and health.get("ok"):
                return
        except Exception:
            time.sleep(0.1)
    raise AssertionError("worker did not become healthy")


def start(state, allowed_client):
    port = free_port()
    proc = subprocess.Popen(
        ["python3", str(WORKER), "--host", "127.0.0.1", "--port", str(port), "--state-root", str(state), "--allowed-client", allowed_client],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    base = f"http://127.0.0.1:{port}"
    wait_health(base)
    return proc, base


def stop(proc):
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    # Health is intentionally open, but protected endpoints reject any client not
    # matching the configured internal service identity/IP.
    proc, base = start(td / "blocked", "192.0.2.1")
    try:
        try:
            request(base + "/v1/ingest", payload={})
            raise AssertionError("forbidden client request accepted")
        except urllib.error.HTTPError as exc:
            assert exc.code == 403
    finally:
        stop(proc)

    proc, base = start(td / "state", "127.0.0.1")
    try:
        payload = {
            "source": "manual",
            "trip": {
                "date": "2026-10-08", "author": "aniket", "destination": "Worker HTTP Test", "duration": "",
                "rawNotes": "synthetic", "routeNotes": "", "costNotes": "", "gearNotes": "", "mustInclude": []
            },
            "files": [
                {"sourceId": "featured-1", "originalFilename": "../../untrusted.jpg", "mimeType": "image/jpeg", "roles": ["featured", "thumbnail"], "contentBase64": jpg_b64()}
            ],
        }
        _, ingested = request(base + "/v1/ingest", payload=payload)
        rid = ingested["runId"]
        assert ingested["status"] == "FILES_STORED"
        _, processed = request(base + f"/v1/runs/{rid}/process", payload={})
        assert processed["status"] == "IMAGES_PROCESSED"
        _, handoff = request(base + f"/v1/runs/{rid}/github/prepare", payload={"branch": "Staging"})
        assert handoff["githubNeeded"] is True and len(handoff["outputs"]) == 2
        assert all("contentBase64" in x for x in handoff["outputs"])
    finally:
        stop(proc)

print("PASS phase5 internal-client worker HTTP bridge")
