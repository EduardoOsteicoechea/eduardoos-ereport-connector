---
name: eduardoos-ereport
description: >-
  Sync Eduardo OS eReport org reports via the public rate-limited API: open or
  edit issues on the website, get/post payloads with an API key (append or
  replace), keep a local execution log under .ereport/execution/, and map
  fail/review evidence into reprobado append bodies. Use when the user mentions
  eReport, Issue Tracker, .ereport connector, eos_live_ keys, org reports,
  execution log, or mapping QA/quejas into a remote report.
disable-model-invocation: true
---

# Eduardo OS eReport API skill

**Install location:** project sidecar **`.ereport/`** (this connector repo).  
**Before first run:** read [CAVEATS.md](CAVEATS.md).  
**Live API contract:** always `GET /api/v1/docs` first (see [reference.md](reference.md)).  
**CLI:** `.ereport/ereport_client.py` · **Local log:** `.ereport/execution_log.py`  
**Spec:** `.ereport/EXECUTION_LOG.md`

Repo: https://github.com/EduardoOsteicoechea/eduardoos-ereport-connector  
Docs: https://eduardoos.com/api-docs

## When to use

- Add **new open issues** (`append`) or bootstrap a full seed (`replace`)
- Keep agent/CI run evidence in **`.ereport/execution/`** (consumer project)
- Map `fail|review` steps → append POST body (`to-ereport`) then remote POST

## Modes (pick one)

| Mode | Use when |
|------|----------|
| **A** | Report not open yet — guide human on the website |
| **B** | Sync via API key (docs → get → append or replace → post) |
| **C** | Parse complaints → append open issues → post |
| **D** | Local execution log (enable → ingest → digest → optional to-ereport) |

### Mode B (API — docs first)

```bash
python .ereport/ereport_client.py docs
# Read docs.catalog.json → payloadSchema.writeSemantics + modes
python .ereport/ereport_client.py request GET /api/v1/ereport/access
python .ereport/ereport_client.py request GET /api/v1/ereport/orgs/$ORG/reports/$REPORT
# append (default): new items only, status reprobado
# replace: full seed — confirmOverwrite true + "mode":"replace"
python .ereport/ereport_client.py request POST /api/v1/ereport/orgs/$ORG/reports/$REPORT --file .ereport/body.json
```

### Mode D (local execution log)

```bash
python .ereport/execution_log.py enable
python .ereport/execution_log.py identity --file identity.json
python .ereport/execution_log.py ingest --file run.json
python .ereport/execution_log.py digest --stream … --step-id …
python .ereport/execution_log.py to-ereport
# POST append body with ereport_client — never auto-close via append
```

**Read order:** `last_status.txt` → `identity.json` → `executions.index.json` → one run. Never load full `executions.json` into chat first.

Runtime files stay in the **host project’s** `.ereport/execution/`. Do not push them to the connector upstream repo.

## Hard rules

1. Never print the API key.  
2. **Always `docs` before any other API call.**  
3. Default POST **`append`**: cannot modify existing item ids; new items need `incidencia` + `reprobado`.  
4. **`replace`** only for explicit full sync + `confirmOverwrite: true`.  
5. Append **cannot** close issues (`reprobado` → `aprobado`).  
6. Honor **60 req/min/key**.  
7. End API writes with `Ver reporte: <viewUrl>`.  
8. Execution log IO failures must not abort host work (fail-soft).
