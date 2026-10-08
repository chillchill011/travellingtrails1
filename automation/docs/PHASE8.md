# Travelling Trails Automation — Phase 8

## Status

Implementation is installed and operational for the user-facing draft chain and the approval-controlled production boundary.

Final project acceptance remains `AWAITING_REAL_ARTICLE_ACCEPTANCE` until a genuine article completes the full human publication cycle. `PROJECT_COMPLETE.md` must not be created before that acceptance.

## Environment identity

Staging is always:

- Git branch: `Staging`
- Netlify project: `devtravtes`
- Netlify site ID: `bb8c325b-9562-4952-8613-439ca95dc9e0`
- Site: `https://devtravtes.netlify.app/`
- CMS: `https://devtravtes.netlify.app/admin/`

Production is always:

- Git branch: `main`
- Netlify project: `travellingtrails1`
- Netlify site ID: `edd2477f-24f5-4005-a05c-f0310f1efe11`
- Site: `https://travellingtrails.in/`
- CMS: `https://travellingtrails.in/admin/`

## User-facing draft workflow

Workflow ID: `TTPhase5Ingestion01`

Current name: `Travelling Trails - Complete Draft Automation`

Form URL:

`https://deshmukh.taild717f3.ts.net:8443/form/travelling-trails-phase5`

The form is protected by n8n user authentication and execute access. An unauthenticated HTTP request receives a redirect to authentication rather than an open public form.

Normal chain:

`Form -> Phase 5 ingestion/images -> Phase 4 atomic Staging image commit -> Phase 6 DeepSeek/validation/draft -> Phase 7 Staging deploy+preview verification -> APPROVAL_REQUIRED`

The same `runId` is passed directly through the subworkflows. The normal path does not use `TT_PHASE6_TEST_RUN_ID` or `TT_PHASE7_RUN_ID`.

Phase 6 workflow ID: `TTPhase6FullDraft01`.

Phase 7 workflow ID: `TTPhase7Review01`.

Phase 6 and Phase 7 retain manual test triggers but now also expose Execute Workflow Trigger inputs for orchestration.

Phase 7 waits for a matching ready `devtravtes` deploy for up to 150 seconds before returning `DEPLOY_WAITING`. This avoids requiring the user to manually run Phase 7 after the Netlify build.

## DeepSeek boundary

DeepSeek is used only in Phase 6 for text generation. It remains text-only. Route screenshots, receipts, maps and other images are not OCR'd or treated as authoritative text sources.

If screenshot information must appear in prose, enter it in the corresponding notes field.

Retries reuse durable `generated_json` and do not call DeepSeek again after a valid generation has been stored.

## Production promotion

Workflow ID: `TTPhase8Promotion01`

Name: `Travelling Trails - Phase 8 Production Promotion`

Approval form:

`https://deshmukh.taild717f3.ts.net:8443/form/travelling-trails-phase8-promote`

This form is also protected by n8n user authentication and execute access. The staging result returns a per-run approval URL. `runId` and the reviewed title are query-bound hidden form fields, so the user does not copy them manually. The only visible approval action is the explicit `APPROVE` selection.

At approval time the worker reads the **current** Staging Markdown at the current Staging commit. It requires `draft: true`, extracts referenced `/assets/images/...` files, resolves their exact Git blob SHAs and SHA-256 hashes, and stores an immutable promotion manifest.

The automated allowlist is limited to:

- `src/blog/<approved-post>.md`
- `src/assets/images/<approved-media>`

Arbitrary paths, path traversal and non-blog/non-media paths are rejected.

For every destination path on `main`:

- missing -> create
- exact same blob -> idempotent/already present
- different blob -> `HARD_COLLISION`

The promotion workflow creates one Git tree and one Git commit using the exact reviewed blobs and then fast-forwards `main` with `force:false`. Because the promotion commit is parented to the captured `main` SHA, a concurrent main update prevents a fast-forward rather than overwriting it.

Automated promotion never changes `draft:true` to `draft:false`.

After the promotion commit, production deploy verification checks only `travellingtrails1`, site ID `edd2477f-24f5-4005-a05c-f0310f1efe11`, branch `main`, and verifies the promoted Markdown still has `draft:true`.

## Manual publication and detection

Human publication remains mandatory in:

`https://travellingtrails.in/admin/`

The owner manually changes `draft: true` to `draft: false` and saves/publishes.

Worker publication verification rejects an ambiguous draft state, verifies the publish commit/diff, requires no unrelated changed path between promotion and the detected publication commit, verifies a ready production Netlify deploy, verifies the final live article URL, and verifies the article is represented in `/blog/`.

The worker exposes a durable list of runs awaiting publication at an internal-only endpoint. The publication-watch workflow is `TTPhase8PublishWatch01`; it checks every 10 minutes and performs verification only. It has no GitHub write node and cannot publish content.

## Durable state

Phase 8 extends the existing `runs` table in the same SQLite database. Fields include:

- `phase8_status`
- `phase8_last_safe_status`
- `phase8_error_message`
- `orchestration_status`
- `promotion_approved_at`
- `promotion_source_commit`
- `promotion_manifest_json`
- `promotion_commit_sha`
- `production_draft_deploy_id`
- `production_draft_deploy_commit`
- `publish_commit_sha`
- `production_deploy_id`
- `production_deploy_commit`
- `production_url`
- `final_result_json`
- completion-notification fields

No second application-state database was introduced.

## Tests

Phase 8 adds `automation/scripts/test-phase8-promotion.py` covering:

- explicit approval required
- current reviewed Staging bytes captured
- `draft:false` promotion rejected
- path/media manifest generation
- hard collision rejection
- manifest idempotency
- promotion-completion idempotency
- Phase 6 and Phase 7 callable-workflow contracts
- protected approval form contract

All prior Phase 1–7 regression tests and the Eleventy build were rerun during Phase 8 implementation.

## Final acceptance boundary

Do not create `automation/docs/PROJECT_COMPLETE.md` until a real intended article proves all of the following:

`real form submission -> automatic Phase 5 -> automatic Phase 6 -> automatic Phase 7 -> staging review -> explicit promotion approval -> main draft:true -> production deploy -> human Decap draft:false -> publication detection -> final live URL/listing verification`
