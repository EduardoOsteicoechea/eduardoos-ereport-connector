#!/usr/bin/env python3
"""Smoke tests for local execution_log (no network)."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import execution_log as el


class ExecutionLogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(self.tmp, ignore_errors=True))
        self.patcher = mock.patch.object(el, "EXEC_DIR", self.tmp / "execution")
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_ingest_index_digest_to_ereport(self) -> None:
        el.cmd_enable(None)  # type: ignore[arg-type]
        el.publish_identity({"stream": "C20MCB-100", "commit": "deadbeef", "source": "test"})
        run = {
            "execution_id": "abcdef0123456789abcdef0123456789",
            "identity": {"stream": "C20MCB-100", "commit": "deadbeef"},
            "subject": {"title": "demo"},
            "steps": [
                {
                    "step_id": "CU 6.2.1",
                    "status": "fail",
                    "messages": ["clearance fail"],
                    "artifacts": [{"role": "log", "uri": "file:///tmp/x.log"}],
                },
                {"step_id": "CU 6.2.2", "status": "pass", "messages": []},
            ],
        }
        saved = el.ingest_run(run)
        self.assertEqual(saved["execution_id"], run["execution_id"])
        idx = json.loads((el.EXEC_DIR / "executions.index.json").read_text(encoding="utf-8"))
        self.assertEqual(idx["by_stream"]["C20MCB-100"]["CU 6.2.1"]["fail"], 1)
        items = el.map_fail_to_items(saved)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["status"], "reprobado")
        status = (el.EXEC_DIR / "last_status.txt").read_text(encoding="utf-8")
        self.assertIn("reason=ok", status)

    def test_duplicate_id_rejected(self) -> None:
        el.cmd_enable(None)  # type: ignore[arg-type]
        run = {
            "execution_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "identity": {"stream": "A"},
            "steps": [{"step_id": "s1", "status": "fail", "messages": ["x"]}],
        }
        el.ingest_run(run)
        with self.assertRaises(ValueError):
            el.ingest_run(run)


if __name__ == "__main__":
    unittest.main()
