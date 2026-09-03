# Eduardo OS eReport connector

Silent sidecar for any project: clone this repo as **`.ereport/`** at your project root. Keeps your tree clean while agents sync Issue Tracker reports via the public API.

## Install (recommended)

From your project root:

```bash
git clone --depth 1 https://github.com/EduardoOsteicoechea/eduardoos-ereport-connector.git .ereport
```

Or run the installer (also wires the Cursor skill):

```bash
# Unix
curl -fsSL https://raw.githubusercontent.com/EduardoOsteicoechea/eduardoos-ereport-connector/main/install.sh | bash

# Windows PowerShell (from project root)
irm https://raw.githubusercontent.com/EduardoOsteicoechea/eduardoos-ereport-connector/main/install.ps1 | iex
```

Then:

```bash
cp .ereport/.env.example .ereport/.env   # edit: API key + org/report ids
```

**Consumer gitignore (suggested):**

```gitignore
.ereport/.env
.ereport/report.payload.json
```

Optional: ignore the whole `.ereport/` folder and clone per machine, or add it as a git submodule.

> `.ereport/` is a **directory** (this connector). A `*.ereport` **file** is a report payload export — different things.

## Cursor skill

After install, skill files live at `.ereport/skill/eduardoos-ereport/`.  
Installers copy them to `.cursor/skills/eduardoos-ereport/` so Cursor can load skill `eduardoos-ereport`.

Read **CAVEATS** before Mode B/C: `.ereport/skill/eduardoos-ereport/CAVEATS.md`

## CLI

```bash
cd .ereport
python ereport_client.py access
python ereport_client.py orgs
python ereport_client.py org-reports
python ereport_client.py get
python ereport_client.py put --file report.payload.json
```

Docs: https://eduardoos.com/api-docs  
Catalog: https://eduardoos.com/api/v1/docs

## License

MIT — see [LICENSE](LICENSE).
