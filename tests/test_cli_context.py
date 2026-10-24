import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from validate_a2ui_chat import main  # noqa: E402


class CliContextTests(unittest.TestCase):
    def test_cli_accepts_official_fixture(self):
        self.assertEqual(main(["examples/short-answer.jsonl"]), 0)

    def test_cli_rejects_invalid_json_context(self):
        context = ROOT / "tests" / "invalid-context.json"
        context.write_text("[]", encoding="utf-8")
        try:
            self.assertNotEqual(main(["examples/short-answer.jsonl", "--context", str(context)]), 0)
        finally:
            context.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
