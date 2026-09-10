#!/usr/bin/env python3
"""Local agent execution log for the .ereport sidecar (host-agnostic).

Stores runs under ``.ereport/execution/`` inside the **consumer project** that
cloned this connector. Runtime data is gitignored in the connector upstream
repo so developers never push host analytics into eduardoos-ereport-connector.

Agents must read index-first (status → identity → index → one run). Use
``to-ereport`` to build an append/replace POST body for the Issue Tracker API;
this module never uploads secrets and never talks to the connector's own remote.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parent
EXEC_DIR = ROOT / "execution"
CONSENT_PATH = EXEC_DIR / "execution.consent.json"
SCHEMA_VERSION = 1
MAX_RUNS_PER_STREAM = 50
MAX_MESSAGES_PER_STEP = 500
STATUS_OK = frozenset({"pass", "fail", "review", "skipped", "error"})

# Shown by agents before asking the user to accept/reject logging.
CONSENT_PROMPT = """\
eReport execution logging (optional extension)
----------------------------------------------
If you ACCEPT, this project will keep a detailed local ledger under
.ereport/execution/ (identity, runs, index, digests). The agent must then
log work in that ledger (fail-soft) and may map fail/review → eReport append.
Data stays in YOUR project’s .ereport/; it is not uploaded to the connector
upstream repo and is separate from the Issue Tracker API.

If you REJECT, the agent will NOT enable the ledger. It may still sync the
Issue Tracker report via the API (append/replace) using its own workflow.

