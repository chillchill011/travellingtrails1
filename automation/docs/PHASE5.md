# Phase 5 — Ingestion and durable run state

Phase 5 adds the durable boundary between a user submission and the already-tested Phase 4 Staging image/GitHub boundary. It does not generate or publish an article. Production `main`, production Netlify configuration, Decap's `main` branch setting, and Phase 1/2/4 behavior remain unchanged.

## Architecture

```text
n8n Form Trigger (or manual synthetic test)
  -> normalize form fields + binary uploads into canonical JSON
  -> Phase 5 worker: durable ingest + immutable original storage
  -> Phase 5 worker: deterministic Pillow processing
  -> Phase 5 worker: persist processed manifest / prepare Phase 4 handoff
  -> existing TTPhase4ImageUpload01 sub-workflow
  -> Phase 5 worker: persist GitHub completion
  -> STOP
```

The Phase 5 worker is a small Python service managed as its own Portainer stack. Its compose file is `automation/phase5/docker-compose.yml` and its image is built from `automation/phase5/Dockerfile`.

It does not publish a host port. It joins the already-existing external Docker network `n8n_default`; the network definition and existing n8n container are not changed or recreated. Protected worker endpoints accept requests only when the source IP resolves to the existing Docker service name `n8n`. `/health` is the only unauthenticated endpoint and exposes no run data. The container is non-root, read-only apart from `/data`, drops all Linux capabilities, uses `no-new-privileges`, and has no Docker socket.

## Canonical input contract

After Form-specific names have been normalized, the worker receives an object shaped like:

```json
{
  "source": "form",
  "submissionKey": "",
  "trip": {
    "date": "2026-10-08",
    "author": "aniket",
    "destination": "",
    "duration": "",
    "rawNotes": "",
    "routeNotes": "",
    "costNotes": "",
    "gearNotes": "",
    "mustInclude": []
  },
  "files": [
    {
      "sourceId": "featured-1",
      "originalFilename": "user supplied name.jpg",
      "mimeType": "image/jpeg",
      "roles": ["featured", "thumbnail"],
      "contentBase64": "..."
    }
  ]
}
```

`source` is `form` or `manual` in Phase 5. The durable normalized object stored in SQLite is source-agnostic and follows the project model:

```json
{
  "runId": "tt-20261008-...",
  "source": "form",
  "trip": { "...": "..." },
  "photos": [],
  "routeImages": [],
  "testRun": false
}
```

Raw image bytes are never stored in SQLite. The database stores metadata, hashes and safe internal references; originals live in the private run directory.

## Run ID and immutable input

The run ID is deterministic:

```text
tt-YYYYMMDD-<first 16 hex of canonical input fingerprint>
```

The fingerprint covers normalized trip data, source IDs/order, submitted filename metadata, deterministic roles, actual image MIME type, byte length and SHA-256, plus the optional `submissionKey`.

Therefore an exact retry after an n8n/workflow restart regenerates the same `runId`. If a caller explicitly retries an existing `runId` with different immutable bytes or metadata, ingestion fails with an immutable-input error. An intentionally separate but otherwise identical submission can use a different `submissionKey`.

## Stable post slug

Phase 5 does not depend on an AI-generated title. It creates and persists the media slug exactly once as:

```text
<date>-<destination>-<first 8 fingerprint hex>
```

The value is normalized through the existing `image_pipeline.sanitize_slug()` function and never changes later for that run. The final article title/permalink may differ; media destinations remain stable and are not silently renamed.

## Source roles

Allowed deterministic source role combinations are:

- `featured`
- `thumbnail`
- `featured + thumbnail`
- `gallery`
- `route`
- `unused`

The n8n Form has separate optional thumbnail, gallery, route and unused inputs. If no separate thumbnail is supplied, the featured source is explicitly recorded with roles `["featured", "thumbnail"]`. No map/route role is inferred from image appearance.

User-supplied filenames are metadata only and never become filesystem or GitHub destinations.

## Source record

Every stored original has at least:

```text
sourceId
originalFilename
safeRef
sourceType
roles
mimeType
byteLength
width
height
orientation
sha256
processingStatus
```

The worker derives MIME type and dimensions from decoded image bytes using Pillow and rejects a conflicting claimed MIME type.

