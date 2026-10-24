import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from serve_renderer import SCENARIOS, evaluate_expression, example, process_request, update_path  # noqa: E402


def payload(name):
    sample = example(name)
    return {"messages": [json.loads(line) for line in sample["text"].splitlines()], "context": sample["context"]}


class RendererTests(unittest.TestCase):
    def test_server_expression_evaluator_handles_data_logic_and_literals(self):
        model = {"form": {"people": 6, "perPerson": 200, "done": False}}
        self.assertEqual(evaluate_expression("{{ $__dataModel.form.people * $__dataModel.form.perPerson }}", model), 1200)
        self.assertTrue(evaluate_expression("{{ $__dataModel.form.people >= 4 && !$__dataModel.form.done }}", model))
        self.assertTrue(evaluate_expression("{{ 'meal plan' == \"meal plan\" }}", model))
        self.assertEqual(evaluate_expression("{{ 4 + 2 * 3 }}", model), 10)
        with self.assertRaisesRegex(ValueError, "除以零"):
            evaluate_expression("{{ 1 / 0 }}", model)
        with self.assertRaisesRegex(ValueError, "不兼容"):
            evaluate_expression("{{ '' > 0 }}", model)

    def test_examples_validate(self):
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario["id"]):
                result = process_request("/api/validate", payload(scenario["id"]))
                self.assertTrue(result["valid"])
                self.assertIn("root", result["nodes"])

    def test_action_submission_returns_function_call_without_navigation(self):
        request = payload("function-call-link")
        result = process_request("/api/submit", {**request, "buttonId": "open"})
        self.assertEqual(result["functionCall"]["call"], "openSuperlink")
        self.assertIsNone(result["query"])

    def test_invalid_button_is_rejected(self):
        with self.assertRaises(ValueError):
            process_request("/api/submit", {**payload("short-answer"), "buttonId": "root"})

    def test_selection_submission_uses_actual_checked_values(self):
        request = payload("mcdonalds-order")
        result = process_request("/api/submit", {
            **request,
            "buttonId": "confirm",
            "dataModel": {"order": {"bigMac": True, "mcChicken": False, "fries": True, "pie": False, "drinkIndex": 0}},
            "selections": {"radio": {}, "checkbox": {"meal-items": ["巨无霸套餐", "薯条"]}, "select": {"drink": 0}, "toggle": {}},
            "inputs": {},
        })
        self.assertIn("巨无霸套餐和薯条", result["query"])
        self.assertIn("可乐", result["query"])
        self.assertIn("请根据我选中的麦当劳餐品", result["query"])

    def test_selection_submission_rejects_values_outside_the_component_group(self):
        request = payload("selection-multiple")
        with self.assertRaisesRegex(ValueError, "未知选项"):
            process_request("/api/submit", {
                **request,
                "buttonId": "confirm",
                "dataModel": {"selection": {"topics": {"performance": True, "cost": False}}},
                "selections": {"radio": {}, "checkbox": {"topics": ["invented"]}, "select": {}, "toggle": {}},
                "inputs": {},
            })

    def test_form_submission_uses_current_model_snapshot(self):
        request = payload("form-ingredients")
        result = process_request("/api/submit", {
            **request,
            "buttonId": "confirm",
            "dataModel": {"form": {"people": 6, "perPerson": 200, "tasteIndex": 0, "note": "素食要求", "utensils": True}},
            "selections": {"radio": {}, "checkbox": {}, "select": {"taste": 0}, "toggle": {}},
            "inputs": {},
        })
        self.assertIn("聚会人数6", result["query"])
        self.assertIn("每人用量200", result["query"])
        self.assertIn("食材总量1200", result["query"])
        self.assertIn("口味清淡", result["query"])
        self.assertIn("备注素食要求", result["query"])
        self.assertIn("一次性餐具是", result["query"])

    def test_form_submit_rejects_invalid_number_before_query_creation(self):
        request = payload("form-ingredients")
        with self.assertRaisesRegex(ValueError, "不满足提交条件"):
            process_request("/api/submit", {
                **request,
                "buttonId": "confirm",
                "dataModel": {"form": {"people": 0, "perPerson": 200, "tasteIndex": 0}},
                "selections": {"radio": {}, "checkbox": {}, "select": {"taste": 0}, "toggle": {}},
                "inputs": {},
            })

    def test_query_template_uses_live_values_and_component_display_order(self):
        request = payload("query-template-food")
        result = process_request("/api/submit", {
            **request,
            "buttonId": "confirm",
            "dataModel": {"meal": {"people": 4, "pizza": True, "salad": True}},
            "selections": {"radio": {}, "checkbox": {"foods": ["沙拉", "披萨"]}, "select": {}, "toggle": {}},
            "inputs": {},
        })
        self.assertEqual(result["query"], "我想吃披萨和沙拉，需要4人一起合作")

    def test_query_template_rejects_empty_values(self):
        request = payload("query-template-food")
        confirm = next(node for node in request["messages"][-1]["updateComponents"]["components"] if node["id"] == "confirm")
        confirm["enabled"] = True
        with self.assertRaisesRegex(ValueError, "函数参数"):
            process_request("/api/submit", {
                **request,
                "buttonId": "confirm",
                "dataModel": {"meal": {"people": "", "pizza": True, "salad": False}},
                "selections": {"radio": {}, "checkbox": {"foods": ["披萨"]}, "select": {}, "toggle": {}},
                "inputs": {},
            })

    def test_query_template_rejects_unconverted_numeric_values(self):
        request = payload("query-template-food")
        confirm = next(node for node in request["messages"][-1]["updateComponents"]["components"] if node["id"] == "confirm")
        confirm["action"]["functionCall"]["args"]["number"] = "{{ $__dataModel.meal.people }}"
        with self.assertRaisesRegex(ValueError, "必须先转换为字符串"):
            process_request("/api/submit", {
                **request,
                "buttonId": "confirm",
                "dataModel": {"meal": {"people": 4, "pizza": True, "salad": False}},
                "selections": {"radio": {}, "checkbox": {"foods": ["披萨"]}, "select": {}, "toggle": {}},
                "inputs": {},
            })

    def test_data_model_update_supports_nested_replace_and_delete(self):
        model = {"form": {"people": 4}, "items": ["a", "b"]}
        model = update_path(model, "/form/people", 6)
        model = update_path(model, "/items/0", None, True)
        self.assertEqual(model, {"form": {"people": 6}, "items": ["b"]})


if __name__ == "__main__":
    unittest.main()
