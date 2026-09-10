# Local execution ledger (consumer project)

When this connector is cloned as `.ereport/` inside **your** product repo, agent
runs are stored here:

```
.ereport/execution/
  execution.enabled
  execution.config.json
  identity.json
  executions.json
  executions.index.json
  last_status.txt
```

- **Consumer repo:** may commit or gitignore this folder (your choice).
- **Connector upstream** ([eduardoos-ereport-connector](https://github.com/EduardoOsteicoechea/eduardoos-ereport-connector)): runtime files under `execution/` are gitignored — do not push analytics into the connector development repo.

CLI: `python execution_log.py enable|ingest|digest|to-ereport`  
Spec: see `EXECUTION_LOG.md` in this repo.
