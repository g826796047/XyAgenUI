#!/usr/bin/env python3
"""无需第三方依赖，校验 XyAgenUI 对话 profile 的 JSONL 流。"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from selection_query import (
    SELECTION_CAPABILITY,
    SUBMIT_SELECTION_EVENT,
    choice_group_errors,
    selection_context_errors,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "catalogs/xy-a2ui-chat-basic/v1/catalog.json"
CHAT_CATALOG_ID = "ohos.a2ui.extended.catalog.form"
SUPPORTED_SCHEMA_KEYS = {
    "$ref", "type", "const", "enum", "allOf", "oneOf", "properties",
    "required", "additionalProperties", "unevaluatedProperties", "items",
    "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
    "minLength", "maxLength", "pattern", "minItems", "maxItems",
}


def _json_type_matches(value: Any, expected: str) -> bool:
    if expected == "null":
        return value is None
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "string":
        return isinstance(value, str)
    return False


def _resolve_ref(root_schema: dict[str, Any], ref: str) -> dict[str, Any]:
    if not ref.startswith("#/"):
        raise ValueError(f"仅支持本地 JSON Schema 引用：{ref}")
    value: Any = root_schema
    for token in ref[2:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if not isinstance(value, dict) or token not in value:
            raise ValueError(f"无法解析 schema 引用：{ref}")
        value = value[token]
    if not isinstance(value, dict):
        raise ValueError(f"Schema 引用的目标不是对象：{ref}")
    return value


def _collect_properties(
    schema: dict[str, Any], root_schema: dict[str, Any], seen: set[str] | None = None
) -> dict[str, dict[str, Any]]:
    seen = set() if seen is None else seen
    result: dict[str, dict[str, Any]] = {}
    ref = schema.get("$ref")
    if isinstance(ref, str) and ref not in seen:
        seen.add(ref)
        result.update(_collect_properties(_resolve_ref(root_schema, ref), root_schema, seen))
    props = schema.get("properties")
    if isinstance(props, dict):
        result.update(props)
    for branch in schema.get("allOf", []):
        if isinstance(branch, dict):
            result.update(_collect_properties(branch, root_schema, seen))
    return result


def _validate_schema(
    value: Any,
    schema: dict[str, Any],
    root_schema: dict[str, Any],
    path: str,
) -> list[str]:
    errors: list[str] = []
    unknown_keywords = set(schema) - SUPPORTED_SCHEMA_KEYS
    if unknown_keywords:
        errors.append(f"{path}：校验器不支持这些 schema 关键字 {sorted(unknown_keywords)}")
        return errors

    ref = schema.get("$ref")
    if isinstance(ref, str):
        errors.extend(_validate_schema(value, _resolve_ref(root_schema, ref), root_schema, path))

    expected_type = schema.get("type")
    if expected_type is not None:
        expected_types = expected_type if isinstance(expected_type, list) else [expected_type]
        if not any(_json_type_matches(value, item) for item in expected_types):
            errors.append(f"{path}：预期类型为 {expected_types}，实际为 {type(value).__name__}")
            return errors

    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}：预期常量为 {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}：值 {value!r} 不属于枚举 {schema['enum']!r}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}：值小于最小值 {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}：值超过最大值 {schema['maximum']}")
        if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
            errors.append(f"{path}：值必须大于 {schema['exclusiveMinimum']}")
        if "exclusiveMaximum" in schema and value >= schema["exclusiveMaximum"]:
            errors.append(f"{path}：值必须小于 {schema['exclusiveMaximum']}")

    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{path}：字符串长度小于 minLength {schema['minLength']}")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append(f"{path}：字符串长度超过 maxLength {schema['maxLength']}")
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            errors.append(f"{path}：字符串不匹配 pattern {schema['pattern']!r}")

    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path}：数组元素少于 minItems {schema['minItems']}")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{path}：数组元素超过 maxItems {schema['maxItems']}")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                errors.extend(_validate_schema(item, item_schema, root_schema, f"{path}[{index}]"))

    if isinstance(value, dict):
        for required in schema.get("required", []):
            if required not in value:
                errors.append(f"{path}：缺少必需属性 {required!r}")
        properties = schema.get("properties", {})
        if isinstance(properties, dict):
            for key, child_schema in properties.items():
                if key in value and isinstance(child_schema, dict):
                    errors.extend(_validate_schema(value[key], child_schema, root_schema, f"{path}.{key}"))
        additional = schema.get("additionalProperties")
        if additional is False:
            allowed = set(properties) if isinstance(properties, dict) else set()
            for key in set(value) - allowed:
                errors.append(f"{path}：存在未声明属性 {key!r}")
        elif isinstance(additional, dict):
            allowed = set(properties) if isinstance(properties, dict) else set()
            for key in set(value) - allowed:
                errors.extend(_validate_schema(value[key], additional, root_schema, f"{path}.{key}"))

        if schema.get("unevaluatedProperties") is False:
            allowed = set(_collect_properties(schema, root_schema))
            for key in set(value) - allowed:
                errors.append(f"{path}：存在未声明属性 {key!r}")

    for branch in schema.get("allOf", []):
        if isinstance(branch, dict):
            errors.extend(_validate_schema(value, branch, root_schema, path))

    branches = schema.get("oneOf")
    if isinstance(branches, list):
        valid_count = 0
        for branch in branches:
            branch_errors = _validate_schema(value, branch, root_schema, path)
            if not branch_errors:
                valid_count += 1
        if valid_count != 1:
            errors.append(f"{path}：oneOf 预期恰好匹配一个 schema，实际匹配 {valid_count} 个")

    return errors


def _event_errors(component: dict[str, Any], allowed_events: list[dict[str, Any]], path: str) -> list[str]:
    if component.get("component") != "Extended.Button":
        return []
    action = component.get("action")
    if not isinstance(action, dict):
        return [f"{path}：按钮缺少 action"]
    event = action.get("event")
    if not isinstance(event, dict):
        return [f"{path}：按钮必须使用 action.event"]
    name = event.get("name")
    matches = [item for item in allowed_events if item.get("name") == name]
    if not matches:
        return [f"{path}：事件 {name!r} 不在 allowedUiEvents 白名单中"]
    event_schema = matches[0].get("contextSchema")
    if not isinstance(event_schema, dict) or event_schema.get("type") != "object":
        return [f"{path}：白名单事件 {name!r} 没有对象类型的 contextSchema"]
    context = event.get("context")
    if not isinstance(context, dict):
        return [f"{path}：事件 context 必须是对象"]
    errors = _validate_schema(context, event_schema, event_schema, f"{path}.action.event.context")
    if _contains_binding_marker(context):
        errors.append(f"{path}：事件 context 必须使用字面量，不能使用 path/call 绑定")
    if name == SUBMIT_SELECTION_EVENT:
        errors.extend(f"{path}：{error}" for error in selection_context_errors(context))
    return errors


def _selection_event(component: dict[str, Any]) -> dict[str, Any] | None:
    if component.get("component") != "Extended.Button":
        return None
    action = component.get("action")
    event = action.get("event") if isinstance(action, dict) else None
    if isinstance(event, dict) and event.get("name") == SUBMIT_SELECTION_EVENT:
        return event
    return None


def _selection_links_errors(nodes: dict[str, Any], reachable: set[str]) -> list[str]:
    errors: list[str] = []
    confirmed: set[str] = set()
    for node_id in reachable:
        event = _selection_event(nodes[node_id]["source"])
        if event is None or selection_context_errors(event.get("context")):
            continue
        target = event["context"]["choiceGroupId"]
        if target not in reachable or nodes[target]["component"] != "Extended.ChoiceGroup":
            errors.append(f"确认按钮 {node_id!r} 的 choiceGroupId 必须引用同一 surface 内可达的选择组")
        else:
            confirmed.add(target)
    for node_id in reachable:
        if nodes[node_id]["component"] == "Extended.ChoiceGroup" and node_id not in confirmed:
            errors.append(f"选择组 {node_id!r} 缺少引用它的确认按钮")
    return errors


def _contains_binding_marker(value: Any) -> bool:
    if isinstance(value, dict):
        # Binding objects must not be smuggled in with unrelated fields.
        if "path" in value or "call" in value:
            return True
        return any(_contains_binding_marker(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_binding_marker(item) for item in value)
    return False


def _contains_function_call(value: Any) -> bool:
    if isinstance(value, dict):
        return "functionCall" in value or any(_contains_function_call(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_function_call(item) for item in value)
    return False


def validate_messages(
    messages: list[Any],
    catalog: dict[str, Any],
    allowed_ui_events: list[dict[str, Any]] | None = None,
    a2ui: dict[str, Any] | None = None,
) -> list[str]:
    """返回已解析 JSONL 消息序列中的所有合同违规项。"""
    errors: list[str] = []
    if not isinstance(catalog, dict):
        return ["catalog 必须是对象"]
    if allowed_ui_events is not None and not isinstance(allowed_ui_events, list):
        return ["allowedUiEvents 必须是数组"]
    allowed_events = []
    components_catalog = catalog.get("components", {})
    if not isinstance(components_catalog, dict) or not components_catalog:
        return ["catalog.components 必须是非空对象"]
    malformed_components = [
        name for name, definition in components_catalog.items()
        if not isinstance(name, str) or not isinstance(definition, dict)
    ]
    if malformed_components:
        return [f"catalog.components 条目必须是对象：{malformed_components!r}"]
    event_names: set[str] = set()
    for index, item in enumerate(allowed_ui_events or []):
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            errors.append(f"allowedUiEvents[{index}] 必须包含字符串 name")
            continue
        allowed_events.append(item)
        if item["name"] in event_names:
            errors.append(f"allowedUiEvents 中事件名重复：{item['name']!r}")
        event_names.add(item["name"])
        schema = item.get("contextSchema")
        if not isinstance(schema, dict) or schema.get("type") != "object":
            errors.append(f"allowedUiEvents[{index}].contextSchema 必须是对象 schema")
            continue
        if not isinstance(schema.get("properties", {}), dict):
            errors.append(f"allowedUiEvents[{index}].contextSchema.properties 必须是对象")
        required = schema.get("required", [])
        if not isinstance(required, list) or any(not isinstance(name, str) for name in required):
            errors.append(f"allowedUiEvents[{index}].contextSchema.required 必须是字符串数组")
        additional = schema.get("additionalProperties", True)
        if not isinstance(additional, (bool, dict)):
            errors.append(f"allowedUiEvents[{index}].contextSchema.additionalProperties 必须是布尔值或 schema")

    if a2ui is None:
        a2ui = {}
    if not isinstance(a2ui, dict):
        return errors + ["a2ui 必须是对象"]
    capabilities = a2ui.get("capabilities", [])
    if not isinstance(capabilities, list) or any(not isinstance(item, str) for item in capabilities):
        errors.append("a2ui.capabilities 必须是字符串数组")
        capabilities = []
    has_selection_event = any(item.get("name") == SUBMIT_SELECTION_EVENT for item in allowed_events)

    if not messages:
        return errors + ["流内容为空"]
    if not isinstance(messages[0], dict) or set(messages[0]) != {"version", "createSurface"}:
        errors.append("第 1 行必须是 v0.9 createSurface 消息")
        return errors

    create = messages[0].get("createSurface")
    if messages[0].get("version") != "v0.9" or not isinstance(create, dict):
        errors.append("第 1 行必须使用 v0.9 版本，且 createSurface 必须是对象")
        return errors
    if set(create) != {"surfaceId", "catalogId"}:
        errors.append("createSurface 只能包含 surfaceId 和 catalogId")
    surface_id = create.get("surfaceId")
    catalog_id = create.get("catalogId")
    if not isinstance(surface_id, str) or not surface_id.strip():
        errors.append("createSurface.surfaceId 必须是非空字符串")
    if catalog_id != CHAT_CATALOG_ID:
        errors.append(f"createSurface.catalogId 必须固定为 {CHAT_CATALOG_ID!r}")
    if "surfaceId" in a2ui and a2ui["surfaceId"] != surface_id:
        errors.append("createSurface.surfaceId 与运行时 a2ui.surfaceId 不一致")
    if "catalogId" in a2ui and a2ui["catalogId"] != CHAT_CATALOG_ID:
        errors.append("运行时 a2ui.catalogId 与固定 catalogId 不一致")

    nodes: dict[str, dict[str, Any]] = {}
    root_definitions = 0
    first_update_seen = False
    for line_number, message in enumerate(messages[1:], start=2):
        prefix = f"line {line_number}"
        if not isinstance(message, dict) or set(message) != {"version", "updateComponents"}:
            errors.append(f"第 {line_number} 行：createSurface 之后只允许 updateComponents 消息")
            continue
        if message.get("version") != "v0.9":
            errors.append(f"第 {line_number} 行：version 必须是 v0.9")
            continue
        update = message.get("updateComponents")
        if not isinstance(update, dict) or set(update) != {"surfaceId", "component"}:
            errors.append(f"第 {line_number} 行：updateComponents 必须包含 surfaceId 和一个 component")
            continue
        if update.get("surfaceId") != surface_id:
            errors.append(f"第 {line_number} 行：surfaceId 与 createSurface 不一致")
        component = update.get("component")
        if not isinstance(component, dict):
            errors.append(f"第 {line_number} 行：component 必须是对象")
            continue
        if _contains_function_call(component):
            errors.append(f"第 {line_number} 行：对话 profile 禁止使用 functionCall")

        component_name = component.get("component")
        component_id = component.get("id")
        if not isinstance(component_name, str) or component_name not in components_catalog:
            errors.append(f"第 {line_number} 行：组件 {component_name!r} 不在 v1 catalog 中")
            continue
        definition = components_catalog[component_name]
        required = definition.get("required", [])
        for required_key in required:
            if required_key not in component:
                errors.append(f"第 {line_number} 行：{component_name} 缺少必需属性 {required_key!r}")
        property_schemas = definition.get("properties", {})
        if not isinstance(property_schemas, dict):
            errors.append(f"catalog 条目 {component_name!r} 的 properties 无效")
            continue
        for key, value in component.items():
            schema = property_schemas.get(key)
            if schema is None:
                errors.append(f"第 {line_number} 行：{component_name} 不支持属性 {key!r}")
            elif isinstance(schema, dict):
                errors.extend(_validate_schema(value, schema, catalog, f"{prefix}.{component_name}.{key}"))

        if component_name == "Extended.ChoiceGroup" or _selection_event(component) is not None:
            if SELECTION_CAPABILITY not in capabilities:
                errors.append(f"{prefix}：选择交互要求 a2ui.capabilities 声明 {SELECTION_CAPABILITY}")
            if not has_selection_event:
                errors.append(f"{prefix}：选择交互要求 allowedUiEvents 包含 {SUBMIT_SELECTION_EVENT}")
        if component_name == "Extended.ChoiceGroup":
            errors.extend(f"{prefix}：{error}" for error in choice_group_errors(component))

        if not isinstance(component_id, str) or not component_id.strip():
            errors.append(f"第 {line_number} 行：组件 id 必须是非空字符串")
            continue
        if component_id == "root":
            root_definitions += 1
            if not first_update_seen:
                if definition.get("category") != "layout":
                    errors.append(f"第 {line_number} 行：root 必须是布局组件")
                first_update_seen = True
            else:
                errors.append(f"第 {line_number} 行：root 只能定义一次")
        elif not first_update_seen:
            errors.append(f"第 {line_number} 行：root 必须是第一个组件定义")

        children = component.get("children", [])
        if not isinstance(children, list) or any(not isinstance(child, str) or not child for child in children):
            errors.append(f"第 {line_number} 行：children 必须是组件 ID 数组")
            children = []
        if component_id in nodes and nodes[component_id]["component"] != component_name:
            errors.append(f"第 {line_number} 行：组件 {component_id!r} 不能更改类型")
        nodes[component_id] = {"component": component_name, "children": list(children), "source": component}
        errors.extend(_event_errors(component, allowed_events, prefix))

    if root_definitions != 1:
        errors.append(f"root 必须且只能定义一次，实际为 {root_definitions} 次")
    if "root" not in nodes:
        errors.append("组件树没有 root")
        return errors

    for node_id, node in nodes.items():
        for child_id in node["children"]:
            if child_id not in nodes:
                errors.append(f"组件 {node_id!r} 引用了未定义的子节点 {child_id!r}")

    visited: set[str] = set()
    active: set[str] = set()

    def visit(node_id: str) -> None:
        if node_id in active:
            errors.append(f"组件树在 {node_id!r} 处存在循环引用")
            return
        if node_id in visited or node_id not in nodes:
            return
        active.add(node_id)
        visited.add(node_id)
        for child_id in nodes[node_id]["children"]:
            visit(child_id)
        active.remove(node_id)

    visit("root")
    for node_id in set(nodes) - visited:
        errors.append(f"组件 {node_id!r} 无法从 root 到达")
    if not any(nodes[node_id]["component"] == "Extended.Text" for node_id in visited):
        errors.append("最终答案树必须包含 Extended.Text 回答节点")
    errors.extend(_selection_links_errors(nodes, visited))
    return errors


def validate_jsonl(
    path: Path,
    catalog: dict[str, Any],
    allowed_ui_events: list[dict[str, Any]] | None = None,
    a2ui: dict[str, Any] | None = None,
) -> list[str]:
    messages: list[Any] = []
    errors: list[str] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            errors.append(f"第 {line_number} 行：JSONL 消息不能为空行")
            continue
        try:
            messages.append(json.loads(line))
        except json.JSONDecodeError as exc:
            errors.append(f"第 {line_number} 行：JSON 无效：{exc.msg}")
    return errors + validate_messages(messages, catalog, allowed_ui_events, a2ui)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jsonl", type=Path, help="A2UI v0.9 对话 profile 的 JSONL 文件")
    context_args = parser.add_mutually_exclusive_group()
    context_args.add_argument("--events", type=Path, help="本轮 allowedUiEvents 的 JSON 数组（兼容普通按钮）")
    context_args.add_argument("--context", type=Path, help="包含 a2ui 和 allowedUiEvents 的宿主上下文 JSON")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG, help="组件目录 JSON")
    args = parser.parse_args(argv)

    try:
        catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
        events = json.loads(args.events.read_text(encoding="utf-8")) if args.events else []
        a2ui = None
        if args.context:
            context = json.loads(args.context.read_text(encoding="utf-8"))
            if not isinstance(context, dict):
                raise ValueError("--context 文件必须包含宿主上下文对象")
            a2ui = context.get("a2ui", {})
            if not isinstance(a2ui, dict):
                raise ValueError("--context 的 a2ui 必须是对象")
            events = context.get("allowedUiEvents", [])
        if not isinstance(events, list):
            raise ValueError("allowedUiEvents 必须是 JSON 数组")
        errors = validate_jsonl(args.jsonl, catalog, events, a2ui)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2

    if errors:
        for error in errors:
            print(f"错误：{error}")
        return 1
    print(
        f"通过：{args.jsonl} 符合 {catalog.get('catalogId', '未命名 catalog')} "
        f"v{catalog.get('catalogVersion', '未知版本')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
