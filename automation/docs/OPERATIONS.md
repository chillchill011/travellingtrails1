# Travelling Trails Automation — Everyday Operations

## Create a new article

1. Open `https://deshmukh.taild717f3.ts.net:8443/form/travelling-trails-phase5` and sign in with the normal authorized n8n account if prompted.
2. Enter the trip date, author, destination, duration and rough trip notes.
3. Add route, cost, gear and must-include notes when relevant.
4. Upload exactly one featured photo. A thumbnail derivative is created automatically if no separate thumbnail is supplied.
5. Optionally upload gallery photos, route screenshots/images and unused photos.
6. Click **Create Staging Draft** once.
7. The automation processes images, generates and validates the article, writes a `draft:true` Staging post, waits for the Staging Netlify deployment and returns the review result.
8. Open the returned Staging preview and edit link. The staging CMS is `https://devtravtes.netlify.app/admin/` and must point to branch `Staging`.

Important screenshot rule: if information visible in a route map, receipt, booking screenshot or other image is important to the article text, type that information into the relevant notes field too. DeepSeek is not allowed to guess or OCR authoritative facts from pixels.

## Approve the reviewed draft for production

After reviewing and editing the Staging draft:

1. Keep the article as `draft:true` in Staging.
2. Open the **Approve Promotion** link returned with the staging draft. The link carries the run ID and reviewed title as hidden form values, so you do not copy either manually.
3. Select `APPROVE` and submit.
4. The automation captures the current Staging Markdown and referenced media into an immutable promotion manifest.
5. It promotes only that article and its referenced media to `main` in one Git commit when a write is needed.
6. It verifies the production draft deployment and returns the production handoff.

The entire `Staging` branch is never merged into `main` by this workflow.

## Publish the article

1. Open `https://travellingtrails.in/admin/`.
2. Confirm you are editing the expected article.
3. Review one final time.
4. Manually change **Draft** from `true` to `false`.
5. Save/publish from Decap CMS.
6. Do not ask the automation to flip the draft flag. The publication action must remain human.
7. The Phase 8 publication watcher checks awaiting runs every 10 minutes. It verifies the human publish commit, the production Netlify deploy, the live article URL and the blog listing.

## Recovery and retry

Every article has one durable `runId`. Repeating a safe step reuses stored state:

- processed images are not re-uploaded when already complete
- DeepSeek is not called again after valid generated JSON exists
- a Staging draft is not duplicated after `DRAFT_CREATED`
- a promotion manifest is never silently recaptured on retry
- an existing exact production promotion is treated idempotently

If a run fails, preserve its run ID and inspect its last safe state. Do not create a new run merely to bypass a deterministic validation, collision or concurrency failure.

A `HARD_COLLISION` means a destination path on `main` already contains different bytes. Resolve it deliberately; the automation will not overwrite it.

## Backups

Backup scripts:

- `automation/scripts/backup-n8n.sh`
- `automation/scripts/backup-phase5-state.sh`

Both SQLite databases should pass `PRAGMA integrity_check = ok` before and after significant workflow changes. The Phase 5/6/7/8 durable database is the same `phase5.sqlite3` database; Phase 8 did not create another database.

## Safety invariants

- Staging = branch `Staging`, project `devtravtes`, site ID `bb8c325b-9562-4952-8613-439ca95dc9e0`.
- Production = branch `main`, project `travellingtrails1`, site ID `edd2477f-24f5-4005-a05c-f0310f1efe11`.
- AI output must always start as `draft:true`.
- Automated production promotion must preserve `draft:true`.
- Only the human owner publishes by changing `draft:true` to `draft:false` in production Decap.
- A production draft is unlisted, not guaranteed private.
