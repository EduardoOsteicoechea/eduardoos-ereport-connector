# Agent Execution Log — project-agnostic specification (for eReport)

**Purpose:** Extract the *ideas* behind Model Checker BA’s analytics engine into a **host-agnostic execution-log system** that any product (desktop, CI, web agent) can implement, so agents can:

1. **Log** their own runs (local and/or web)
2. **Read back** those runs (index-first, never dump full DB into context)
3. **Update eReport** from execution evidence (append open issues / replace seeds)

**Non-goal:** Copy Revit / CE-CU types. ModelBA is the **reference implementation**, not the schema.

**Related live systems today**

| Layer | Today (ModelBA) | Agnostic target |
|-------|-----------------|-----------------|
| Structured run ledger | `IntegrationAnalyticsService` → Public Documents JSON | Execution Log store (local and/or API) |
| Build / agent identity | `BuildInfo` (DLL last-executed wins) | `identity` block (branch/commit/version/source) |
| Verbose debug | `LoggerProviderService` / DualLogger / Telemetry HTML | `artifacts[]` pointers |
| QA report mirror | `QaReportAnalyticsPublisher` → seed + `.ereport` + HTML | eReport payload sync |
| Remote Issue Tracker | Manual `.ereport/ereport_client.py` | Same client + optional auto-bridge |

Live eReport API contract: always `GET https://eduardoos.com/api/v1/docs` (prefer over this doc if they disagree).

---

## 1. Design principles (non-negotiable)

1. **Opt-in + user consent.** Logging is off until the user **ACCEPT**s (`execution_log.py accept` → `enable`). Agents must show the consent prompt and wait. **REJECT** means no ledger; the agent may still sync the Issue Tracker without detailed logging. Never enable silently.
2. **Fail-soft.** Logging must never abort the primary work (verification, agent task, build). IO errors → status file, continue.
3. **Identity = last executed wins.** The identity of the *process that ran* beats any shared “install stamp” sitting on disk with a newer timestamp.
4. **Index-first reads.** Agents must not load the full run DB into context. Read status → index → filtered runs → open artifacts on demand.
5. **Structured store ≠ verbose logs.** Keep a small JSON ledger + separate large text/HTML logs referenced by path/URI.
6. **Retention.** Cap runs per identity stream (e.g. per branch) and messages per step; atomic writes (`.tmp` + replace).
7. **Report sync is a separate concern.** Execution log can *feed* eReport; it is not the Issue Tracker itself.
8. **Local and web share one schema.** Same JSON shapes; transport differs (`file://` vs HTTPS).

---

## 2. Vocabulary (agnostic)

| Agnostic term | ModelBA analogue | Meaning |
|---------------|------------------|---------|
| `project_id` | `ModelCheckerBA` | Product / campaign namespace |
| `execution_id` | `run_id` | One run of a batch of steps |
| `identity` | `BuildInfo` + session branch/commit | Who/what binary or agent ran |
| `subject` | Revit `Document` title/path | Model / workspace / target under test |
| `step` | `validacion` / article check | One unit of work inside the run |
| `step_id` | `SubarticleId` (e.g. `CU 6.2.1`) | Stable id agents key on |
| `status` | `EstadoVerificacion` | Normalized outcome enum |
| `messages` | `incumplimientos` (description strings) | Human-readable findings |
| `artifacts` | `log_path`, `resultado_json_path`, Telemetry HTML | Pointers to heavy evidence |
| `feedback` | `feedback_por_articulo` / open `quejas` | External complaints attached to steps |
| `report_mirror` | `reporte_qa_seed.json` / `.ereport` | Local Issue Tracker snapshot |
| `last_status` | `analytics.last_status.txt` | One-line health for IT |

### Status mapping

