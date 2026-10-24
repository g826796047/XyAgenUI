import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from validate_a2ui_chat import validate_jsonl  # noqa: E402
from validate_a2ui_chat import validate_messages  # noqa: E402


class StandardBindingTests(unittest.TestCase):
    def test_local_data_model_updates_are_accepted(self):
        catalog = json.loads((ROOT / "references/a2ui/official/extended_catalog.json").read_text(encoding="utf-8"))
        self.assertEqual(validate_jsonl(ROOT / "examples/form-ingredients.jsonl", catalog, json.loads((ROOT / "examples/form-runtime-context.json").read_text(encoding="utf-8"))["allowedUiEvents"], {"capabilities": ["form-reactivity-v1"]}), [])

    def test_rejects_interpolated_or_incomplete_expression_strings(self):
        catalog = json.loads((ROOT / "references/a2ui/official/extended_catalog.json").read_text(encoding="utf-8"))
        context = json.loads((ROOT / "examples/form-runtime-context.json").read_text(encoding="utf-8"))
        messages = [json.loads(line) for line in (ROOT / "examples/form-ingredients.jsonl").read_text(encoding="utf-8").splitlines()]
        total = next(node for node in messages[2]["updateComponents"]["components"] if node["id"] == "total")
        total["content"] = "食材总量：{{ $__dataModel.form.people * $__dataModel.form.perPerson }} g"
        errors = validate_messages(messages, catalog, context["allowedUiEvents"], context["a2ui"])
        self.assertTrue(any("表达式必须独占" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
