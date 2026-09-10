---
name: eduardoos-ereport
description: >-
  Sync Eduardo OS eReport org reports via the public rate-limited API: open or
  edit issues on the website, get/post payloads with an API key (append or
  replace). Optional local execution ledger under .ereport/execution/ requires
  explicit user ACCEPT before enable. Use when the user mentions eReport,
  Issue Tracker, .ereport connector, eos_live_ keys, org reports, execution
  log, or mapping QA/quejas into a remote report.
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

## Mandatory: execution-logging consent (before Mode D)

When implementing or wiring eReport in a host repo, the agent **must notify the user** that an optional **execution logging extension** exists, and **must wait for an explicit choice** before enabling it.

1. Show the prompt (or run `python .ereport/execution_log.py prompt`).
2. Ask the user to **ACCEPT** or **REJECT** logging.
3. Record the choice:

```bash
python .ereport/execution_log.py accept   # user accepted
# or
python .ereport/execution_log.py reject   # user rejected
```

| User choice | Agent behavior |
|-------------|----------------|
| **ACCEPT** | Run `enable`, then treat detailed ledger logging as a **standing rule**: identity → ingest after work units → digest before closeouts; map `fail\|review` via `to-ereport` + API `append` when syncing opens. Fail-soft (log IO never aborts host work). |
| **REJECT** | Do **not** call `enable` / `ingest`. Still may sync the Issue Tracker via API (`append` / `replace`) using the agent’s own report workflow — no `.ereport/execution/` ledger. |
| **Unset** | Do not enable logging. Ask again if the task needs evidence tracking. |

Never enable logging silently. Never imply REJECT blocks eReport API sync.

## When to use

- Add **new open issues** (`append`) or bootstrap a full seed (`replace`)
- After **ACCEPT**: keep agent/CI evidence in **`.ereport/execution/`** (consumer project)
- Map `fail|review` steps → append POST body (`to-ereport`) then remote POST

## Modes (pick one)

| Mode | Use when |
|------|----------|
| **A** | Report not open yet — guide human on the website |
| **B** | Sync via API key (docs → get → append or replace → post) |
| **C** | Parse complaints → append open issues → post |
| **D** | Local execution log — **only after user ACCEPT** |

### Mode B (API — docs first)

```bash
python .ereport/ereport_client.py docs
python .ereport/ereport_client.py request GET /api/v1/ereport/access
python .ereport/ereport_client.py request GET /api/v1/ereport/orgs/$ORG/reports/$REPORT
python .ereport/ereport_client.py request POST /api/v1/ereport/orgs/$ORG/reports/$REPORT --file .ereport/body.json
```

### Mode D (local execution log — consent first)

```bash
python .ereport/execution_log.py prompt          # show user; wait for answer
python .ereport/execution_log.py accept          # only if user accepts
python .ereport/execution_log.py enable
python .ereport/execution_log.py identity --file identity.json
python .ereport/execution_log.py ingest --file run.json
python .ereport/execution_log.py digest --stream … --step-id …
python .ereport/execution_log.py to-ereport
```

**If logging was ACCEPTED**, agents must incorporate these standing rules:

1. Publish/refresh **identity** (last-executed wins) when a process starts.
2. **Ingest** a portable run (or step batch) after meaningful work units.
3. Before coding closeouts / claiming fixes: emit a **digest** (index-first; never dump full DB into chat).
4. Prefer **append** of new `reprobado` items from `fail|review|error`; never auto-close via append.
5. Fail-soft: ledger IO errors → status line, continue host work.
6. Never print API keys; never push `.ereport/execution/` runtime data to the connector upstream remote.

**Read order:** `consent` → `last_status` → `identity` → `executions.index.json` → one run.

## Hard rules

1. Never print the API key.  
2. **Always `docs` before any other API call.**  
3. Default POST **`append`**: cannot modify existing item ids; new items need `incidencia` + `reprobado`.  
4. **`replace`** only for explicit full sync + `confirmOverwrite: true`.  
5. Append **cannot** close issues (`reprobado` → `aprobado`).  
6. Honor **60 req/min/key**.  
7. End API writes with `Ver reporte: <viewUrl>`.  
8. **Never enable execution logging without user ACCEPT.**  
9. If REJECT: sync report without ledger; if ACCEPT: detailed ledger logging is mandatory for that project’s agent workflow.