Reply clearly: ACCEPT logging  |  REJECT logging
"""


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _atomic_write(path: Path, data: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, str):
        raw = data.encode("utf-8")
    else:
        raw = data
    fd, tmp = tempfile.mkstemp(prefix="ereport-exec-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(raw)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _write_json(path: Path, obj: Any) -> None:
    _atomic_write(path, json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def _read_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        bad = path.with_name(path.stem + f".bad-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}" + path.suffix)
        try:
            path.rename(bad)
        except OSError:
            pass
        return default


def _sanitize(text: str) -> str:
    t = (text or "").strip()
    low = t.lower()
    if "eos_live_" in low or "authorization: bearer" in low:
        return "[redacted]"
    return t


def _slug(s: str) -> str:
    out = re.sub(r"[^a-zA-Z0-9._-]+", "-", (s or "").strip().lower()).strip("-")
    return out[:48] or "step"


def consent_state() -> str:
    """Return accepted | rejected | unset."""
    data = _read_json(CONSENT_PATH, {})
    if not isinstance(data, dict):
        return "unset"
    choice = str(data.get("logging") or "").strip().lower()
    if choice in ("accepted", "rejected"):
        return choice
    return "unset"


def write_consent(choice: str, note: str = "") -> dict[str, Any]:
    choice = choice.strip().lower()
    if choice not in ("accepted", "rejected"):
        raise ValueError("choice must be accepted or rejected")
    EXEC_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "logging": choice,
        "decided_at_utc": _utc_now(),
        "note": (note or "").strip(),
        "prompt_version": 1,
    }
    _write_json(CONSENT_PATH, payload)
    if choice == "rejected":
        cfg_path = EXEC_DIR / "execution.config.json"
        cfg = _read_json(cfg_path, {})
        if not isinstance(cfg, dict):
            cfg = {}
        cfg["enabled"] = False
        _write_json(cfg_path, cfg)
        flag = EXEC_DIR / "execution.enabled"
        if flag.is_file():
            try:
                flag.unlink()
            except OSError:
                pass
        write_last_status(f"{_utc_now()} reason=disabled consent=rejected")
    return payload


def ensure_enabled() -> bool:
    if consent_state() == "rejected":
        return False
    if consent_state() != "accepted":
        return False
    flag = EXEC_DIR / "execution.enabled"
    cfg = _read_json(EXEC_DIR / "execution.config.json", {})
    if flag.is_file():
        return True
    if isinstance(cfg, dict) and cfg.get("enabled") is True:
        return True
    if isinstance(cfg, dict) and cfg.get("enabled") is False:
        return False
    return False


def require_accepted_consent() -> None:
    state = consent_state()
    if state == "accepted":
        return
    if state == "rejected":
        print(
            "Execution logging was REJECTED by the user. "
            "Do not enable the ledger; sync eReport without detailed logging.",
            file=sys.stderr,
        )
        sys.exit(3)
    print(CONSENT_PROMPT, file=sys.stderr)
    print(
        "No consent on file. Ask the user to ACCEPT or REJECT, then run:\n"
        "  python execution_log.py accept\n"
        "  python execution_log.py reject",
        file=sys.stderr,
    )
    sys.exit(2)


def write_last_status(line: str) -> None:
    try:
        _atomic_write(EXEC_DIR / "last_status.txt", line.strip() + "\n")
    except OSError:
        pass


def load_db() -> dict[str, Any]:
    db = _read_json(EXEC_DIR / "executions.json", {"schema_version": SCHEMA_VERSION, "runs": []})
    if not isinstance(db, dict):
        db = {"schema_version": SCHEMA_VERSION, "runs": []}
    db.setdefault("schema_version", SCHEMA_VERSION)
    db.setdefault("runs", [])
    return db


def rebuild_index(db: dict[str, Any]) -> dict[str, Any]:
    by_stream: dict[str, dict[str, Any]] = {}
    for run in db.get("runs") or []:
        stream = ((run.get("identity") or {}).get("stream") or "default").strip() or "default"
        by_stream.setdefault(stream, {})
        for st in run.get("steps") or []:
            sid = (st.get("step_id") or "").strip()
            if not sid:
                continue
            cur = by_stream[stream].get(sid) or {
                "total": 0, "pass": 0, "fail": 0, "review": 0, "skipped": 0, "error": 0,
            }
            status = (st.get("status") or "").lower()
            cur["total"] += 1
            if status in cur:
                cur[status] += 1
            cur["last_execution_id"] = run.get("execution_id")
            cur["last_subject"] = (run.get("subject") or {}).get("title")
            cur["last_status"] = status
            cur["last_timestamp_utc"] = run.get("timestamp_utc")
            for art in st.get("artifacts") or []:
                if art.get("role") == "log" and art.get("uri"):
                    cur["last_log_uri"] = art.get("uri")
                    break
            by_stream[stream][sid] = cur
    return {"schema_version": SCHEMA_VERSION, "by_stream": by_stream}


def trim_runs(runs: list[dict[str, Any]], max_per_stream: int = MAX_RUNS_PER_STREAM) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    kept: list[dict[str, Any]] = []
    for run in reversed(runs):
        stream = ((run.get("identity") or {}).get("stream") or "default").strip() or "default"
        if counts.get(stream, 0) >= max_per_stream:
            continue
        counts[stream] = counts.get(stream, 0) + 1
        kept.append(run)
    kept.reverse()
    return kept


def normalize_run(run: dict[str, Any]) -> dict[str, Any]:
    out = dict(run)
    eid = (out.get("execution_id") or "").strip() or uuid4().hex
    out["execution_id"] = eid
    out["timestamp_utc"] = (out.get("timestamp_utc") or "").strip() or _utc_now()
    identity = dict(out.get("identity") or {})
    identity["stream"] = (identity.get("stream") or "default").strip() or "default"
    for k in ("commit", "app_version", "source", "source_path"):
        if k in identity and isinstance(identity[k], str):
            identity[k] = _sanitize(identity[k])
    out["identity"] = identity
    subject = dict(out.get("subject") or {})
    for k in ("title", "uri"):
        if k in subject and isinstance(subject[k], str):
            subject[k] = _sanitize(subject[k])
    out["subject"] = subject
    steps_in = out.get("steps") or []
    if not steps_in:
        raise ValueError("steps required")
    steps: list[dict[str, Any]] = []
    for st in steps_in:
        step = dict(st)
        step["step_id"] = (step.get("step_id") or "").strip()
        if not step["step_id"]:
            raise ValueError("step_id required")
        status = (step.get("status") or "").lower().strip()
        if status not in STATUS_OK:
            status = "pass" if step.get("pass") else "fail"
        step["status"] = status
        step["pass"] = status == "pass"
        msgs = step.get("messages") or []
        norm_msgs: list[Any] = []
        for m in msgs:
            if len(norm_msgs) >= MAX_MESSAGES_PER_STEP:
                break
            if isinstance(m, str):
                t = _sanitize(m)
                if t:
                    norm_msgs.append(t)
            elif isinstance(m, dict):
                cp = {k: (_sanitize(v) if isinstance(v, str) else v) for k, v in m.items()}
                if str(cp.get("text") or "").strip():
                    norm_msgs.append(cp)
        step["messages"] = norm_msgs
        steps.append(step)
    out["steps"] = steps
    return out


def ingest_run(run: dict[str, Any]) -> dict[str, Any]:
    if not ensure_enabled():
        write_last_status(f"{_utc_now()} reason=disabled")
        print("execution logging disabled", file=sys.stderr)
        return {"disabled": True}
    try:
        run = normalize_run(run)
        db = load_db()
        for existing in db["runs"]:
            if existing.get("execution_id") == run["execution_id"]:
                raise ValueError(f"execution_id already exists: {run['execution_id']}")
        if run.get("project_id") and not db.get("project_id"):
            db["project_id"] = run["project_id"]
        db["runs"].append(run)
        db["runs"] = trim_runs(db["runs"])
        _write_json(EXEC_DIR / "executions.json", db)
        idx = rebuild_index(db)
        _write_json(EXEC_DIR / "executions.index.json", idx)
        msg_n = sum(len(s.get("messages") or []) for s in run["steps"])
        write_last_status(
            f"{_utc_now()} reason=ok stream={run['identity']['stream']} "
            f"commit={run['identity'].get('commit') or ''} execution_id={run['execution_id']}; "
            f"n={len(run['steps'])}; messages_stored={msg_n}; db=executions.json"
        )
        return run
    except Exception as e:
        write_last_status(f"{_utc_now()} reason=io_error {e}")
        raise


def publish_identity(identity: dict[str, Any]) -> dict[str, Any]:
    identity = dict(identity)
    identity["stream"] = (identity.get("stream") or "default").strip() or "default"
    for k in ("commit", "app_version", "source", "source_path"):
        if k in identity and isinstance(identity[k], str):
            identity[k] = _sanitize(identity[k])
    identity["published_at_utc"] = _utc_now()
    _write_json(EXEC_DIR / "identity.json", identity)
    return identity


def map_fail_to_items(run: dict[str, Any]) -> list[dict[str, Any]]:
    date = (run.get("timestamp_utc") or "")[:10]
    prefix = (run.get("execution_id") or "exec")[:12]
    items: list[dict[str, Any]] = []
    for st in run.get("steps") or []:
        status = (st.get("status") or "").lower()
        if status not in ("fail", "review", "error"):
            continue
        msgs = []
        for m in st.get("messages") or []:
            if isinstance(m, str):
                msgs.append(m)
            elif isinstance(m, dict) and m.get("text"):
                msgs.append(str(m["text"]))
        incidencia = "\n".join(msgs[:8]) or f"{st.get('step_id')} {status}"
        if len(msgs) > 8:
            incidencia += f"\n…+{len(msgs) - 8} more"
        items.append({
            "id": f"exec-{prefix}-{_slug(str(st.get('step_id')))}",
            "nombre": f"{st.get('step_id') or ''} {st.get('label') or ''}".strip(),
            "incidencia": incidencia,
            "solucion": "",
            "status": "reprobado",
            "fechaIncidencia": date,
            "fechaSolucion": "",
            "imagesIncidencia": [],
            "imagesSolucion": [],
        })
    return items


def cmd_prompt(_: argparse.Namespace) -> None:
    print(CONSENT_PROMPT)
    print(json.dumps({"consent": consent_state(), "path": str(CONSENT_PATH)}, indent=2))


def cmd_accept(args: argparse.Namespace) -> None:
    out = write_consent("accepted", note=getattr(args, "note", "") or "")
    print(json.dumps(out, indent=2))
    print("Next: python execution_log.py enable")


def cmd_reject(args: argparse.Namespace) -> None:
    out = write_consent("rejected", note=getattr(args, "note", "") or "")
    print(json.dumps(out, indent=2))
    print("Logging rejected — agent must sync eReport without the execution ledger.")


def cmd_consent(_: argparse.Namespace) -> None:
    print(json.dumps({"consent": consent_state(), "detail": _read_json(CONSENT_PATH, {})}, indent=2, ensure_ascii=False))


def cmd_enable(_: argparse.Namespace) -> None:
    require_accepted_consent()
    EXEC_DIR.mkdir(parents=True, exist_ok=True)
    (EXEC_DIR / "execution.enabled").write_text("", encoding="utf-8")
    cfg_path = EXEC_DIR / "execution.config.json"
    cfg = _read_json(cfg_path, {})
    if not isinstance(cfg, dict):
        cfg = {}
    cfg["enabled"] = True
    cfg.setdefault("max_runs_per_stream", MAX_RUNS_PER_STREAM)
    cfg.setdefault("max_messages_per_step", MAX_MESSAGES_PER_STEP)
    _write_json(cfg_path, cfg)
    write_last_status(f"{_utc_now()} reason=ok enabled consent=accepted")
    print(json.dumps({"enabled": True, "consent": "accepted", "root": str(EXEC_DIR)}, indent=2))


def cmd_status(_: argparse.Namespace) -> None:
    path = EXEC_DIR / "last_status.txt"
    line = path.read_text(encoding="utf-8").strip() if path.is_file() else ""
    print(json.dumps({"consent": consent_state(), "last_status": line or "reason=no_session"}, indent=2))


def cmd_identity(args: argparse.Namespace) -> None:
    if args.file:
        require_accepted_consent()
        identity = json.loads(Path(args.file).read_text(encoding="utf-8"))
        out = publish_identity(identity)
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return
    path = EXEC_DIR / "identity.json"
    if not path.is_file():
        print("identity missing — publish with --file", file=sys.stderr)
        sys.exit(1)
    print(path.read_text(encoding="utf-8"))


def cmd_ingest(args: argparse.Namespace) -> None:
    require_accepted_consent()
    run = json.loads(Path(args.file).read_text(encoding="utf-8"))
    if "execution" in run and isinstance(run["execution"], dict):
        run = run["execution"]
    out = ingest_run(run)
    print(json.dumps({"execution_id": out.get("execution_id"), "steps": len(out.get("steps") or []), "root": str(EXEC_DIR)}, indent=2))


def cmd_index(args: argparse.Namespace) -> None:
    path = EXEC_DIR / "executions.index.json"
    if not path.is_file():
        idx = rebuild_index(load_db())
        _write_json(path, idx)
    else:
        idx = _read_json(path, {"schema_version": SCHEMA_VERSION, "by_stream": {}})
    stream = (args.stream or "").strip()
    step_id = (args.step_id or "").strip()
    by = idx.get("by_stream") or {}
    if stream and step_id:
        print(json.dumps((by.get(stream) or {}).get(step_id) or {}, indent=2, ensure_ascii=False))
    elif stream:
        print(json.dumps(by.get(stream) or {}, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(idx, indent=2, ensure_ascii=False))


def cmd_digest(args: argparse.Namespace) -> None:
    """≤15-line agent digest (index-first)."""
    status_path = EXEC_DIR / "last_status.txt"
    status = status_path.read_text(encoding="utf-8").strip() if status_path.is_file() else "reason=no_session"
    if "reason=disabled" in status:
        print("### Execution digest\nevidence: N/A (disabled)")
        return
    if "reason=io_error" in status:
        print("### Execution digest\nevidence: INSUFICIENTE (io_error)")
        print(status)
        return
    identity = _read_json(EXEC_DIR / "identity.json", {})
    stream = (args.stream or identity.get("stream") or "default").strip()
    step_id = (args.step_id or "").strip()
    idx = _read_json(EXEC_DIR / "executions.index.json", rebuild_index(load_db()))
    step = ((idx.get("by_stream") or {}).get(stream) or {}).get(step_id) if step_id else None
    lines = [
        "### Execution digest",
        f"stream={stream} commit={identity.get('commit') or ''}",
    ]
    if step_id:
        if not step:
            lines.append(f"step_id={step_id} evidence: INSUFICIENTE")
        else:
            lines.append(
                f"step_id={step_id} status={step.get('last_status')} "
                f"execution_id={step.get('last_execution_id')} "
                f"fail={step.get('fail')} pass={step.get('pass')}"
            )
            lines.append(f"last_log={step.get('last_log_uri') or ''}")
            lines.append("evidence: OK")
    else:
        lines.append(f"last_status={status}")
        lines.append("evidence: OK (pass --step-id for step slice)")
    print("\n".join(lines[:15]))


def cmd_to_ereport(args: argparse.Namespace) -> None:
    require_accepted_consent()
    db = load_db()
    run = None
    if args.execution_id:
        for r in db.get("runs") or []:
            if r.get("execution_id") == args.execution_id:
                run = r
                break
        if not run:
            print("execution_id not found", file=sys.stderr)
            sys.exit(1)
    else:
        runs = db.get("runs") or []
        if not runs:
            print("no runs", file=sys.stderr)
            sys.exit(1)
        run = runs[-1]
    mode = (args.mode or "append").lower()
    items = map_fail_to_items(run)
    if mode == "append":
        body = {
            "confirmOverwrite": True,
            "mode": "append",
            "payload": {
                "lastExecutionId": run.get("execution_id"),
                "stream": (run.get("identity") or {}).get("stream"),
                "commit": (run.get("identity") or {}).get("commit"),
                "sections": [{
                    "id": "execution-findings",
                    "title": "Execution findings",
                    "kind": "funcionalidades",
                    "groups": [{
                        "id": "execution-findings-g",
                        "title": f"From {run.get('execution_id')}",
                        "items": items,
                    }],
                }],
            },
        }
    else:
        print("mode=replace needs a full seed file — use ereport_client.py request POST with mode replace", file=sys.stderr)
        sys.exit(2)
    dest = ROOT / "execution_append_body.json"
    _write_json(dest, body)
    print(json.dumps({"item_count": len(items), "wrote": str(dest), "mode": "append"}, indent=2))
    print("Next: python ereport_client.py docs && python ereport_client.py request POST "
          f"/api/v1/ereport/orgs/{{orgId}}/reports/{{reportId}} --file {dest.name}")


def main() -> None:
    p = argparse.ArgumentParser(description="Local .ereport execution log (agent analytics)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("prompt", help="Print the user consent prompt (agents must show this first)").set_defaults(func=cmd_prompt)
    acc = sub.add_parser("accept", help="Record user ACCEPT of detailed execution logging")
    acc.add_argument("--note", default="")
    acc.set_defaults(func=cmd_accept)
    rej = sub.add_parser("reject", help="Record user REJECT — agent syncs eReport without ledger")
    rej.add_argument("--note", default="")
    rej.set_defaults(func=cmd_reject)
    sub.add_parser("consent", help="Show consent state").set_defaults(func=cmd_consent)

    sub.add_parser("enable", help="Enable ledger (requires prior accept)").set_defaults(func=cmd_enable)
    sub.add_parser("status", help="Print consent + last_status").set_defaults(func=cmd_status)

    idp = sub.add_parser("identity", help="Show or publish identity.json (last-executed wins)")
    idp.add_argument("--file", help="JSON identity to publish")
    idp.set_defaults(func=cmd_identity)

    ing = sub.add_parser("ingest", help="Append one portable execution run JSON")
    ing.add_argument("--file", required=True, help="Run JSON (or {execution:...})")
    ing.set_defaults(func=cmd_ingest)

    ix = sub.add_parser("index", help="Show executions.index.json (optionally filter)")
    ix.add_argument("--stream", default="")
    ix.add_argument("--step-id", default="")
    ix.set_defaults(func=cmd_index)

    dig = sub.add_parser("digest", help="≤15-line agent digest (index-first)")
    dig.add_argument("--stream", default="")
    dig.add_argument("--step-id", default="")
    dig.set_defaults(func=cmd_digest)

    te = sub.add_parser("to-ereport", help="Build append POST body from fail|review|error steps")
    te.add_argument("--execution-id", default="")
    te.add_argument("--mode", default="append", choices=["append"])
    te.set_defaults(func=cmd_to_ereport)

    args = p.parse_args()
    try:
        args.func(args)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
