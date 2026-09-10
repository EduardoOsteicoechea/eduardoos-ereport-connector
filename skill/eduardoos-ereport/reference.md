# eReport API reference (connector)

**Source of truth:** `GET https://eduardoos.com/api/v1/docs` (no auth).  
**Before any API action:** run `python .ereport/ereport_client.py docs` and read `routes`, `agentGuidance`, and **`payloadSchema`**.

Base default: `https://eduardoos.com`  
Auth: `Authorization: Bearer eos_live_…` (required for all `/api/v1/ereport/*`)

## Ordered Issue Tracker flow

1. `GET /api/v1/docs`  
2. `GET /api/v1/ereport/access`  
3. `GET /api/v1/ereport/orgs`  
4. `GET /api/v1/ereport/orgs/{orgId}/reports`  
5. `GET /api/v1/ereport/orgs/{orgId}/reports/{reportId}` → `viewUrl`, `payload`  
6. `POST` same URL with:

```json
{
  "confirmOverwrite": true,
  "mode": "append",
  "tema": "optional",
  "payload": {}
}
```

| mode | Behavior |
|------|----------|
| `append` (default) | Merge only; existing ids immutable; new items = non-empty `incidencia` + `status: "reprobado"` |
| `replace` | Full payload replace; requires `confirmOverwrite: true`; mixed statuses OK |

## Local execution log (optional — user consent first)

**Not** on the Eduardo OS API. Under `.ereport/execution/` in the **consumer** project only after the user **ACCEPT**s.

```bash
python .ereport/execution_log.py prompt     # agent must show this to the user
python .ereport/execution_log.py accept     # or: reject
python .ereport/execution_log.py enable     # blocked until accept
python .ereport/execution_log.py ingest|digest|to-ereport
```

| Consent | Meaning |
|---------|---------|
| `accept` | Agent must incorporate detailed ledger logging into its standing rules |
| `reject` | No ledger; agent may still POST Issue Tracker updates without execution logging |

See `EXECUTION_LOG.md` and skill **Mandatory: execution-logging consent**. Do not upload the ledger to the connector development remote.

## Thin CLI

```bash
python .ereport/ereport_client.py docs
python .ereport/ereport_client.py request METHOD /path [--file body.json]
```

Bare `.ereport` payload files auto-wrap as `{confirmOverwrite:true, payload:…}` on report POST (still defaults to append unless the JSON includes `"mode":"replace"`).

## viewUrl

`{BASE}/ereport/workspace?user={ownerSafe}&org={orgId}&report={reportId}`
