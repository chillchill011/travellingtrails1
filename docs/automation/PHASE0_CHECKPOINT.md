# Travelling Trails Automation — Phase 0 Checkpoint

Date: 2026-10-08
Branch: `Staging`

## Git / Netlify boundary

- Production branch remains `main`.
- Automation development branch is `Staging`.
- `Staging` was synchronized to current `main` before this checkpoint.
- Production Netlify project remains on `main`.
- Staging Netlify project (`devtravtes`) is configured to deploy `Staging`.

## Server discovery

Host: `deshmukh`

- OS: Ubuntu 24.04 family, Linux kernel 7.0.0-34-generic.
- Docker: 29.1.3.
- n8n container image: `docker.n8n.io/n8nio/n8n:2.40.7`.
- n8n health check: HTTP 200.
- n8n persistence: SQLite at `/home/aniket/nas-stack/n8n/data/database.sqlite`.
- n8n workflow count at discovery: 12 total, 7 active.
- n8n credential count at discovery: 7.
- Dedicated Telegram credential confirmed by name: `Travelling Trails Bot`.
- Existing unrelated project containers were not modified.
- ImageMagick is not installed on the host yet.
- Netlify CLI is not installed on the host yet.
- No Travelling Trails checkout or dedicated backup directory existed on the host at discovery.

## Safety rules carried forward

- Do not write automation-development changes to `main`.
- Do not modify unrelated n8n workflows or credentials.
- Back up n8n before any material workflow change.
- Import/test new Travelling Trails workflow inactive before activation.
- All generated posts must begin with `draft: true` and automation must stop before publishing.
- Secrets, raw credential data, database dumps, and private execution logs must remain outside Git.
