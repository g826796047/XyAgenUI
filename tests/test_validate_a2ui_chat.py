import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from validate_a2ui_chat import validate_jsonl, validate_messages  # noqa: E402
from selection_query import build_selection_query  # noqa: E402


CATALOG = json.loads((ROOT / "catalogs/xy-a2ui-chat-basic/v1/catalog.json").read_text(encoding="utf-8"))
SCENARIOS = json.loads((ROOT / "examples/scenarios.json").read_text(encoding="utf-8"))
EVENTS = json.loads((ROOT / "examples/allowed-ui-events.json").read_text(encoding="utf-8"))
SELECTION_CONTEXT = json.loads((ROOT / "examples/selection-runtime-context.json").read_text(encoding="utf-8"))
SELECTION_RESULTS = json.loads((ROOT / "examples/selection-results.json").read_text(encoding="utf-8"))


def read_messages(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def final_text(messages):
    components = {}
    for message in messages:
        update = message.get("updateComponents")
        if update:
            component = update["component"]
            components[component["id"]] = component
    rendered_text = "\n".join(
        item.get("content", "")
        for item in components.values()
        if item.get("component") == "Extended.Text"
    )
    visible_labels = "\n".join(
        item.get("label", "")
        for item in components.values()
        if item.get("component") == "Extended.Button"
    )
    choice_content = "\n".join(
        "\n".join(
            [item.get("label", "")]
            + [option.get("label", "") + " " + option.get("description", "") for option in item.get("options", [])]
        )
        for item in components.values()
        if item.get("component") == "Extended.ChoiceGroup"
    )
    return "\n".join((rendered_text, visible_labels, choice_content))


def fixture_context(scenario):
    if scenario.get("runtimeContext"):
        return json.loads((ROOT / "examples" / scenario["runtimeContext"]).read_text(encoding="utf-8"))
    return {"a2ui": {}, "allowedUiEvents": EVENTS if scenario["events"] else []}


class ChatProfileTests(unittest.TestCase):
    def test_fixed_query_set_uses_a2ui_and_preserves_required_facts(self):
        self.assertEqual(
            {scenario["id"] for scenario in SCENARIOS},
            {
                "short-answer", "long-answer", "structured-summary", "comparison", "image-answer",
                "allowed-event", "no-event", "selection-single", "selection-multiple", "party-checklist",
            },
        )
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario["id"]):
                path = ROOT / "examples" / f"{scenario['id']}.jsonl"
                context = fixture_context(scenario)
                errors = validate_jsonl(path, CATALOG, context["allowedUiEvents"], context["a2ui"])
                self.assertEqual(errors, [])
                messages = read_messages(path)
                rendered_text = final_text(messages)
                for fact in scenario["requiredFacts"]:
                    self.assertIn(fact.lower(), rendered_text.lower())
                components = {
                    message["updateComponents"]["component"]["id"]: message["updateComponents"]["component"]
                    for message in messages[1:]
                }
                used = {component["component"] for component in components.values()}
                self.assertTrue(set(scenario["requiredComponents"]).issubset(used))

    def test_all_catalog_components_are_exercised_by_fixtures(self):
        used = set()
        for path in (ROOT / "examples").glob("*.jsonl"):
            for message in read_messages(path):
                update = message.get("updateComponents")
                if update:
                    used.add(update["component"]["component"])
        self.assertEqual(used, set(CATALOG["components"]))

    def test_event_requires_matching_whitelist_and_schema(self):
        messages = read_messages(ROOT / "examples/allowed-event.jsonl")
        self.assertEqual(validate_messages(messages, CATALOG, []), [
            "line 4：事件 'open_item' 不在 allowedUiEvents 白名单中"
        ])
        bad_events = [{
            "name": "open_item",
            "description": "打开条目。",
            "contextSchema": {
                "type": "object",
                "properties": {"itemId": {"type": "number"}},
                "required": ["itemId"],
                "additionalProperties": False,
            },
        }]
        errors = validate_messages(messages, CATALOG, bad_events)
        self.assertTrue(any("预期类型为 ['number']" in error for error in errors))

    def test_catalog_id_is_fixed(self):
        messages = read_messages(ROOT / "examples/short-answer.jsonl")
        messages[0]["createSurface"]["catalogId"] = "xy-a2ui-chat-basic"
        errors = validate_messages(messages, CATALOG)
        self.assertTrue(any("catalogId 必须固定为" in error for error in errors))

    def test_rejects_root_redefinition_and_unknown_component_property(self):
        messages = read_messages(ROOT / "examples/short-answer.jsonl")
        messages.insert(3, messages[1])
        errors = validate_messages(messages, CATALOG)
        self.assertTrue(any("root 必须且只能定义一次" in error for error in errors))

        messages = read_messages(ROOT / "examples/short-answer.jsonl")
        messages[-1]["updateComponents"]["component"]["customColor"] = "red"
        errors = validate_messages(messages, CATALOG)
        self.assertTrue(any("不支持属性 'customColor'" in error for error in errors))

    def test_rejects_plain_text_and_forbidden_function_calls(self):
        messages = read_messages(ROOT / "examples/short-answer.jsonl")
        messages[-1]["updateComponents"]["component"]["action"] = {
            "functionCall": {"call": "openUrl", "args": {"url": "https://example.test"}}
        }
        errors = validate_messages(messages, CATALOG)
        self.assertTrue(any("禁止使用 functionCall" in error for error in errors))
        self.assertTrue(any("不支持属性 'action'" in error for error in errors))
        self.assertIn("第 1 行必须是 v0.9 createSurface 消息", validate_messages(["Plain text"], CATALOG))

    def test_image_fixture_references_included_asset(self):
        image_messages = read_messages(ROOT / "examples/image-answer.jsonl")
        image = next(
            message["updateComponents"]["component"]
            for message in image_messages
            if "updateComponents" in message
            and message["updateComponents"]["component"].get("component") == "Extended.Image"
        )
        self.assertTrue((ROOT / image["src"]).is_file())

    def test_selection_fixtures_generate_queries_from_selected_values(self):
        for result in SELECTION_RESULTS:
            with self.subTest(fixture=result["fixture"]):
                messages = read_messages(ROOT / "examples" / f"{result['fixture']}.jsonl")
                group = next(
                    message["updateComponents"]["component"]
                    for message in messages
                    if message.get("updateComponents", {}).get("component", {}).get("id") == result["choiceGroupId"]
                )
                confirm = next(
                    message["updateComponents"]["component"]
                    for message in messages
                    if message.get("updateComponents", {}).get("component", {}).get("component") == "Extended.Button"
                    and message["updateComponents"]["component"].get("action", {}).get("event", {}).get("name")
                    == "submit_selection_query"
                )
                query = build_selection_query(
                    group, result["selectedValues"], confirm["action"]["event"]["context"]["prompt"]
                )
                self.assertEqual(query, result["expectedQuery"])

    def test_selection_interaction_requires_capability_and_event_whitelist(self):
        messages = read_messages(ROOT / "examples/selection-single.jsonl")
        self.assertTrue(any("capabilities" in error for error in validate_messages(messages, CATALOG, SELECTION_CONTEXT["allowedUiEvents"])))
        self.assertTrue(any("allowedUiEvents" in error for error in validate_messages(messages, CATALOG, [], SELECTION_CONTEXT["a2ui"])))

    def test_selection_event_context_is_literal_and_has_exact_fields(self):
        messages = read_messages(ROOT / "examples/selection-single.jsonl")
        button = next(message["updateComponents"]["component"] for message in messages if message.get("updateComponents", {}).get("component", {}).get("component") == "Extended.Button")
        button["action"]["event"]["context"]["extra"] = "not allowed"
        errors = validate_messages(messages, CATALOG, SELECTION_CONTEXT["allowedUiEvents"], SELECTION_CONTEXT["a2ui"])
        self.assertTrue(any("只能且必须包含" in error or "未声明属性 'extra'" in error for error in errors))

        button["action"]["event"]["context"].pop("extra")
        button["action"]["event"]["context"]["prompt"] = {"path": "selection.prompt"}
        errors = validate_messages(messages, CATALOG, SELECTION_CONTEXT["allowedUiEvents"], SELECTION_CONTEXT["a2ui"])
        self.assertTrue(any("字面量" in error or "非空白字符串" in error for error in errors))

        button["action"]["event"]["context"]["prompt"] = {"call": "buildPrompt", "args": {}, "extra": True}
        errors = validate_messages(messages, CATALOG, SELECTION_CONTEXT["allowedUiEvents"], SELECTION_CONTEXT["a2ui"])
        self.assertTrue(any("字面量" in error for error in errors))

    def test_malformed_event_schema_is_rejected(self):
        messages = read_messages(ROOT / "examples/allowed-event.jsonl")
        malformed = [{
            "name": "open_item",
            "description": "打开条目。",
            "contextSchema": {
                "type": "object",
                "properties": [],
                "required": ["itemId"],
                "additionalProperties": False,
            },
        }]
        errors = validate_messages(messages, CATALOG, malformed)
        self.assertTrue(any("properties 必须是对象" in error for error in errors))

    def test_selection_group_contract_rejects_duplicate_values_invalid_bounds_and_preselection(self):
        messages = read_messages(ROOT / "examples/selection-multiple.jsonl")
        group = next(message["updateComponents"]["component"] for message in messages if message.get("updateComponents", {}).get("component", {}).get("component") == "Extended.ChoiceGroup")
        group["options"][1]["value"] = group["options"][0]["value"]
        errors = validate_messages(messages, CATALOG, SELECTION_CONTEXT["allowedUiEvents"], SELECTION_CONTEXT["a2ui"])
        self.assertTrue(any("value 重复" in error for error in errors))

        group["options"][1]["value"] = "layout"
        group["maxSelected"] = 4
        errors = validate_messages(messages, CATALOG, SELECTION_CONTEXT["allowedUiEvents"], SELECTION_CONTEXT["a2ui"])
        self.assertTrue(any("maximum" in error or "最大值" in error or "maxSelected" in error or "选择数量" in error for error in errors))

        group.pop("maxSelected")
        group["selectedValues"] = ["protocol"]
        errors = validate_messages(messages, CATALOG, SELECTION_CONTEXT["allowedUiEvents"], SELECTION_CONTEXT["a2ui"])
        self.assertTrue(any("selectedValues" in error for error in errors))

    def test_selection_button_must_reference_a_reachable_choice_group(self):
        messages = read_messages(ROOT / "examples/selection-single.jsonl")
        button = next(message["updateComponents"]["component"] for message in messages if message.get("updateComponents", {}).get("component", {}).get("component") == "Extended.Button")
        button["action"]["event"]["context"]["choiceGroupId"] = "absent"
        errors = validate_messages(messages, CATALOG, SELECTION_CONTEXT["allowedUiEvents"], SELECTION_CONTEXT["a2ui"])
        self.assertTrue(any("可达的选择组" in error for error in errors))

    def test_streamed_choice_group_update_is_validated_against_final_reference(self):
        messages = read_messages(ROOT / "examples/selection-single.jsonl")
        original_group = next(
            message["updateComponents"]["component"]
            for message in messages
            if message.get("updateComponents", {}).get("component", {}).get("component") == "Extended.ChoiceGroup"
        )
        final_group = json.loads(json.dumps(original_group))
        final_group["label"] = "最终讲解方式"
        messages.append({
            "version": "v0.9",
            "updateComponents": {"surfaceId": "test-selection-single", "component": final_group},
        })
        errors = validate_messages(messages, CATALOG, SELECTION_CONTEXT["allowedUiEvents"], SELECTION_CONTEXT["a2ui"])
        self.assertEqual(errors, [])
        result = next(item for item in SELECTION_RESULTS if item["fixture"] == "selection-single")
        confirm = next(message["updateComponents"]["component"] for message in messages if message.get("updateComponents", {}).get("component", {}).get("component") == "Extended.Button")
        query = build_selection_query(final_group, result["selectedValues"], confirm["action"]["event"]["context"]["prompt"])
        self.assertIn("\n最终讲解方式\n", query)


if __name__ == "__main__":
    unittest.main()
