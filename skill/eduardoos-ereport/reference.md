# eReport API reference (connector)

Base default: `https://eduardoos.com`  
Auth: `Authorization: Bearer eos_live_…`

## Ordered endpoints

1. `GET /api/v1/ereport/access`  
2. `GET /api/v1/ereport/orgs`  
3. `GET /api/v1/ereport/orgs/{orgId}/reports`  
4. `GET /api/v1/ereport/orgs/{orgId}/reports/{reportId}` → `viewUrl`, `payload`, …  
5. `POST /api/v1/ereport/orgs/{orgId}/reports/{reportId}`  
   Body: `{ "confirmOverwrite": true, "payload": { /* full */ }, "tema"?: "…" }`

Catalog: `GET /api/v1/docs` (no auth). Keys: UI only.

## viewUrl

`{BASE}/ereport/workspace?user={ownerSafe}&org={orgId}&report={reportId}`

## Item fields

`id`, `status` (`aprobado`|`reprobado`|`no_aplica`), `nombre`, `incidencia`, `solucion`,
`fechaIncidencia`, `fechaSolucion`, `images`, `imagesIncidencia`, `imagesSolucion`.
