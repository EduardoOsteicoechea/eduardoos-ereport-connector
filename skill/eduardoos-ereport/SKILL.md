---
name: eduardoos-ereport
description: >-
  Sync Eduardo OS eReport org reports via the public rate-limited API: open or
  edit issues on the website, get/put full payloads with an API key, and ingest
  any parseable complaints document into sections/groups/items. Use when the
  user mentions eReport, Issue Tracker, .ereport connector, eos_live_ keys,
  org reports, or mapping QA/quejas into a remote report.
disable-model-invocation: true
---

# Eduardo OS eReport API skill

**Install location:** project sidecar **`.ereport/`** (this connector repo).  
**Before first run:** read [CAVEATS.md](CAVEATS.md).  
**Live API contract:** always `GET /api/v1/docs` first (see [reference.md](reference.md)).  
**CLI:** `.ereport/ereport_client.py` (from project root: `python .ereport/ereport_client.py …`).

Repo: https://github.com/EduardoOsteicoechea/eduardoos-ereport-connector  
Docs: https://eduardoos.com/api-docs

## When to use

- Add **new open issues** to an **owned** org report from chat, files, or pasted data
- Wire a repo agent to docs-driven access → orgs → reports → get → additive post
- Ingest QA/complaints docs as **new** `reprobado` items (never rewrite existing ones)

## Modes (pick one)

| Mode | Use when |
|------|----------|
| **A** | Report not open yet — guide human on the website |
| **B** | Sync via API key (docs → get → append new issues → post) |
| **C** | Parse any complaints source → append open issues → post |

If the report is not open on the site: **Mode A first**, then B or C.

### Mode A (non-technical)

1. Sign in at https://eduardoos.com  
2. Open eReport → organization → report (or create one)  
3. Copy **Org ID** + **Report ID**  
4. Create API key only in UI: `/auth/profile` or `/api-keys`  
5. Put key + ids in `.ereport/.env` (gitignored). Say “report is open”.

### Mode B (API — docs first)

```bash
# Required: EDUARDOOS_API_KEY in .ereport/.env
python .ereport/ereport_client.py docs
# Read docs.catalog.json → payloadSchema.writeSemantics (additive POST)
python .ereport/ereport_client.py request GET /api/v1/ereport/access
python .ereport/ereport_client.py request GET /api/v1/ereport/orgs
python .ereport/ereport_client.py request GET /api/v1/ereport/orgs/$ORG/reports
python .ereport/ereport_client.py request GET /api/v1/ereport/orgs/$ORG/reports/$REPORT
# Append ONLY new items (status reprobado + non-empty incidencia). Do not change existing item ids.
python .ereport/ereport_client.py request POST /api/v1/ereport/orgs/$ORG/reports/$REPORT --file .ereport/report.payload.json
```

### Mode C

1. Confirm org/report (Mode A if needed).  
2. `docs` then GET current payload.  
3. Parse user data; create **new** item ids with `status: reprobado` and non-empty `incidencia`.  
4. **Never edit/delete existing issues** — server returns 400.  
5. POST; print open ids + `Ver reporte: <viewUrl>`.

## Hard rules

1. Never print the API key.  
2. **Always `docs` before any other API call** — schema evolves.  
3. API POST is **additive for issues** (server merge). Cannot modify existing asuntos.  
4. New issues: non-empty `incidencia` + `status: "reprobado"`.  
5. Honor **60 req/min/key**.  
6. End with `Ver reporte: <viewUrl>`.

## Host-repo install (cleanest)

```bash
git clone --depth 1 https://github.com/EduardoOsteicoechea/eduardoos-ereport-connector.git .ereport
# wire skill into .cursor/skills/eduardoos-ereport (see install.sh / install.ps1)
```
