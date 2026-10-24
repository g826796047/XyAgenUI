import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from serve_renderer import default_context  # noqa: E402
from validate_a2ui_chat import COMPONENTS, validate_jsonl, validate_messages  # noqa: E402

CATALOG = json.loads((ROOT / "references/a2ui/official/extended_catalog.json").read_text(encoding="utf-8"))


def messages(name):
    return [json.loads(line) for line in (ROOT / "examples" / f"{name}.jsonl").read_text(encoding="utf-8").splitlines()]


def context(name):
    scenarios = json.loads((ROOT / "examples/scenarios.json").read_text(encoding="utf-8"))
    scenario = next(item for item in scenarios if item["id"] == name)
    return json.loads((ROOT / "examples" / scenario["runtimeContext"]).read_text(encoding="utf-8")) if scenario.get("runtimeContext") else default_context()


class A2UIProfileTests(unittest.TestCase):
    def test_all_examples_use_function_contract(self):
        scenarios = json.loads((ROOT / "examples/scenarios.json").read_text(encoding="utf-8"))
        seen_components = set()
        for scenario in scenarios:
            with self.subTest(scenario=scenario["id"]):
                runtime = context(scenario["id"])
                stream = messages(scenario["id"])
                seen_components.update(node.get("component") for message in stream for node in message.get("updateComponents", {}).get("components", []))
                self.assertEqual(
                    validate_jsonl(ROOT / "examples" / f"{scenario['id']}.jsonl", CATALOG, runtime["a2ui"]["allowedFunctions"], runtime["a2ui"]),
                    [],
                )
        self.assertEqual(COMPONENTS, seen_components)

    def test_query_template_requires_matching_params_and_component_refs(self):
        stream = messages("query-template-food")
        runtime = context("query-template-food")
        self.assertEqual(validate_messages(stream, CATALOG, runtime["a2ui"]["allowedFunctions"], runtime["a2ui"]), [])
        button = next(node for node in stream[-1]["updateComponents"]["components"] if node["id"] == "confirm")
        button["action"]["functionCall"]["args"].pop("number")
        errors = validate_messages(stream, CATALOG, runtime["a2ui"]["allowedFunctions"], runtime["a2ui"])
        self.assertTrue(any("占位符" in error for error in errors), errors)

        button["action"]["functionCall"]["args"]["number"] = "4"
        button["action"]["functionCall"]["args"]["unused"] = "额外参数"
        errors = validate_messages(stream, CATALOG, runtime["a2ui"]["allowedFunctions"], runtime["a2ui"])
        self.assertTrue(any("占位符" in error for error in errors), errors)

    def test_query_template_rejects_unknown_component_reference(self):
        stream = messages("query-template-food")
        runtime = context("query-template-food")
        args = next(node for node in stream[-1]["updateComponents"]["components"] if node["id"] == "confirm")["action"]["functionCall"]["args"]
        args["food"]["args"]["group"] = "missing"
        errors = validate_messages(stream, CATALOG, runtime["a2ui"]["allowedFunctions"], runtime["a2ui"])
        self.assertTrue(any("不存在的 getCheckboxGroupValues group" in error for error in errors), errors)

    def test_query_template_rejects_non_string_arguments(self):
        stream = messages("query-template-food")
        runtime = context("query-template-food")
        args = next(node for node in stream[-1]["updateComponents"]["components"] if node["id"] == "confirm")["action"]["functionCall"]["args"]
        args["number"] = 4
        errors = validate_messages(stream, CATALOG, runtime["a2ui"]["allowedFunctions"], runtime["a2ui"])
        self.assertTrue(any("非空字符串、字符串数组或动态字符串值" in error for error in errors), errors)

        args["number"] = True
        errors = validate_messages(stream, CATALOG, runtime["a2ui"]["allowedFunctions"], runtime["a2ui"])
        self.assertTrue(any("非空字符串、字符串数组或动态字符串值" in error for error in errors), errors)

        args["number"] = ["4", True]
        errors = validate_messages(stream, CATALOG, runtime["a2ui"]["allowedFunctions"], runtime["a2ui"])
        self.assertTrue(any("非空字符串、字符串数组或动态字符串值" in error for error in errors), errors)

    def test_query_template_rejects_object_returning_function(self):
        stream = messages("form-ingredients")
        runtime = context("form-ingredients")
        args = next(node for node in stream[-1]["updateComponents"]["components"] if node["id"] == "confirm")["action"]["functionCall"]["args"]
        args["utensils"] = {"call": "getToggleValue", "args": {"componentId": "utensils"}}
        errors = validate_messages(stream, CATALOG, runtime["a2ui"]["allowedFunctions"], runtime["a2ui"])
        self.assertTrue(any("函数结果不是字符串或字符串数组" in error for error in errors), errors)

    def test_rejects_old_event_and_unknown_function(self):
        stream = messages("function-call-link")
        node = next(item for item in stream[-1]["updateComponents"]["components"] if item["id"] == "open")
        node["action"] = {"event": {"name": "open_item"}}
        self.assertTrue(any("action.event 已废弃" in error for error in validate_messages(stream, CATALOG, ["openSuperlink"])))
        node["action"] = {"functionCall": {"call": "eval", "args": {}}}
        self.assertTrue(any("未知函数" in error or "不在项目" in error for error in validate_messages(stream, CATALOG, ["eval"])))

    def test_rejects_duplicate_and_unknown_allowed_functions(self):
        stream = messages("short-answer")
        runtime = {"catalogId": CATALOG["catalogId"], "allowedFunctions": ["sendMsgToXiaoyi", "sendMsgToXiaoyi", "eval"]}
        errors = validate_messages(stream, CATALOG, runtime["allowedFunctions"], runtime)
        self.assertTrue(any("唯一" in error for error in errors), errors)
        self.assertTrue(any("未知函数" in error for error in errors), errors)

    def test_multiple_components_and_data_updates_are_valid(self):
        stream = messages("short-answer")
        stream[1]["updateComponents"]["components"].append({"id": "extra", "component": "Text", "content": "额外事实"})
        stream[1]["updateComponents"]["components"][0]["children"].append("extra")
        self.assertEqual(validate_messages(stream, CATALOG, default_context()["a2ui"]["allowedFunctions"], default_context()["a2ui"]), [])
        stream.insert(2, {"version": "v0.9", "updateDataModel": {"surfaceId": "test-short", "path": "/state", "value": {"ready": True}}})
        self.assertEqual(validate_messages(stream, CATALOG, default_context()["a2ui"]["allowedFunctions"], default_context()["a2ui"]), [])


if __name__ == "__main__":
    unittest.main()
