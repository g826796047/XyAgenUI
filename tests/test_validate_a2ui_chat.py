import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from validate_a2ui_chat import validate_jsonl, validate_messages  # noqa: E402

CATALOG = json.loads((ROOT / "references/a2ui/official/extended_catalog.json").read_text(encoding="utf-8"))


def messages(name):
    return [json.loads(line) for line in (ROOT / "examples" / f"{name}.jsonl").read_text(encoding="utf-8").splitlines()]


class A2UIProfileTests(unittest.TestCase):
    def test_all_examples_use_official_catalog(self):
        scenarios = json.loads((ROOT / "examples/scenarios.json").read_text(encoding="utf-8"))
        for scenario in scenarios:
            context = json.loads((ROOT / "examples" / scenario["runtimeContext"]).read_text(encoding="utf-8")) if scenario.get("runtimeContext") else {"a2ui": {}, "allowedUiEvents": json.loads((ROOT / "examples/allowed-ui-events.json").read_text(encoding="utf-8")) if scenario.get("events") else []}
            self.assertEqual(validate_jsonl(ROOT / "examples" / f"{scenario['id']}.jsonl", CATALOG, context["allowedUiEvents"], context.get("a2ui", {})), [], scenario["id"])

    def test_multiple_components_and_data_updates_are_valid(self):
        stream = messages("short-answer")
        stream[1]["updateComponents"]["components"].append({"id": "extra", "component": "Text", "content": "额外事实"})
        stream[1]["updateComponents"]["components"][0]["children"].append("extra")
        self.assertEqual(validate_messages(stream, CATALOG), [])
        stream.insert(2, {"version": "v0.9", "updateDataModel": {"surfaceId": "test-short", "path": "/state", "value": {"ready": True}}})
        self.assertEqual(validate_messages(stream, CATALOG), [])

    def test_rejects_old_profile_and_function_call(self):
        stream = messages("short-answer")
        stream[0]["createSurface"]["catalogId"] = "ohos.a2ui.extended.catalog.form"
        self.assertTrue(validate_messages(stream, CATALOG))
        stream = messages("allowed-event")
        stream[1]["updateComponents"]["components"][2]["action"] = {"functionCall": {"call": "eval"}}
        self.assertTrue(any("functionCall" in error for error in validate_messages(stream, CATALOG, json.loads((ROOT / "examples/allowed-ui-events.json").read_text(encoding="utf-8")))))

    def test_rejects_graph_errors_and_unknown_properties(self):
        stream = messages("short-answer")
        stream[1]["updateComponents"]["components"][0]["children"] = ["answer", "answer"]
        self.assertTrue(any("重复引用" in error for error in validate_messages(stream, CATALOG)))
        stream = messages("short-answer")
        stream[1]["updateComponents"]["components"][1]["unknown"] = True
        self.assertTrue(any("不支持属性" in error for error in validate_messages(stream, CATALOG)))

    def test_event_requires_whitelist(self):
        stream = messages("allowed-event")
        self.assertTrue(any("白名单" in error for error in validate_messages(stream, CATALOG, [])))


if __name__ == "__main__":
    unittest.main()
