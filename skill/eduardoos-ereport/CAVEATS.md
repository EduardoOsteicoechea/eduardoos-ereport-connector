# Caveats — `.ereport` connector downloaders

Read this before Mode B/C.

## What this is

- A **sidecar folder** `.ereport/` in *your* project (clone of `eduardoos-ereport-connector`).
- Plus a Cursor skill that teaches an agent to call Eduardo OS’s **public eReport API** with **your** key.
- The CLI is intentionally thin: **API key + docs + generic request**. Agents must learn endpoints and write rules from `GET /api/v1/docs` **before every session/action**.
- Good for: **adding** open issues from **any data the agent can parse**.

## What this is not

- **Not** permission to edit existing issues via API — server **rejects** mutations to existing item ids (additive merge only).
- **Not** key management (keys = **UI only**).
- **Not** access to other people’s reports — **owned only**.
- **Not** unlimited traffic — **60 req/min/key** (429 + `Retry-After`).
- **Not** the same as a `*.ereport` report **file** — `.ereport/` is the connector **directory**.
- **Not** a hardcoded schema — prefer live docs over this skill’s snapshots.

## Requirements

1. Subscriptions: **`api`** + **`ereport`**  
2. Key from https://eduardoos.com/auth/profile or `/api-keys`  
3. `orgId` + `reportId`  
4. Secrets only in `.ereport/.env` — never commit

## Safety

- Always **docs → get → append new `reprobado` issues (with text) → post**  
- Never change existing asuntos via API  
- End with `Ver reporte: <viewUrl>`

## Liability

You own what your agent writes. Prefer `GET https://eduardoos.com/api/v1/docs` if docs disagree with this skill.