| Agnostic `status` | ModelBA | eReport item `status` (suggested) |
|-------------------|---------|-----------------------------------|
| `pass` | `Cumple` | often `aprobado` (when closing an issue) |
| `fail` | `NoCumple` | `reprobado` (open issue) |
| `review` | `ARevisar` | `reprobado` or keep open with note |
| `skipped` | `NoRevisar` | `no_aplica` or leave unchanged |
| `error` | catch → often `ARevisar` | `reprobado` |

Agents must treat **`review` as evidence, not automatic close**. Global step status can be `review` while `messages[]` still list failures — that is valid.

---

## 3. Reference architecture (extractable)

```
Host work (Revit verify / agent task / CI job)
  │
  ├─ Identity.refresh_and_publish()     // last-executed wins
  ├─ ExecutionLog.begin(subject)
  │     └─ session { execution_id, identity, subject, started_utc }
  ├─ for each step:
  │     run step → result
  │     verbose_logger.write(...)       // optional large artifact
  │     ExecutionLog.record(session, step_result)
  └─ ExecutionLog.complete(session)
        ├─ persist run → executions.json (DB)
        ├─ rebuild index → executions.index.json
        ├─ export per-step result JSON (optional)
        ├─ write last_status
        └─ ReportMirror.publish(session)   // local seed/.ereport/HTML
              └─ (optional) EreportBridge.push(mode=append|replace)
```

### Layers to ship as a reusable kit

| Component | Responsibility | Must stay host-free |
|-----------|----------------|---------------------|
| **A. Identity** | Resolve branch/commit/version; mirror “last executed” | Yes |
| **B. ExecutionLog core** | begin/record/complete, DB, index, retention, atomic IO | Yes |
| **C. Verbose logger adapter** | Host-specific paths (Revit docs, CI logs, browser) | Adapter only |
| **D. Feedback store** | Optional per-`step_id` complaints / normative notes | Yes (generic JSON) |
| **E. Report mirror** | Stamp seed + snapshots + HTML embed | Uses eReport payload shape |
| **F. Ereport bridge** | HTTP client: docs → get → merge → post | Already exists as `.ereport/` |

ModelBA couples A–E inside C# with Revit types. Extraction = keep A/B/D/E as a library (any language) + thin host adapters for C + F.

---

## 4. Storage layouts

### 4.1 Local layout (recommended portable)

```
{root}/
  execution.config.json
  execution.enabled                 # empty flag → force ON (QA)
  execution.last_status.txt
  identity.json                     # last-executed mirror
  feedback_by_step.json             # optional
  executions.json                   # DB (schema_version + runs[])
  executions.index.json             # by_identity_stream → by step_id
  report/
    report.seed.json                # latest Issue Tracker payload
    report.ereport                  # same bytes, .ereport extension
    report.populado.html
    report.last_status.txt
    seeds_manifest.json
    seeds/report_seed_YYYYMMDD_HHmmss.json
    ereports/report_YYYYMMDD_HHmmss.ereport
```

**ModelBA paths today (reference only — do not hardcode in agnostic core):**

```
C:\Users\Public\Documents\HexagonMultivista\ModelCheckerBA\analytics\
%USERPROFILE%\Documents\Model Checker BA Logs\
%USERPROFILE%\Documents\Model Checker BA Verificaciones\<model>\<step_id>\resultado_verificacion.json
%USERPROFILE%\Documents\Model Checker BA Procesos\<model>\*.html
```

Agnostic `{root}` should come from config:

```json
{
  "project_id": "my-product",
  "root": "%COMMON_DOCUMENTS%/MyVendor/MyProduct/execution",
  "enabled": true,
  "max_runs_per_stream": 50,
  "max_messages_per_step": 500,
  "max_methods_per_step": 15,
  "max_feedback_per_step": 50,
  "identity_stream_key": "branch"
}
```

`identity_stream_key` = how retention buckets runs (`branch`, `app_version`, `agent_id`, …).

### 4.2 Web layout (same schema, different transport)

Option A — **sidecar files under eReport media** (matches Eduardo OS “filesystem under owner”, no S3):