## Durable store

Phase 5 uses a dedicated application SQLite database rather than n8n internal tables:

```text
/home/aniket/nas-stack/travellingtrails-phase5/phase5.sqlite3
```

Run files live below:

```text
/home/aniket/nas-stack/travellingtrails-phase5/runs/<runId>/sources/
/home/aniket/nas-stack/travellingtrails-phase5/runs/<runId>/processed/
```

The host directory is private (`0700`). Source files use generated names such as `source-featured-1.bin`, not submitted filenames. Files are written to a same-directory temporary file, fsynced, hash-verified, then atomically renamed. Existing immutable sources must have the exact recorded SHA-256. Symlinks and path escapes are rejected.

SQLite runs in WAL mode and contains:

### `runs`

```text
run_id (PK)
source
status
last_safe_status
created_at
updated_at
post_slug
post_path
git_commit_sha
raw_input_json
normalized_input_json
generated_json
validation_errors_json
source_image_manifest_json
processed_image_manifest_json
error_message
input_fingerprint (UNIQUE)
test_run
cleanup_at
```

`generated_json` and `post_path` are intentionally unused/null in Phase 5 but retained for the later text/draft phases.

### `source_images`

One durable row per submitted original, including safe reference, roles, dimensions, MIME type, byte length, SHA-256 and processing state.

### `processed_images`

One durable row per deterministic output, including source ID, role, filename, repository/public/local references, dimensions, bytes, SHA-256, Git blob SHA and write status.

### `status_history`

Append-only transition history for recovery/audit.

This store is deliberately separate from n8n's own `database.sqlite`; Phase 5 never creates application tables inside n8n's database.

## Status transitions

Normal progression is:

```text
RECEIVED
  -> NORMALIZED
  -> FILES_STORED
  -> IMAGES_PROCESSING
  -> IMAGES_PROCESSED
  -> GITHUB_IMAGES_WRITING
  -> GITHUB_IMAGES_COMPLETE
```

`IMAGES_PROCESSING` and `GITHUB_IMAGES_WRITING` are transient states. `last_safe_status` records the last durable restart boundary. Errors transition to `FAILED` with a bounded `error_message` while preserving that safe boundary.

A processing retry from `FAILED + FILES_STORED` reruns only deterministic image processing. A GitHub retry from `FAILED + IMAGES_PROCESSED` or an interrupted `GITHUB_IMAGES_WRITING` reuses the persisted processed manifest and bytes. A run already at `GITHUB_IMAGES_COMPLETE` returns an idempotent no-write result.

## Processor integration

`automation/lib/image_pipeline.py` remains the one deterministic transformation implementation. Phase 5 only orchestrates it.

The worker calls the existing functions for source inspection, filename/path validation and derivative creation. Phase 5 extends the manifest helper only enough to allow an explicitly separate thumbnail source while retaining the legacy Phase 4 behavior where a plain `featured` source produces featured + thumbnail derivatives.

Processing uses a run-local temporary directory. The complete processed directory is atomically renamed into place only after all outputs succeed. A mid-run processor failure deletes the temporary derivative directory, records `FAILED` with `last_safe_status=FILES_STORED`, and leaves immutable originals available for retry.

Derivative rules remain the Phase 4 contract:

```text
featured  max width 1600; preserve aspect ratio; never upscale
thumbnail center crop 400:267; max 400x267; never upscale
gallery   center crop 800:533; max 800x533; never upscale
route     preserve full image; max width 1600; never crop; never upscale
JPEG      quality 85, optimized/progressive, EXIF orientation applied, metadata not copied
```

## Phase 4 handoff

The worker's prepare boundary accepts only branch `Staging`. Any other branch fails before returning GitHub-write material.

For each processed output it returns the existing Phase 4 fields:

```text
repoPath
publicPath
sha256
gitBlobSha
contentBase64
```

n8n calls the existing `TTPhase4ImageUpload01` sub-workflow. Phase 5 does not duplicate Phase 4 Git tree/commit/ref logic. Phase 4 remains responsible for:

```text
exact Staging guard
remote existence check
same blob SHA -> idempotent success
different existing blob -> collision failure
one atomic tree/commit for missing files
non-force fast-forward ref update
concurrent Staging movement failure
```

