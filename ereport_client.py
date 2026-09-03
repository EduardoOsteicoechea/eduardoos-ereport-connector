#!/usr/bin/env python3
"""Eduardo OS eReport API client — run from the .ereport/ sidecar (one command at a time)."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parent


def load_env() -> None:
    path = ROOT / ".env"
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def cfg() -> dict[str, str]:
    load_env()
    base = os.environ.get("EDUARDOOS_BASE_URL", "https://eduardoos.com").rstrip("/")
    return {
        "base": base,
        "key": os.environ.get("EDUARDOOS_API_KEY", "").strip(),
        "org": os.environ.get("EDUARDOOS_ORG_ID", "").strip(),
        "report": os.environ.get("EDUARDOOS_REPORT_ID", "").strip(),
    }


def request(method: str, path: str, body: dict[str, Any] | None = None) -> Any:
    c = cfg()
    if not c["key"]:
        print("Missing EDUARDOOS_API_KEY in .env", file=sys.stderr)
        sys.exit(2)
    url = c["base"] + path
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {c['key']}")
    req.add_header("X-Correlation-ID", str(uuid4()))
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        retry = e.headers.get("Retry-After")
        msg = f"HTTP {e.code}: {detail}"
        if e.code == 429 and retry:
            msg += f" (Retry-After: {retry})"
        print(msg, file=sys.stderr)
        sys.exit(1)


def print_view(data: dict[str, Any]) -> None:
    view = data.get("viewUrl")
    if not view:
        c = cfg()
        owner = data.get("ownerSafe") or ""
        org = data.get("orgId") or c["org"]
        report = data.get("reportId") or c["report"]
        if owner and org and report:
            view = f"{c['base']}/ereport/workspace?user={owner}&org={org}&report={report}"
    if view:
        print(f"Ver reporte: {view}")


def cmd_access(_: argparse.Namespace) -> None:
    out = request("GET", "/api/v1/ereport/access")
    print(json.dumps(out, indent=2, ensure_ascii=False))


def cmd_orgs(_: argparse.Namespace) -> None:
    out = request("GET", "/api/v1/ereport/orgs")
    for org in out.get("orgs") or []:
        print(f"{org.get('id')}\t{org.get('name')}")
    print(json.dumps({"ownerSafe": out.get("ownerSafe"), "count": len(out.get("orgs") or [])}, indent=2))


def cmd_org_reports(_: argparse.Namespace) -> None:
    c = cfg()
    if not c["org"]:
        print("Set EDUARDOOS_ORG_ID", file=sys.stderr)
        sys.exit(2)
    out = request("GET", f"/api/v1/ereport/orgs/{c['org']}/reports")
    for rep in out.get("reports") or []:
        print(f"{rep.get('id')}\t{rep.get('tema')}\t{rep.get('reportNumber')}")
    print(json.dumps({"orgId": out.get("orgId"), "orgName": out.get("orgName"), "count": len(out.get("reports") or [])}, indent=2))


def cmd_get(_: argparse.Namespace) -> None:
    c = cfg()
    if not c["org"] or not c["report"]:
        print("Set EDUARDOOS_ORG_ID and EDUARDOOS_REPORT_ID", file=sys.stderr)
        sys.exit(2)
    out = request("GET", f"/api/v1/ereport/orgs/{c['org']}/reports/{c['report']}")
    payload = out.get("payload")
    dest = ROOT / "report.payload.json"
    dest.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {dest}")
    print_view(out)


def cmd_put(args: argparse.Namespace) -> None:
    c = cfg()
    if not c["org"] or not c["report"]:
        print("Set EDUARDOOS_ORG_ID and EDUARDOOS_REPORT_ID", file=sys.stderr)
        sys.exit(2)
    path = Path(args.file)
    payload = json.loads(path.read_text(encoding="utf-8"))
    body = {"confirmOverwrite": True, "payload": payload}
    out = request("POST", f"/api/v1/ereport/orgs/{c['org']}/reports/{c['report']}", body)
    print(json.dumps({"snapshotId": out.get("snapshotId"), "tema": (out.get("meta") or {}).get("tema")}, indent=2))
    print_view(out)


def main() -> None:
    p = argparse.ArgumentParser(description="Eduardo OS eReport API client")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("access").set_defaults(func=cmd_access)
    sub.add_parser("orgs").set_defaults(func=cmd_orgs)
    sub.add_parser("org-reports").set_defaults(func=cmd_org_reports)
    sub.add_parser("get").set_defaults(func=cmd_get)
    put = sub.add_parser("put")
    put.add_argument("--file", required=True, help="JSON file with full .ereport payload object")
    put.set_defaults(func=cmd_put)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
