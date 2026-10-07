# Phase 1 automation scaffold

Staging-only development for Travelling Trails. `02_BLOG_POST_SCHEMA.md` is the authoritative publishing contract.

Safety invariants: generated content starts with `draft: true`; DeepSeek returns strict JSON; validation and YAML/Markdown assembly are deterministic; no image processing is implemented in Phase 1; production `main` is untouched.

Run: `node automation/scripts/test-text-pipeline.js`.

Server mutation helpers use `/mnt/storage/chatgpt-locks/travellingtrails-n8n.lock`. `backup-n8n.sh` uses SQLite's online backup API and writes private timestamped backups under `/mnt/storage/travellingtrails-backups`. Restore is guarded and requires n8n to be stopped through Portainer before use.