After Phase 4 succeeds, Phase 5 verifies the returned branch, action, commit SHA, repo paths, SHA-256 values and Git blob SHAs against the persisted processed manifest before recording `GITHUB_IMAGES_COMPLETE`.

If the sub-workflow reports an error, the Phase 5 n8n workflow records a durable GitHub failure and then fails the n8n execution instead of weakening the guard.

## Original-file retention and cleanup

Production source originals are never automatically deleted in Phase 5. They become eligible for cleanup only after:

1. status is `GITHUB_IMAGES_COMPLETE`;
2. processed/source manifests and Git commit SHA have been durably recorded; and
3. the chosen operational retention window has passed.

A practical initial retention target is 14 days, but no automatic production purge is enabled in Phase 5.

Synthetic runs explicitly created with `testRun: true` may use the internal cleanup endpoint immediately after `GITHUB_IMAGES_COMPLETE`. It removes only that run's local `sources/` and `processed/` directories, marks the source rows `PURGED`, and retains the SQLite run/manifests/status history as audit evidence. The endpoint refuses non-test runs.

## Backup and recovery

Before Phase 5 n8n mutation, a normal online backup of n8n's SQLite database is still required under the established Travelling Trails lock.

Phase 5 application state can be backed up with:

```text
automation/scripts/backup-phase5-state.sh
```

It uses SQLite's online backup API for `phase5.sqlite3` and archives the immutable/atomically-created `runs/` tree into the private Travelling Trails backup root, then writes SHA-256 checksums.

Recovery is intentionally simple: restore `phase5.sqlite3` and `runs/` together into the dedicated Phase 5 state directory while the Phase 5 worker is stopped, verify `SHA256SUMS`, then start the worker through Portainer. On the next retry, source/output hashes are revalidated before any later boundary is continued.

## n8n workflow

```text
ID:    TTPhase5Ingestion01
Name:  Travelling Trails - Phase 5 Ingestion and Run State
State: inactive after testing
```

Template:

```text
automation/n8n/phase5-ingestion-run-state-workflow.json
```

The Form uses n8n user authentication and requires workflow execute permission. The workflow also has a manual trigger used only for controlled synthetic integration testing; its payload is supplied through the executing process environment and is not committed/pinned in the workflow.

No DeepSeek call exists in the Phase 5 workflow.

## Tests

Phase 5 tests:

```text
python3 automation/scripts/test-phase5-ingestion.py
python3 automation/scripts/test-phase5-worker.py
```

They cover stable IDs, SQLite restart persistence, source hashes, unsafe submitted filenames as metadata-only input, duplicate submitted names, role mapping, separate thumbnail input, exact retry, changed immutable source rejection, mid-run failure/recovery, wrong-branch rejection, deterministic manifest reuse, GitHub completion persistence and test-only cleanup.

Existing Phase 1/2/4 tests remain required unchanged.

## Known limitations

- The V1 Form normalizer base64-encodes n8n binary items for the internal worker request. This is simple and reliable for a single-user workflow but is memory-heavier than streaming multipart intake. The worker caps each source at 40 MiB, at most 40 source files, and the request body at 220 MiB.
- Worker access control relies on Docker bridge source identity (`n8n` DNS -> current container IP), not a cryptographic application token. There is no host/public port. This is suitable for the current single-host trusted-container boundary; a later phase may add a managed shared secret or mTLS if the trust boundary expands.
- Production originals are intentionally not auto-purged yet.
- Phase 5 does not generate alt text/captions, infer locations, call DeepSeek, create Markdown, change `draft`, publish, or merge to `main`.

## Phase 6 handoff

Phase 6 may consume only durable Phase 5 outputs after `GITHUB_IMAGES_COMPLETE` (or deliberately earlier if its design explicitly requires it):

```text
normalized_input_json
source_image_manifest_json
processed_image_manifest_json
post_slug
git_commit_sha
```

The next phase should connect these durable inputs to the already-tested Phase 1 generation/validation contract and Phase 2 Staging draft-write boundary. It must preserve the stored media `post_slug`/paths, keep `draft: true`, avoid regenerating already-validated image outputs, and continue to treat `main`/production as untouched until a separate approved publishing phase.
