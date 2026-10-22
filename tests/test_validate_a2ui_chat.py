import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from validate_a2ui_chat import validate_jsonl, validate_messages  # noqa: E402


CATALOG = json.loads((ROOT / "catalogs/xy-a2ui-chat-basic/v1/catalog.json").read_text(encoding="utf-8"))
SCENARIOS = json.loads((ROOT / "examples/scenarios.json").read_text(encoding="utf-8"))
EVENTS = json.loads((ROOT / "examples/allowed-ui-events.json").read_text(encoding="utf-8"))


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
    return "\n".join((rendered_text, visible_labels))


class ChatProfileTests(unittest.TestCase):
    def test_fixed_query_set_uses_a2ui_and_preserves_required_facts(self):
        self.assertEqual(
            {scenario["id"] for scenario in SCENARIOS},
            {"short-answer", "long-answer", "structured-summary", "comparison", "image-answer", "allowed-event", "no-event"},
        )
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario["id"]):
                path = ROOT / "examples" / f"{scenario['id']}.jsonl"
                events = EVENTS if scenario["events"] else []
                errors = validate_jsonl(path, CATALOG, events)
                self.assertEqual(errors, [])
                rendered_text = final_text(read_messages(path))
                for fact in scenario["requiredFacts"]:
                    self.assertIn(fact.lower(), rendered_text.lower())

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


if __name__ == "__main__":
    unittest.main()
