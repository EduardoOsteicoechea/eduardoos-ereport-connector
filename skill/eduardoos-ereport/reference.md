# eReport API reference (connector)

**Source of truth:** `GET https://eduardoos.com/api/v1/docs` (no auth).  
Read `routes`, `agentGuidance`, and **`payloadSchema`** before crafting requests.

Base default: `https://eduardoos.com`  
Auth: `Authorization: Bearer eos_live_…` (required for all `/api/v1/ereport/*`)

## Ordered flow (from catalog)

1. `GET /api/v1/docs` — catalog + payloadSchema  
2. `GET /api/v1/ereport/access`  
3. `GET /api/v1/ereport/orgs`  
4. `GET /api/v1/ereport/orgs/{orgId}/reports`  
5. `GET /api/v1/ereport/orgs/{orgId}/reports/{reportId}` → `viewUrl`, `payload`  
6. `POST /api/v1/ereport/orgs/{orgId}/reports/{reportId}`  
   Body: `{ "confirmOverwrite": true, "payload": { /* full .ereport */ }, "tema"?: "…" }`

## Thin CLI

```bash
python .ereport/ereport_client.py docs
python .ereport/ereport_client.py request METHOD /path [--file body.json]
```

Path may use `{orgId}` / `{reportId}` placeholders filled from `.env`.

## Payload (summary — prefer catalog.payloadSchema)

Root: `orgName`, `reportName`, `appTitle`, `reportDate`, `reportNumber` (Report Code),
`validationCriteria[]`, `theme`, `sections[]`.

Item: `id`, `nombre`, `incidencia`, `solucion`, dates, images,
`status` (`aprobado`|`reprobado`|`no_aplica`|`""`),
`criteriaStatus` map label → same status values.

Effective status rules and Report Code formula live in `payloadSchema`.

## viewUrl

`{BASE}/ereport/workspace?user={ownerSafe}&org={orgId}&report={reportId}`
