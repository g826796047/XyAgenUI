"""验证 CLI 接入宿主上下文，同时保留普通按钮的旧入口。"""

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from validate_a2ui_chat import main, validate_messages


CATALOG = json.loads((ROOT / "catalogs/xy-a2ui-chat-basic/v1/catalog.json").read_text(encoding="utf-8"))


class HostContextTests(unittest.TestCase):
    def run_cli(self, *args):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = main(list(args))
        return result, stdout.getvalue() + stderr.getvalue()

    def test_cli_accepts_selection_context_and_rejects_missing_capability(self):
        fixture = str(ROOT / "examples/selection-single.jsonl")
        result, _ = self.run_cli(fixture, "--context", str(ROOT / "examples/selection-runtime-context.json"))
        self.assertEqual(result, 0)
        result, output = self.run_cli(fixture)
        self.assertEqual(result, 1)
        self.assertIn("selection-query-v1", output)

    def test_legacy_events_entry_point_still_accepts_regular_buttons(self):
        result, _ = self.run_cli(
            str(ROOT / "examples/allowed-event.jsonl"), "--events", str(ROOT / "examples/allowed-ui-events.json")
        )
        self.assertEqual(result, 0)

    def test_cli_rejects_invalid_context_shapes_without_crashing(self):
        invalid = [[], {"a2ui": []}, {"allowedUiEvents": {}}, {"allowedUiEvents": [42]}]
        with tempfile.TemporaryDirectory() as temporary:
            context_path = Path(temporary) / "context.json"
            for value in invalid:
                with self.subTest(value=value):
                    context_path.write_text(json.dumps(value), encoding="utf-8")
                    result, output = self.run_cli(
                        str(ROOT / "examples/short-answer.jsonl"), "--context", str(context_path)
                    )
                    self.assertNotEqual(result, 0)
                    self.assertIn("错误", output)

    def test_runtime_surface_and_catalog_must_match_if_provided(self):
        messages = [json.loads(line) for line in (ROOT / "examples/short-answer.jsonl").read_text(encoding="utf-8").splitlines()]
        for context in ({"surfaceId": "another-surface"}, {"catalogId": "another-catalog"}):
            with self.subTest(context=context):
                self.assertTrue(validate_messages(messages, CATALOG, a2ui=context))

    def test_malformed_catalog_and_blank_ids_return_errors(self):
        messages = [json.loads(line) for line in (ROOT / "examples/short-answer.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(validate_messages(messages, [], []), ["catalog 必须是对象"])
        messages[0]["createSurface"]["surfaceId"] = "   "
        self.assertTrue(any("surfaceId" in error for error in validate_messages(messages, CATALOG)))

    def test_events_and_full_context_cannot_be_combined(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                main(["unused.jsonl", "--events", "events.json", "--context", "context.json"])


if __name__ == "__main__":
    unittest.main()
