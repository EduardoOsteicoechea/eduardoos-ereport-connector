# Local execution ledger (consumer project)

When this connector is cloned as `.ereport/` inside **your** product repo:

## Consent first

Agents **must** ask you to **ACCEPT** or **REJECT** detailed logging before enabling:

```bash
python ../execution_log.py prompt
python ../execution_log.py accept   # or reject
python ../execution_log.py enable   # requires accept
```

- **Accept** → ledger files below are used; the agent must log runs in detail (fail-soft).
- **Reject** → no ledger; the agent may still update the remote Issue Tracker without this extension.

## Layout (after accept + enable)

```
.ereport/execution/
  execution.consent.json
  execution.enabled
  execution.config.json
  identity.json
  executions.json
  executions.index.json
  last_status.txt
```

- **Consumer repo:** may commit or gitignore this folder (your choice).
- **Connector upstream:** runtime files under `execution/` are gitignored — do not push analytics into the connector development repo.

CLI: `python execution_log.py …`  
Spec: `EXECUTION_LOG.md`
