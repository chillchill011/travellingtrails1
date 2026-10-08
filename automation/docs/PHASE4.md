# Phase 4 — Image manifest and safe Staging upload

Phase 4 establishes the deterministic image boundary. Production `main` remains read-only and no article Markdown is created.

## Canonical manifest

Each run records `runId`, sanitized `postSlug`, `sourceImages[]`, and `outputs[]`. Source records contain source ID/name/path, MIME type, dimensions, orientation, byte count, SHA-256, and role. Output records contain source ID, role, deterministic filename, `src/assets/images/<filename>` repo path, `/assets/images/<filename>` public path, dimensions, bytes, SHA-256, Git blob SHA, and status.

Statuses move from `PLANNED` to `PROCESSED`; the GitHub boundary reports `UPLOADED` or `ALREADY_EXISTS`/`ALREADY_EXISTS_SAME_CONTENT`.

## Filename algorithm

`postSlug` is Unicode-normalized to ASCII, lowercased, non-alphanumeric runs become one hyphen, and empty slugs are rejected. Uploaded source filenames never become repository destinations.

Outputs are deterministic JPEGs:

- `<post-slug>-featured.jpg`
- `<post-slug>-thumbnail.jpg`
- `<post-slug>-01.jpg`, `<post-slug>-02.jpg`, ...
- `<post-slug>-route-01.jpg`, ...

Only `src/assets/images/[a-z0-9-]+.jpg` is accepted. Leading slashes, path traversal, backslashes, subdirectories, unsafe characters, and duplicate output paths are rejected.

## Derivative rules

The repo-local processor is `automation/lib/image_pipeline.py` and uses Pillow already installed on the host.

- Featured: preserve aspect ratio, maximum width 1600 px, never upscale.
- Thumbnail: center-crop to 400:267 ratio, maximum 400 x 267, never upscale.
- Gallery: center-crop to 800:533 ratio, maximum 800 x 533, never upscale.
- Route: preserve the full image aspect ratio, maximum width 1600 px, never crop map content.
- Output: JPEG quality 85, optimized/progressive, EXIF orientation applied, metadata not copied.

No image content inference, alt text, captions, or location inference occurs in Phase 4.

## GitHub/idempotency contract

Branch is hardcoded/guarded as `Staging`. Before writing each output, remote state is checked. Missing path means `CREATE`; matching Git blob SHA means idempotent success; a different blob at the same path is a hard collision and is never overwritten.

The n8n workflow creates missing Git blobs, constructs one tree based on the current Staging tree, creates one commit, and fast-forwards `refs/heads/Staging` with `force:false`. A concurrent branch move therefore fails instead of being force-overwritten. Exact retries reuse the same deterministic paths and blob SHAs.

For a future persistent run record store at least: runId, post slug, source SHA-256 values, output SHA-256 values, Git blob SHAs, repo paths, public paths, current status, and final Git commit SHA.

## n8n workflow

- ID: `TTPhase4ImageUpload01`
- Name: `Travelling Trails - Phase 4 Staging Image Upload`
- State: inactive
- Credential: `GitHub - Travelling Trails`

The current n8n container has Node.js but no Python/ImageMagick and does not mount this repository. To avoid a container reconfiguration/restart or a new heavy image stack in Phase 4, deterministic derivative generation remains in the tested repo-local Pillow helper. The n8n workflow accepts already-processed normalized outputs (including base64 bytes and verified hashes), validates the image manifest boundary, performs collision/idempotency checks, and executes the atomic Git tree/commit/ref update. Phase 5 ingestion must either mount/expose this helper safely or add an equivalent deterministic image-processing worker before invoking this workflow.

## Integration test and cleanup

Use only synthetic local fixtures. Generate the four deterministic outputs for slug `phase-4-integration-test`, confirm no destination exists on `origin/Staging`, copy them into `src/assets/images/`, commit and push only to `Staging`, fetch and verify remote bytes/hashes, verify an exact retry resolves to already-existing same content, and verify altered bytes at an existing path resolve to collision without a write. Confirm `origin/main` is unchanged and no Markdown references the files.

After verification, delete all temporary integration images in a separate Staging cleanup commit and push it. Confirm no `phase-4-integration-test*.jpg` paths remain remotely.

## Tests

Run:

- `node automation/scripts/test-text-pipeline.js`
- `node automation/scripts/test-github-draft.js`
- `python3 automation/scripts/test-image-pipeline.py`
- `node automation/scripts/test-github-image.js`
- `git diff --check`
- `ELEVENTY_ENV=production NODE_ENV=production npm run build`

## Known limitations / Phase 5 handoff

Phase 4 does not collect Telegram/form images, persist run state in a database, generate image descriptions, or create article Markdown. The n8n container cannot directly execute the host Pillow helper without an explicit safe integration point. Phase 5 should add normalized photo intake and durable run-state recovery while preserving this deterministic manifest, filename, hash, collision, and Staging-only contract.
