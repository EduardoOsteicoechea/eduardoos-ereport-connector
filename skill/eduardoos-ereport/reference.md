# eReport API reference (connector)

**Source of truth:** `GET https://eduardoos.com/api/v1/docs` (no auth).  
**Before any API action:** run `python .ereport/ereport_client.py docs` and read `routes`, `agentGuidance`, and **`payloadSchema`**.

Base default: `https://eduardoos.com`  
Auth: `Authorization: Bearer eos_live_…` (required for all `/api/v1/ereport/*`)

## Website registration + site Connector

Live catalog keys: `payloadSchema.ereport.websiteRegistration`, `payloadSchema.ereport.webConnector.features`, `errors.website_registration_exists`.

| Surface | Behavior |
|---------|----------|
| Hub create | `purpose` / `firstReportPurpose`: `website_registration` \| `other` (default `other`) |
| Cookie access | `GET /api/ereport/access` → `websiteRegistration: { orgId, reportId, tema } \| null` |
| Site chrome | Menu **Connector** + header **bug_report** (left of menu) only when entitlement + binding |
| Quick modal | Add-only issues; parse `nombre` until first `.` |
| Settings modal | Gear opens settings dialog; section/group defaults in `localStorage` key `ereport.connector.defaults` |
| Advanced | `/ereport/web-connector`; save alerts on node create/save |
| CLI `.env` | `EDUARDOOS_ORG_ID` / `EDUARDOOS_REPORT_ID` → website_registration report |
| API scope | Key routes still reach **all** owned orgs/reports (UI lock only) |

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

### Granular nodes (web connector / quick modal)

- `POST …/reports/{reportId}/sections`
- `PATCH …/sections/{sectionId}`
- `POST …/sections/{sectionId}/groups`
- `PATCH …/groups/{groupId}`
- `POST …/groups/{groupId}/items`
- `PATCH …/items/{itemId}`

Same paths under cookie `/api/ereport/...` for the site UI.

### Web embed

- Loader: `https://eduardoos.com/ereport/embed.js`
- Theme: `https://eduardoos.com/ereport/embed-theme.css`
- Mount: `EduardoOSEreport.mount({ orgId, reportId, menuSelector })`

## Local execution log (optional — user consent first)

**Not** on the Eduardo OS API. Under `.ereport/execution/` in the **consumer** project only after the user **ACCEPT**s.

```bash
python .ereport/execution_log.py prompt     # agent must show this to the user
python .ereport/execution_log.py accept     # or: reject
python .ereport/execution_log.py enable     # blocked until accept
python .ereport/execution_log.py ingest|digest|to-ereport
```

See `EXECUTION_LOG.md` and skill **Mandatory: execution-logging consent**.

## Thin CLI

```bash
python .ereport/ereport_client.py docs
python .ereport/ereport_client.py request METHOD /path [--file body.json]
```

`viewUrl`: `{BASE}/ereport/workspace?user={ownerSafe}&org={orgId}&report={reportId}`
