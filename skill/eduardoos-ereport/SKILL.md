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
**Endpoints / payload:** [reference.md](reference.md).  
**CLI:** `.ereport/ereport_client.py` (from project root: `python .ereport/ereport_client.py …`).

Repo: https://github.com/EduardoOsteicoechea/eduardoos-ereport-connector  
Docs: https://eduardoos.com/api-docs

## When to use

- Open / update / extend issues in an **owned** org report from chat, files, or pasted data
- Wire a repo agent to `access → orgs → org-reports → get → put`
- Ingest QA/complaints docs into the live report

## Modes (pick one)

| Mode | Use when |
|------|----------|
| **A** | Report not open yet — guide human on the website |
| **B** | Sync via API key (get → edit payload → put) |
| **C** | Parse any complaints source → merge open issues → put |

If the report is not open on the site: **Mode A first**, then B or C.

### Mode A (non-technical)

1. Sign in at https://eduardoos.com  
2. Open eReport → organization → report (or create one)  
3. Copy **Org ID** + **Report ID**  
4. Create API key only in UI: `/auth/profile` or `/api-keys`  
5. Put key + ids in `.ereport/.env` (gitignored). Say “report is open”.

### Mode B (API)

```bash
python .ereport/ereport_client.py access
python .ereport/ereport_client.py orgs
python .ereport/ereport_client.py org-reports
python .ereport/ereport_client.py get
python .ereport/ereport_client.py put --file .ereport/report.payload.json
```

### Mode C

1. Confirm org/report (Mode A if needed).  
2. `get` current payload.  
3. Parse user data; map to items (`reprobado` = open).  
4. **Merge in place** — never put a thin payload of only new issues.  
5. `put`; print open ids + `Ver reporte: <viewUrl>`.

## Hard rules

1. Never print the API key.  
2. `put` is **full replace** — always `get` first.  
3. Preserve `fechaIncidencia` / `fechaSolucion` and untouched items.  
4. Honor **60 req/min/key**.  
5. End with `Ver reporte: <viewUrl>`.

## Host-repo install (cleanest)

```bash
git clone --depth 1 https://github.com/EduardoOsteicoechea/eduardoos-ereport-connector.git .ereport
# wire skill into .cursor/skills/eduardoos-ereport (see install.sh / install.ps1)
```
