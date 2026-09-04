# eReport API reference (connector)

**Source of truth:** `GET https://eduardoos.com/api/v1/docs` (no auth).  
**Before any action:** run `python .ereport/ereport_client.py docs` and read `routes`, `agentGuidance`, and **`payloadSchema`**.

Base default: `https://eduardoos.com`  
Auth: `Authorization: Bearer eos_live_…` (required for all `/api/v1/ereport/*`)

## Ordered flow (from catalog)

1. `GET /api/v1/docs` — catalog + payloadSchema  
2. `GET /api/v1/ereport/access`  
3. `GET /api/v1/ereport/orgs`  
4. `GET /api/v1/ereport/orgs/{orgId}/reports`  
5. `GET /api/v1/ereport/orgs/{orgId}/reports/{reportId}` → `viewUrl`, `payload`  
6. `POST /api/v1/ereport/orgs/{orgId}/reports/{reportId}`  
   Body: `{ "confirmOverwrite": true, "payload": { /* stored + new open issues */ }, "tema"?: "…" }`  
   Server **merges** additively (cannot change existing item ids).

## Thin CLI

```bash
python .ereport/ereport_client.py docs
python .ereport/ereport_client.py request METHOD /path [--file body.json]
```

## Payload (summary — prefer catalog.payloadSchema)

Root: `orgName`, `reportName`, `appTitle`, `reportDate`, `reportNumber`,
`validationCriteria[]`, `theme`, `sections[]`.

Item: `id`, `nombre`, `incidencia`, `solucion`, dates, images,
`status`, `criteriaStatus`.

**New API items:** `incidencia` non-empty + `status: "reprobado"`.  
**Existing items:** do not modify (400).

## viewUrl

`{BASE}/ereport/workspace?user={ownerSafe}&org={orgId}&report={reportId}`
