# Phase 2 — Staging GitHub draft write

This phase adds the deterministic write boundary after Phase 1 validation/serialization.

Safety invariants:

- branch is exactly `Staging` during implementation/testing;
- post paths must match `src/blog/YYYY-MM-DD-slug.md`;
- Markdown must contain `draft: true` and may never contain `draft: false`;
- remote path state is checked before writing;
- same-path + same-content is an idempotent success;
- same-path + different-content is a hard collision and must stop;
- the Markdown draft is written last (images will be added in a later phase);
- production `main` is untouched.

Run the deterministic tests with:

`node automation/scripts/test-github-draft.js`

The n8n workflow template is stored at `automation/n8n/phase2-staging-draft-write-workflow.json`. It intentionally references the dedicated credential name `GitHub - Travelling Trails` but is not imported until that credential exists in n8n. Do not reuse credentials owned by unrelated automations.
