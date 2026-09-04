# Eduardo OS eReport connector

Silent sidecar for any project: clone this repo as **`.ereport/`** at your project root. Keeps your tree clean while agents sync Issue Tracker reports via the public API.

**Design (docs-first):** the client stays thin — require an API key, fetch `GET /api/v1/docs` **before any action**, then craft authenticated requests from the live catalog (`routes` + `payloadSchema`). API POST is **additive for issues** (server rejects edits to existing item ids). Architecture changes land in the product docs; agents re-learn without connector churn.

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
```

Optional: ignore the whole `.ereport/` folder and clone per machine, or add it as a git submodule.

> `.ereport/` is a **directory** (this connector). A `*.ereport` **file** is a report payload export — different things.

## Cursor skill

After install, skill files live at `.ereport/skill/eduardoos-ereport/`.  
Installers copy them to `.cursor/skills/eduardoos-ereport/` so Cursor can load skill `eduardoos-ereport`.

Read **CAVEATS** before Mode B/C: `.ereport/skill/eduardoos-ereport/CAVEATS.md`

## CLI (docs-first)

```bash
cd .ereport
# 1) Live catalog (no key) — always first
python ereport_client.py docs

# 2) Generic requests (key required except docs)
python ereport_client.py request GET /api/v1/ereport/access
python ereport_client.py request GET /api/v1/ereport/orgs
python ereport_client.py request GET /api/v1/ereport/orgs/{orgId}/reports
python ereport_client.py request GET /api/v1/ereport/orgs/{orgId}/reports/{reportId}
# edit report.payload.json using payloadSchema from docs
python ereport_client.py request POST /api/v1/ereport/orgs/{orgId}/reports/{reportId} --file report.payload.json
```

Convenience aliases still work: `access`, `orgs`, `org-reports`, `get`, `put --file …`.

Docs: https://eduardoos.com/api-docs  
Catalog: https://eduardoos.com/api/v1/docs

## License

MIT — see [LICENSE](LICENSE).