```
POST/GET /api/v1/ereport/orgs/{orgId}/reports/{reportId}/executions
POST/GET .../executions/{execution_id}
GET     .../executions/index?stream=...
```

Option B — **embed summary only into report meta** (weaker): stamp `lastExecutionId` / digest on the Issue Tracker payload; keep full DB local.

Option C — **dedicated executions service** next to eReport with the portable schema.

**Recommendation for Eduardo OS:** keep Issue Tracker POST (`mode=append|replace`) for human-facing issues only. **Execution logs stay local** in the consumer project's `.ereport/execution/` via [eduardoos-ereport-connector](https://github.com/EduardoOsteicoechea/eduardoos-ereport-connector) — not uploaded to Eduardo OS media and never pushed into the connector upstream repo.

---

## 5. Portable JSON schemas

### 5.1 `identity.json`

```json
{
  "stream": "C20MCB-100",
  "commit": "a88f1faf",
  "built_at_utc": "2026-09-02T10:39:28Z",
  "app_version": "1.1.4",
  "source": "local|ci|web_agent",
  "source_path": "optional path or URI of the binary/agent that ran",
  "published_at_utc": "2026-09-10T14:00:00Z"
}
```

**Rule:** When a process starts work, load identity from *itself* first; then overwrite the shared mirror (`identity.json` / Public buildinfo). Never pick “newest timestamp across install + feature DLL” — that mis-tags runs (ModelBA bug fixed as “last executed wins”).

### 5.2 `execution.config.json`

| Field | Type | Meaning |
|-------|------|---------|
| `enabled` | bool | Master switch |
| `max_runs_per_stream` | int | Retention per stream (ModelBA: 50) |
| `max_messages_per_step` | int | Cap; `≤0` = unlimited (ModelBA: 500) |
| `max_methods_per_step` | int | Optional stack/method sample |
| `max_feedback_per_step` | int | Open feedback notes copied into step |
| `global_notes` | string\|string[] | Attached to every step (ModelBA: `comentarios_tester`) |

### 5.3 DB — `executions.json`

```json
{
  "schema_version": 1,
  "project_id": "model-checker-ba",
  "runs": [
    {
      "execution_id": "1909cd0067864d07b60a40c778799698",
      "timestamp_utc": "2026-08-31T21:47:04.001Z",
      "identity": {
        "stream": "C20MCB-100",
        "commit": "6320aacd",
        "app_version": "1.1.4",
        "source": "local"
      },
      "subject": {
        "title": "029-013-019-CA-VEDIA 2343_RV27",
        "uri": "C:\\...\\file.rvt"
      },
      "steps": [
        {
          "step_id": "CU 6.2.1",
          "group_id": "6.2",
          "kind": "check",
          "label": "optional human title",
          "implementation": "VerificacionCorredoresAltos",
          "status": "fail",
          "pass": false,
          "duration_ms": 220,
          "messages": ["…finding text…"],
          "methods": ["VerificacionCorredoresAltos.Verificar"],
          "artifacts": [
            { "role": "log", "uri": "file:///C:/Users/.../CU 6.2.1_....txt" },
            { "role": "result", "uri": "file:///C:/Users/.../resultado_verificacion.json" }
          ],
          "feedback_open": [
            { "id": "queja-1", "text": "…", "state": "open" }
          ],
          "notes": [],
          "meta": {}
        }
      ]
    }
  ]
}
```

**ModelBA field map**

| Portable | ModelBA JSON |
|----------|--------------|
| `execution_id` | `run_id` |
| `identity.stream` | `branch` |
| `identity.commit` | `commit` |
| `subject.title/uri` | `model.title/path` |
| `steps` | `validaciones` |
| `step_id` | `subarticle_id` |
| `group_id` | `article_id` |
| `implementation` | `clase` |
| `status` / `pass` | `estado` / `cumple` |
| `messages` | `incumplimientos` |
| `methods` | `archivos_y_metodos` |
| `artifacts[log].uri` | `log_path` |
| `artifacts[result].uri` | `resultado_json_path` |
| `feedback_open` | `feedback_cliente` |

