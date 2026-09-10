# Eduardo OS eReport connector

Silent sidecar for any project: clone this repo as **`.ereport/`** at your project root. Keeps your tree clean while agents sync Issue Tracker reports via the public API and keep a **local execution log** under `.ereport/execution/`.

**Design (docs-first):** the client stays thin — require an API key, fetch `GET /api/v1/docs` **before any API action**, then craft authenticated requests from the live catalog (`routes` + `payloadSchema`).

**POST modes (live docs):**

- `mode: "append"` (default) — additive merge; new items need `incidencia` + `status: "reprobado"`; cannot edit existing ids.
- `mode: "replace"` + `confirmOverwrite: true` — full seed bootstrap (mixed statuses).

**Execution log:** local only. Runtime files under `.ereport/execution/` belong to the **consumer project**. They are gitignored in this upstream connector repo so host analytics are never pushed to [eduardoos-ereport-connector](https://github.com/EduardoOsteicoechea/eduardoos-ereport-connector).

## Install (recommended)

From your project root:

```bash
git clone --depth 1 https://github.com/EduardoOsteicoechea/eduardoos-ereport-connector.git .ereport
```

Or run the installer (also wires the Cursor skill):

```bash
# Unix
curl -fsSL https://raw.githubusercontent.com/EduardoOsteicoechea/eduardoos-ereport-connector/main/install.sh | bash

# Windows PowerShell (from project root)
irm https://raw.githubusercontent.com/EduardoOsteicoechea/eduardoos-ereport-connector/main/install.ps1 | iex
```

Then:

```bash
cp .ereport/.env.example .ereport/.env   # required: EDUARDOOS_API_KEY; org/report ids for edits
```

**Consumer gitignore (suggested):**

```gitignore
.ereport/.env
.ereport/report.payload.json
.ereport/docs.catalog.json
.ereport/execution_append_body.json
# optional — keep execution history private, or commit it in YOUR repo:
# .ereport/execution/
```

> `.ereport/` is a **directory** (this connector). A `*.ereport` **file** is a report payload export — different things.

## Cursor skill

After install, skill files live at `.ereport/skill/eduardoos-ereport/`.  
Installers copy them to `.cursor/skills/eduardoos-ereport/` so Cursor can load skill `eduardoos-ereport`.

Read **CAVEATS** before Mode B/C: `.ereport/skill/eduardoos-ereport/CAVEATS.md`

## CLI (docs-first API)

```bash
cd .ereport
python ereport_client.py docs
python ereport_client.py request GET /api/v1/ereport/access
python ereport_client.py request GET /api/v1/ereport/orgs/{orgId}/reports/{reportId}
python ereport_client.py request POST /api/v1/ereport/orgs/{orgId}/reports/{reportId} --file body.json
```

## Local execution log

```bash
cd .ereport
python execution_log.py enable
python execution_log.py identity --file identity.json   # last-executed wins
python execution_log.py ingest --file run.json
python execution_log.py status
python execution_log.py digest --stream C20MCB-100 --step-id "CU 6.2.1"
python execution_log.py to-ereport                     # writes execution_append_body.json
# then POST append via ereport_client (docs first)
```

Read protocol: `last_status` → `identity` → `executions.index.json` → one run — never dump full DB into chat.

Full schema: [EXECUTION_LOG.md](EXECUTION_LOG.md)

Docs: https://eduardoos.com/api-docs  
Catalog: https://eduardoos.com/api/v1/docs

## License

MIT — see [LICENSE](LICENSE).
