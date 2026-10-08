# Phase 7 — Safe Staging Review Handoff

> **STAGING**
> GitHub branch = `Staging`
> Netlify project = `devtravtes`
> Netlify site ID = `bb8c325b-9562-4952-8613-439ca95dc9e0`
> URL = `https://devtravtes.netlify.app/`
>
> **PRODUCTION**
> GitHub branch = `main`
> Netlify project = `travellingtrails1`
> Netlify site ID = `edd2477f-24f5-4005-a05c-f0310f1efe11`
> URL = `https://travellingtrails.in/`

Never infer environment from Netlify's `context: production` label. `devtravtes + Staging` is staging.

## Purpose

Phase 7 extends a Phase 6 `DRAFT_CREATED` run into a durable, retry-safe staging review handoff. It verifies that the draft commit is contained by GitHub `Staging`, verifies a ready deploy from the `devtravtes` site, HTTP-checks the direct staging preview, creates one canonical review payload, and stops. `draft:true` is mandatory; Phase 7 never publishes or writes to `main`.

## Preflight baseline

At Phase 7 start on 2026-10-08:

- `origin/Staging`: `8e09c45326d28ecbe120c079afd79736af459b8a`
- `origin/main`: `e4a2f9eb75ea3e7e9de3268d9cbf59c7602cb5dc`
- `https://devtravtes.netlify.app/`: HTTP 200
- `https://travellingtrails.in/`: HTTP 200
- `devtravtes` latest ready deploy: branch `Staging`, commit `8e09c45326d28ecbe120c079afd79736af459b8a`
- `travellingtrails1` latest ready deploy: branch `main`, commit `e4a2f9eb75ea3e7e9de3268d9cbf59c7602cb5dc`
- n8n: `2.40.7`

Pre-mutation backups:

- n8n: `/mnt/storage/travellingtrails-backups/20261008T180037Z-phase1`
- durable state: `/mnt/storage/travellingtrails-backups/20261008T180132Z-phase5-state`

Both SQLite databases passed `PRAGMA integrity_check` through Python's SQLite API.

## Decap branch isolation

The source CMS config remains production-safe with `backend.branch: main`. The build now runs `automation/scripts/write-decap-config.js` after Eleventy. The script identifies the Netlify project using the immutable site ID (with a matching site-name cross-check) and writes only the generated `public/admin/config.yml`:

- staging site ID → `branch: Staging`
- production site ID → `branch: main`
- unknown Netlify site identity → hard failure

Therefore merging this mechanism later cannot redirect the production CMS to `Staging`; production is explicitly pinned by its own site ID. The staging CMS link is withheld until a deployed staging build is verified to serve `branch: Staging`.

## Durable Phase 7 state

The existing `runs` row is extended in-place with:

`phase7_status`, `phase7_last_safe_status`, `phase7_error_message`, `staging_deploy_id`, `staging_deploy_commit`, `staging_preview_url`, `review_url`, `review_payload_json`, `notification_status`, and `notification_sent_at`.

Lifecycle: `NOT_STARTED → DEPLOY_WAITING → DEPLOY_VERIFIED → REVIEW_READY → NOTIFICATION_SENDING → NOTIFICATION_SENT`, with `FAILED` retaining the last safe checkpoint.

## Deployment verification and URL guard

`automation/lib/phase7_review.py` hard-codes the staging identity guard. It rejects `main`, the production Netlify site ID, and the production Netlify project. It uses GitHub compare semantics to require the Phase 6 commit to be contained by `Staging`, accepts only a `ready` deploy from `devtravtes` on branch `Staging`, and accepts a matching commit or descendant containing the draft commit.

Preview URLs are generated only under `https://devtravtes.netlify.app/` and are HTTP checked. The review payload always sets `published: false`.

Draft URLs are described as **staging previews / unlisted staging previews**, not private URLs. Existing Eleventy behavior filters drafts from production-style collections but still generates direct pages.

## Canonical review result

The durable review payload includes run ID, title, destination, `Staging` branch, draft commit, Markdown path, staging preview, optional safe CMS URL, image count, generation warnings, missing information, and `published: false`.

Telegram and form paths should consume this same object. Phase 7 does not duplicate business logic. A Telegram sender may mark notification `SENDING` and then `SENT`; retries after `SENT` return `NO_NOTIFICATION_NEEDED`. Form-originated automation may return the same review object directly without creating a second payload shape.

## n8n

`automation/n8n/phase7-staging-review-handoff-workflow.json` is a controlled inactive workflow export. It asks the internal worker to prepare the run, verify the staging deploy/preview, and return the canonical review result. The production n8n instance is not restarted by Phase 7.

## Recovery and idempotency

A run already at review/notification state does not repeat generation or GitHub writes. Phase 7 never calls DeepSeek. Notification completion is durable; retries after success cannot produce a second successful send. Deployment verification can be retried while `DEPLOY_WAITING`, and a verified payload is persisted for later reuse.

## Tests

New deterministic tests:

- `python3 automation/scripts/test-phase7-review.py`
- `node automation/scripts/test-decap-branch.js`

The full Phase 1/2/4/5/6 regression suite, `git diff --check`, and a production-mode Eleventy build remain mandatory.

## Acceptance evidence

Acceptance evidence is appended after the controlled staging run. Synthetic files are removed afterward while durable audit history is retained.

## Phase boundary

Phase 7 stops at safe staging review handoff. It does **not** implement `Staging → main`, `draft:false`, automatic publishing, automatic merging, or production CMS publishing. Those require explicit approval in a later phase.