**Important ModelBA limitation to fix in the agnostic design:** domain objects have `Elemento`, `ValorMedido`, `ValorRequerido`, etc., but analytics stores **only truncated description strings**. Prefer portable `messages` as objects when possible:

```json
{
  "text": "…",
  "element_ref": "optional",
  "measured": "optional",
  "required": "optional",
  "severity": "optional"
}
```

Back-compat: string messages remain valid.

### 5.4 Index — `executions.index.json`

```json
{
  "schema_version": 1,
  "by_stream": {
    "C20MCB-100": {
      "CU 6.2.1": {
        "total": 6,
        "pass": 0,
        "fail": 4,
        "review": 0,
        "skipped": 2,
        "error": 0,
        "last_execution_id": "…",
        "last_subject": "…",
        "last_status": "fail",
        "last_log_uri": "…",
        "last_timestamp_utc": "…"
      }
    }
  }
}
```

Rebuild on every `complete()`. Agents query `by_stream[stream][step_id]` first.

### 5.5 Feedback — `feedback_by_step.json`

Keyed by `step_id`:

```json
{
  "CU 6.2.1": {
    "ticket": "optional",
    "normative": ["…"],
    "limitations": ["…"],
    "complaints": [
      {
        "id": "stable-id",
        "state": "open|closed|out_of_scope|not_delivered",
        "closed_in": "optional milestone id",
        "text": "…",
        "expected": "…"
      }
    ],
    "tester_notes": []
  }
}
```

**Only `open` complaints** are copied into the run step at record time (ModelBA behavior). Normative/limitations stay in the feedback file for on-demand agent reads.

Avoid product-specific states like `cerrado_en_82` in the agnostic schema — use `closed` + `closed_in`.

### 5.6 `execution.last_status.txt` (one line)

```
2026-09-04T15:20:17Z reason=ok stream=C20MCB-100 commit=a88f1faf execution_id=…; n=7; messages_stored=1; db=…/executions.json; report=…/report
```

Reasons to support: `ok`, `disabled`, `session_started`, `no_session`, `io_error`, plus report-mirror reasons in a sibling file.

### 5.7 Report mirror stamp fields

When publishing local seed / before eReport POST, stamp:

- `lastExecutionId` / `lastAnalyticsRunId`
- `Branch` or `stream`
- `Commit`
- `Stamp` (`yyyyMMdd_HHmmss`)

Keep the Issue Tracker payload shape required by eReport (`sections[].groups[].items[]`, statuses `aprobado|reprobado|no_aplica|""`).

---

## 6. Write path (API for hosts)

### Core API (language-agnostic)

```text
begin(subject) -> session | null
record(session, step_result) -> void
complete(session, optional_raw_results) -> void
is_enabled() -> bool
reset_enabled_cache() -> void
```

### When to call (ModelBA reference)

| Host event | Call |
|------------|------|
| Process / add-in startup | `identity.refresh_and_publish()` |
| Start batch | `begin(subject)` |
| After each unit (success or catch) | `record(...)` |
| End batch (even cancel) | `complete(...)` |

### Record algorithm (reference)

1. If session null → return.
2. Extract messages (cap `max_messages_per_step`; `≤0` = all).
3. Optionally parse verbose log for method names (`ENTER …` pattern in ModelBA).
4. Resolve open feedback for `step_id`.
5. Copy/locate verbose log into a stream-scoped folder; store URI on step.
6. Append step to session (memory only until complete).

### Complete algorithm (reference)

1. Persist run into `executions.json` (atomic).
2. Trim to `max_runs_per_stream` for that identity stream.
3. Rebuild index.
4. Export per-step result JSON (optional).
5. Write aggregate stream log (optional).
6. `ReportMirror.publish(session)`.
7. Write `last_status reason=ok`.

