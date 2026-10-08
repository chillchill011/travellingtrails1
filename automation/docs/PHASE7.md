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

## Genuine acceptance evidence

Phase 7 reused the retained, genuine Phase 5/6 synthetic acceptance run `tt-20261008-8cd97b0472a037c1`. Its original Phase 6 draft commit is `b919f86268e8a4d7dba5f1deb562cb0767f309ba`, its durable `deepseek_call_count` remained `2`, and no Phase 7 step called DeepSeek or rewrote the draft.

For the controlled review test, the exact previously generated synthetic Markdown and four image blobs were temporarily restored to `Staging` in commit `dfe3ee13b739fd55e196a82b1c2098515f923bb8`. Netlify project `devtravtes` deployed that commit as deploy `6ac7dcc6a7a213000786015b`, branch `Staging`, state `ready`.

Verified staging preview:

`https://devtravtes.netlify.app/synthetic-automation-acceptance-test-synthetic-phase-6-ridge/` → HTTP 200.

The same path on `https://travellingtrails.in/` returned HTTP 404, and `origin/main` stayed at `e4a2f9eb75ea3e7e9de3268d9cbf59c7602cb5dc`.

The durable review payload contained `published:false`, branch `Staging`, four images, the Phase 6 commit/path, generation warnings/missing information, the staging preview, and the staging CMS URL. The synthetic source is a retained manual acceptance run, so no external Telegram message was actually sent. The durable acceptance state was therefore restored to `REVIEW_READY` with `notification_status=PENDING`; notification duplicate suppression is proven by the deterministic state test rather than a fake external send.

Live Decap verification after the Phase 7 deployment:

- `https://devtravtes.netlify.app/admin/config.yml` serves `backend.branch: Staging`.
- `https://travellingtrails.in/admin/config.yml` serves `backend.branch: main`.
- staging `/admin/` returns HTTP 200.

The Phase 7 workflow was imported into n8n with stable ID `TTPhase7Review01` and remains inactive (`active=0`). The first import attempt correctly failed without changing workflow state because the draft export lacked an ID; the export was fixed to match the established project format and the next import succeeded.

## Final verification and backups

The complete Phase 1/2/4/5/6 regression suite, the expanded Phase 7 deploy/state/idempotency suite, Decap branch-isolation tests, `git diff --check`, and the normal production-mode Eleventy build all passed after the final fixes. Phase 7 deploy tests explicitly cover matching/ready, wrong site, wrong branch, failed deploy, descendant containment, and timeout/retry.

Final backups:

- n8n database: `/mnt/storage/travellingtrails-backups/20261008T181306Z-phase1`
  - SHA-256: `4f2f13f2924ab519b8242bab250b90e271fde9d9a204dfea394568fe82e8c66c`
- Phase 5/6/7 durable state: `/mnt/storage/travellingtrails-backups/20261008T181316Z-phase5-state`
  - `phase5.sqlite3` SHA-256: `fe39f86d5b4ab3fb0d68a5a4125d058a73509267a9818e77a55737206cbded8a`
  - `runs.tar.gz` SHA-256: `f16f8f8b29e156fd06f5cd5be17a767aacadd3e4f340e78c24313c38fd3cc896`

Both live SQLite databases passed `PRAGMA integrity_check` after these backups.

The temporary synthetic Markdown/image fixture is removed from the final `Staging` tree after acceptance; durable audit history remains retained.