Corrupt DB → rename to `executions.bad-<timestamp>.json` and start fresh (ModelBA pattern).

---

## 7. Read path for agents (mandatory discipline)

**Never** open full `executions.json` into the LLM context first.

### Ordered protocol

1. **`execution.last_status.txt`**
   - `disabled` → `execution: N/A`
   - `io_error` → treat as unhealthy; do not invent outcomes
   - `ok` → continue
2. **`identity.json`** — confirm stream/commit under test (“last executed”).
3. **`executions.index.json`** → `by_stream[stream][step_id]`
   - Missing key → `execution: INSUFICIENTE` for that step
4. **`feedback_by_step.json`** → **only that `step_id` key**
5. Filter `executions.json` for last ≤10 runs matching stream + step (or load by `last_execution_id` only)
6. Open `artifacts` URIs on demand (grep log for ENTER/RESULT; don’t paste entire HTML)
7. Optionally `report/seeds_manifest.json` + stamped seeds

### Required agent output before coding / closing

Emit a short digest (≤15 lines), e.g.:

```text
### Execution digest
stream=… commit=… execution_id=…
step_id=CU 6.2.1 status=fail messages=6
last_log=…
feedback_open=1
evidence: INSUFICIENTE|OK|N/A
```

This matches ModelBA AGENT_SPEC / closeout analytics culture.

---

## 8. Local vs web — how agents log and see themselves

### 8.1 Local (desktop / Revit / CI machine)

| Action | How |
|--------|-----|
| Enable | Create `execution.enabled` **or** `"enabled": true` in config |
| Write | Host calls begin/record/complete → files under `{root}` |
| Read | Agent reads files on disk (index-first) |
| Update eReport | Agent runs connector after IT |

**Connector (existing):**

```bash
python .ereport/ereport_client.py docs
python .ereport/ereport_client.py request GET /api/v1/ereport/access
python .ereport/ereport_client.py request GET '/api/v1/ereport/orgs/{orgId}/reports/{reportId}'
# merge evidence into payload
python .ereport/ereport_client.py request POST '/api/v1/ereport/orgs/{orgId}/reports/{reportId}' --file body.json
```

Body modes (live docs):

- **`mode: "append"`** (default): add new open items only; new items need non-empty `incidencia` + `status: "reprobado"`.
- **`mode: "replace"`**: full seed bootstrap (`confirmOverwrite: true`); allows mixed statuses.

### 8.2 Web (agent running in cloud / Eduardo OS)

| Action | How |
|--------|-----|
| Write | `POST /executions` (proposed) with portable run JSON; or write sidecar under report media |
| Read | `GET /executions?stream=&step_id=` or `GET /executions/{id}` + index endpoint |
| Update eReport | Same Issue Tracker POST; map `fail|review` → new `reprobado` items; never invent closes without evidence |

**Agent self-visibility loop**

```
run work → log execution (local or web)
     → read own last execution_id + step outcomes
     → diff vs eReport open items
     → POST append (new opens) or replace (controlled seed sync)
     → print viewUrl
```

### 8.3 What “web logging” is *not* in ModelBA today

ModelBA does **not** upload analytics to Eduardo OS automatically. Telemetry HTML under `Model Checker BA Procesos` is local HTML. DualLogger mirrors steps into local `.txt`. Remote sync is **agent/human via eReport API**.

The agnostic kit should make that bridge **first-class** (optional auto-push), not pretend ModelBA already does it.

---

## 9. Mapping execution evidence → eReport items

### Rules

1. Prefer **append** for routine agent updates.
2. Use **replace** only for seed bootstrap / explicit full sync.
3. New append items: `incidencia` non-empty, `status: "reprobado"`.
4. Do not modify/delete existing item ids in append mode.
5. Preserve `fechaIncidencia` / `fechaSolucion`, `validationCriteria`, `criteriaStatus`, untouched items.
6. Stamp report meta with `lastExecutionId`, stream, commit.
7. Always print `Ver reporte: <viewUrl>`.
8. Never print API keys.

### Suggested mapping from a failed step

```json
{
  "id": "exec-<execution_id_prefix>-<step_id_slug>",
  "nombre": "<step_id> <short label>",
  "incidencia": "<joined messages or first N + count>",
  "solucion": "",
  "status": "reprobado",
  "fechaIncidencia": "<YYYY-MM-DD>",
  "fechaSolucion": "",
  "imagesIncidencia": [],
  "imagesSolucion": []
}
```

Idempotency: stable ids from `(step_id, complaint_id)` or hash of `(stream, step_id, message_fingerprint)` so re-runs don’t spam duplicates — **or** check existing open items before append.

### Closing items

API-key append **cannot** flip `reprobado` → `aprobado`. Closing requires:

- `mode: "replace"` with full payload, or
- JWT web editor, or
- a future PATCH/close endpoint (out of scope unless Eduardo OS adds it).

Agents should therefore treat execution `pass` as **evidence to propose closes**, not silent closes via append.

---

## 10. Extraction plan (from ModelBA → reusable kit)

### Phase 0 — Document (this spec)

Done when agents can follow local read protocol + eReport update without reading C#.

### Phase 1 — Portable schema + CLI adapter (no Revit)

Deliverables:

- JSON Schema files for `executions`, `index`, `identity`, `config`, `feedback`
- Python CLI next to `.ereport/`:
  - `execution_log.py ingest-modelba` — read Public ModelBA analytics → emit portable `executions.json`
  - `execution_log.py digest --stream --step-id`
  - `execution_log.py to-ereport --mode append|replace` — map opens → POST body
- Tests with fixtures from real anonymized runs

### Phase 2 — Library core (any one language first)

- begin/record/complete, atomic IO, retention, index rebuild
- Host adapter interface: `ISubject`, `IStepResult`, `IVerboseLogLocator`
- ModelBA adapter wraps existing C# as a thin façade **or** gradually replace internals

### Phase 3 — Web endpoints on Eduardo OS

- Store portable executions under owner filesystem
- List/filter by `project_id`, `stream`, `step_id`
- Auth: same API key entitlements as eReport
- Rate limit; append-only executions (executions are evidence — prefer immutability)

### Phase 4 — Auto-bridge (optional)

- After `complete()`, if config `ereport.auto_push: true`, call connector with append of new fails
- Never auto-replace without explicit config

### What to leave behind (ModelBA-only)

- `HexagonMultivista\ModelCheckerBA` paths
- Revit `Document`, `IVerificacionNormativa`
- CE/CU enums as required core types (ok inside `meta` / adapter)
- `cerrado_en_82`-style campaign states
- Installer Inno `onlyifdoesntexist` quirks (document: config updates need migration notes)
- Assuming repo `UI/Resources/analytics/` is live evidence (**it is not** — Public Documents is)

---

## 11. Security, privacy, ops

- Fail-soft: no secrets in execution logs; redact API keys if bridging.
- Artifacts may contain model paths / PII — treat local logs as sensitive; web upload should allow redaction hooks.
- Atomic writes; file lock around DB.
- History: report mirror snapshots max ~50 (ModelBA); eReport server history max 50 snapshots.
- Rate limit remote calls (60 req/min/key).

---

## 12. Acceptance criteria for “agents can see themselves and update eReport”

- [ ] Agent shows consent prompt and records ACCEPT or REJECT before any `enable`.
- [ ] ACCEPT → agent can enable local logging; standing rules include detailed ledger ingest/digest.
- [ ] REJECT → no ledger; agent may still sync eReport via API without execution logging.
- [ ] After a run, `last_status` shows `ok` with `execution_id`.
- [ ] Index answers “last status for step_id under stream” without full DB load.
- [ ] Digest ≤15 lines produced from index + one run slice.
- [ ] Same portable JSON round-trips local ↔ (future) web GET/POST.
- [ ] Agent maps `fail|review` → eReport append `reprobado` with viewUrl printed.
- [ ] Agent can bootstrap full seed via `mode=replace` when explicitly requested.
- [ ] Mis-tagged identity (install stamp beating feature binary) cannot happen: last-executed wins.
- [ ] Logging failure never fails the host workflow.

---

## 13. ModelBA file index (for implementers extracting code)

| File | Role |
|------|------|
| `ModelCheckerBA.Common/Utilities/MiscellaneousHelpers/IntegrationAnalyticsService.cs` | Core ledger |
| `ModelCheckerBA.Common/Utilities/MiscellaneousHelpers/BuildInfo.cs` | Identity last-executed |
| `ModelCheckerBA.Common/Utilities/MiscellaneousHelpers/QaReportAnalyticsPublisher.cs` | Seed / `.ereport` / HTML mirror |
| `ModelCheckerBA.Common/Utilities/MiscellaneousHelpers/LoggerProviderService.cs` | Verbose `.txt` |
| `ModelCheckerBA.Common/Utilities/MiscellaneousHelpers/ManagedWorkflowV2/Telemetry.cs` | Local HTML telemetry |
| `ModelCheckerBA.Common/Core/VerificationEngine.cs` | begin/record/complete call sites |
| `ModelCheckerBA.Common/Core/Incumplimiento.cs` / `ResultadoVerificacion.cs` | Domain results (flatten into messages) |
| `ModelCheckerBA.Common/UI/Resources/analytics/*` | Installer seeds (not live IT) |
| `scripts/Write-BuildInfo.ps1` + `Directory.Build.targets` | Emit DLL-local buildinfo |
| `CurrentTask/PROMPT_Analytics_store_all_incumplimientos_C20MCB-82.md` | Cap semantics |
| `CurrentTask/PROMPT_BuildInfo_last_executed_wins_C20MCB-82.md` | Identity law |
| `CurrentTask/PROMPT_reviewer_closeout_wave6_analytics.md` | Agent read discipline |
| `.ereport/ereport_client.py` + `docs.catalog.json` | Remote Issue Tracker |

---

## 14. One-page agent cheat sheet

```text
LOCAL READ
  1) {root}/execution.last_status.txt
  2) {root}/identity.json
  3) {root}/executions.index.json → by_stream[stream][step_id]
  4) feedback_by_step.json[step_id] only
  5) slice executions.json (≤10) or single execution_id
  6) open artifacts URIs only as needed

LOCAL WRITE (host)
  identity.refresh → begin → record* → complete → report mirror

WEB / EREPORT
  docs → access → get report
  map fail/review → new reprobado items (append)
  or full seed (replace + confirmOverwrite)
  print Ver reporte: <viewUrl>

NEVER
  load full DB into chat
  trust repo UI/Resources analytics over {root}
  auto-close issues via append
  print API keys
  abort host work on log IO failure
```

---

## 15. Suggested next implementation tickets

1. **Spec freeze:** this file (`EXECUTION_LOG.md`) + skill reference in the connector.
2. **CLI (local):** `execution_log.py` under `.ereport/` — enable / identity / ingest / digest / to-ereport → then `ereport_client.py` POST append|replace.
3. **~~API on Eduardo OS~~:** **Rejected** — execution ledger is local to the implementing project’s `.ereport/execution/`, not server media.
4. **Skill update:** teach agents the local read protocol + append/replace rules.
5. **Optional C# façade:** ModelBA `IntegrationAnalyticsService` exports portable JSON into `.ereport/execution/`.
6. **Phase 4 auto-bridge (optional):** after ingest, if config `ereport.auto_push: true`, call connector append — never auto-replace.

End of specification.
