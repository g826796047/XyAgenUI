#!/usr/bin/env python3
"""Validate A2UI v0.9 JSONL against the A2UIRender Extended catalog."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "references/a2ui/official/extended_catalog.json"
CHAT_CATALOG_ID = "ohos.a2ui.extended.catalog"
PROTOCOL_VERSION = "v0.9"
COMPONENTS = {"Text", "Image", "Divider", "Progress", "Button", "TextInput", "Toggle", "Radio", "Checkbox", "CheckboxGroup", "Select", "Row", "Column", "List", "Stack", "Grid", "NavContainer", "Tabs", "TabContent", "Web", "If"}
LAYOUTS = {"Row", "Column", "Stack", "Grid", "List", "Tabs", "TabContent", "NavContainer", "If"}
CONTAINERS = {"Row", "Column", "Stack", "Grid", "List", "Tabs", "NavContainer"}
DEPRECATED = {"Extended.Card", "Extended.ChoiceGroup", "Extended.Form", "Extended.NumberInput", "Extended.Output"}
EXPR_RE = re.compile(r"^\{\{([^{}]+)\}\}$")
SAFE_FUNCTIONS = {"getRadioValue", "getCheckboxGroupValues", "getToggleValue", "getSelectValue", "setDataModel", "setAttributes", "navigate", "break"}


def _obj(value: Any) -> bool:
    return isinstance(value, dict)


def _id(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value == value.strip()


def _schema_ref(catalog: dict[str, Any], ref: str) -> Any:
    if not ref.startswith("#/"):
        return None
    value: Any = catalog
    for token in ref[2:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if not isinstance(value, dict) or token not in value:
            return None
        value = value[token]
    return value


def _valid_pointer(path: Any) -> bool:
    if not isinstance(path, str) or not path.startswith("/"):
        return False
    return all(not re.search(r"~(?![01])", token) for token in path.split("/")[1:])


def _expression_errors(source: str, path: str) -> list[str]:
    """Accept the documented data-model arithmetic/logical subset without evaluating it."""
    match = EXPR_RE.fullmatch(source)
    if not match:
        if "{{" in source or "}}" in source:
            return [f"{path} 表达式必须独占整个属性值并使用完整的 {{...}} 语法"]
        return []
    expression = match.group(1).strip()
    token_pattern = re.compile(r"\s*(\$__dataModel(?:\.[A-Za-z_$][\w$]*)*|(?:\d+\.\d+|\d+)|'(?:[^'\\]|\\.)*'|true|false|null|===|!==|==|!=|<=|>=|&&|\|\||[()+\-*/%<>!?])")
    tokens: list[str] = []
    position = 0
    while position < len(expression):
        found = token_pattern.match(expression, position)
        if not found:
            return [f"{path} 表达式包含不支持的 token"]
        tokens.append(found.group(1))
        position = found.end()
    if not tokens or len(tokens) > 256:
        return [f"{path} 表达式为空或过长"]
    cursor = 0
    depth = 0

    def primary() -> bool:
        nonlocal cursor, depth
        if cursor >= len(tokens):
            return False
        token = tokens[cursor]
        if token in {"!", "+", "-"}:
            cursor += 1
            return primary()
        if token == "(":
            cursor += 1
            depth += 1
            if depth > 20 or not logical_or() or cursor >= len(tokens) or tokens[cursor] != ")":
                return False
            cursor += 1
            depth -= 1
            return True
        if token.startswith("$__dataModel") or re.fullmatch(r"\d+(?:\.\d+)?", token) or token.startswith("'") or token in {"true", "false", "null"}:
            cursor += 1
            return True
        return False

    def binary(next_level, operators: set[str]) -> bool:
        nonlocal cursor
        if not next_level():
            return False
        while cursor < len(tokens) and tokens[cursor] in operators:
            cursor += 1
            if not next_level():
                return False
        return True

    def multiplicative() -> bool: return binary(primary, {"*", "/", "%"})
    def additive() -> bool: return binary(multiplicative, {"+", "-"})
    def relational() -> bool: return binary(additive, {">", ">=", "<", "<="})
    def equality() -> bool: return binary(relational, {"==", "!=", "===", "!=="})
    def logical_and() -> bool: return binary(equality, {"&&"})
    def logical_or() -> bool: return binary(logical_and, {"||"})

    if not logical_or() or cursor != len(tokens):
        return [f"{path} 表达式不符合官方安全语法子集"]
    return []


def _dynamic_tree(value: Any, path: str, functions: set[str]) -> list[str]:
    if isinstance(value, dict):
        if set(value) == {"path"}:
            return [] if _valid_pointer(value.get("path")) else [f"{path}.path 不是合法 JSON Pointer"]
        if set(value) == {"functionCall"}:
            call = value.get("functionCall", {}).get("call") if isinstance(value.get("functionCall"), dict) else None
            if call not in SAFE_FUNCTIONS or call not in functions:
                return [f"{path} 使用了未被运行时 allowedFunctions 授权的函数 {call!r}"]
            return _dynamic_tree(value["functionCall"].get("args", {}), f"{path}.functionCall.args", functions)
        errors: list[str] = []
        for key, child in value.items():
            # Event contexts are literal host payloads, not dynamic component values.
            if key == "action" and isinstance(child, dict) and "event" in child:
                continue
            errors.extend(_dynamic_tree(child, f"{path}.{key}", functions))
        return errors
    if isinstance(value, list):
        return [error for index, item in enumerate(value) for error in _dynamic_tree(item, f"{path}[{index}]", functions)]
    if isinstance(value, str):
        return _expression_errors(value, path)
    return []


def _schema_errors(value: Any, schema: Any, catalog: dict[str, Any], path: str, depth: int = 0, refs: frozenset[str] = frozenset()) -> tuple[list[str], set[str]]:
    """Validate the JSON Schema subset used by the pinned official catalog."""
    if depth > 60:
        return [f"{path} schema 引用层级超限"], set()
    if schema is True or not isinstance(schema, (dict, bool)):
        return [], set()
    if schema is False:
        return [f"{path} 不允许此值"], set()
    errors: list[str] = []
    evaluated: set[str] = set()
    ref = schema.get("$ref")
    if isinstance(ref, str):
        target = _schema_ref(catalog, ref)
        if target is None:
            errors.append(f"{path} 引用了未知 schema {ref!r}")
        elif ref not in refs:
            ref_errors, ref_props = _schema_errors(value, target, catalog, path, depth + 1, refs | {ref})
            errors.extend(ref_errors); evaluated.update(ref_props)
    for keyword in ("allOf", "anyOf", "oneOf"):
        branches = schema.get(keyword)
        if not isinstance(branches, list):
            continue
        results = [_schema_errors(value, branch, catalog, path, depth + 1, refs) for branch in branches]
        valid = [(branch_errors, props) for branch_errors, props in results if not branch_errors]
        if keyword == "allOf":
            for branch_errors, props in results:
                errors.extend(branch_errors); evaluated.update(props)
        elif not valid or (keyword == "oneOf" and len(valid) != 1):
            errors.append(f"{path} 不符合官方 catalog {keyword} schema")
        else:
            for _, props in valid:
                evaluated.update(props)
    if "not" in schema and not _schema_errors(value, schema["not"], catalog, path, depth + 1, refs)[0]:
        errors.append(f"{path} 命中禁止的 schema")
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path} 必须为 {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path} 不是允许值")
    expected = schema.get("type")
    types = expected if isinstance(expected, list) else [expected]
    checks = {"object": lambda v: _obj(v), "array": lambda v: isinstance(v, list), "string": lambda v: isinstance(v, str), "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool), "integer": lambda v: isinstance(v, int) and not isinstance(v, bool), "boolean": lambda v: isinstance(v, bool), "null": lambda v: v is None}
    if expected is not None and not any(checks.get(kind, lambda _: True)(value) for kind in types):
        return errors + [f"{path} 类型不符合官方 catalog schema"], evaluated
    if isinstance(value, dict):
        props = schema.get("properties", {}) if isinstance(schema.get("properties"), dict) else {}
        patterns = schema.get("patternProperties", {}) if isinstance(schema.get("patternProperties"), dict) else {}
        for required in schema.get("required", []) if isinstance(schema.get("required", []), list) else []:
            if required not in value: errors.append(f"{path} 缺少必需属性 {required!r}")
        matched: set[str] = set()
        for key, child in value.items():
            if key in props:
                child_errors, _ = _schema_errors(child, props[key], catalog, f"{path}.{key}", depth + 1, refs)
                errors.extend(child_errors); matched.add(key)
            for pattern, pattern_schema in patterns.items():
                try: applies = re.search(pattern, key) is not None
                except re.error: applies = False
                if applies:
                    child_errors, _ = _schema_errors(child, pattern_schema, catalog, f"{path}.{key}", depth + 1, refs)
                    errors.extend(child_errors); matched.add(key)
            if key not in matched and isinstance(schema.get("additionalProperties"), dict):
                child_errors, _ = _schema_errors(child, schema["additionalProperties"], catalog, f"{path}.{key}", depth + 1, refs)
                errors.extend(child_errors)
        evaluated.update(matched)
        if schema.get("additionalProperties") is False:
            errors.extend(f"{path} 不支持属性 {key!r}" for key in value if key not in matched)
        if schema.get("unevaluatedProperties") is False:
            errors.extend(f"{path} 不支持属性 {key!r}" for key in value if key not in evaluated)
        for bound in ("minProperties", "maxProperties"):
            limit = schema.get(bound)
            if isinstance(limit, int) and ((bound == "minProperties" and len(value) < limit) or (bound == "maxProperties" and len(value) > limit)):
                errors.append(f"{path} 属性数量不符合 {bound}")
    if isinstance(value, list):
        for bound in ("minItems", "maxItems"):
            limit = schema.get(bound)
            if isinstance(limit, int) and ((bound == "minItems" and len(value) < limit) or (bound == "maxItems" and len(value) > limit)):
                errors.append(f"{path} 数组长度不符合 {bound}")
        if schema.get("uniqueItems") is True:
            encoded = [json.dumps(item, sort_keys=True, ensure_ascii=False) for item in value]
            if len(encoded) != len(set(encoded)): errors.append(f"{path} 数组元素必须唯一")
        prefix = schema.get("prefixItems", [])
        if isinstance(prefix, list):
            for index, child in enumerate(prefix[:len(value)]):
                child_errors, _ = _schema_errors(value[index], child, catalog, f"{path}[{index}]", depth + 1, refs); errors.extend(child_errors)
        items = schema.get("items")
        if isinstance(items, dict):
            start = len(prefix) if isinstance(prefix, list) else 0
            for index, item in enumerate(value[start:], start=start):
                child_errors, _ = _schema_errors(item, items, catalog, f"{path}[{index}]", depth + 1, refs); errors.extend(child_errors)
    if isinstance(value, str):
        if isinstance(schema.get("minLength"), int) and len(value) < schema["minLength"]: errors.append(f"{path} 字符串长度小于 minLength")
        if isinstance(schema.get("maxLength"), int) and len(value) > schema["maxLength"]: errors.append(f"{path} 字符串长度大于 maxLength")
        pattern = schema.get("pattern")
        if isinstance(pattern, str):
            try:
                if not re.search(pattern, value): errors.append(f"{path} 格式不匹配")
            except re.error:
                errors.append(f"{path} schema pattern 无效")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        for bound, check in (("minimum", lambda a, b: a < b), ("maximum", lambda a, b: a > b), ("exclusiveMinimum", lambda a, b: a <= b), ("exclusiveMaximum", lambda a, b: a >= b)):
            limit = schema.get(bound)
            if isinstance(limit, (int, float)) and check(value, limit): errors.append(f"{path} 超出 {bound} 范围")
    return errors, evaluated


def _dynamic_authorization_errors(node: dict[str, Any], functions: set[str], catalog: dict[str, Any], path: str) -> list[str]:
    errors = _dynamic_tree(node, path, functions)
    definitions = catalog.get("extendedFunctions", {})
    allowed = functions & SAFE_FUNCTIONS & set(definitions if isinstance(definitions, dict) else {})
    for key in ("onClick", "onAppear", "onChange", "onSelect"):
        handlers = node.get(key, [])
        if not isinstance(handlers, list): continue
        for index, handler in enumerate(handlers):
            call = handler.get("call") if isinstance(handler, dict) else None
            if call not in allowed:
                errors.append(f"{path}.{key}[{index}] 函数 {call!r} 未被运行时 allowedFunctions 授权")
            elif isinstance(handler, dict):
                errors.extend(_dynamic_tree(handler.get("args", {}), f"{path}.{key}[{index}].args", functions))
    action = node.get("action")
    if isinstance(action, dict) and isinstance(action.get("functionCall"), dict):
        call = action["functionCall"].get("call")
        if call not in allowed:
            errors.append(f"{path}.action.functionCall 函数 {call!r} 未被运行时 allowedFunctions 授权")
    return errors


def _event_errors(node: dict[str, Any], allowed: list[dict[str, Any]], path: str, functions: set[str] | None = None) -> list[str]:
    action = node.get("action")
    if not isinstance(action, dict):
        return []
    if "functionCall" in action:
        return [f"{path}.action.functionCall 不属于本项目允许的服务端交互合同"]
    event = action.get("event")
    if not isinstance(event, dict) or not _id(event.get("name")):
        return [f"{path}.action.event 必须包含事件 name"]
    definitions = {item.get("name"): item for item in allowed if isinstance(item, dict)}
    if event["name"] not in definitions:
        return [f"{path} 事件 {event['name']!r} 不在 allowedUiEvents 白名单中"]
    context = event.get("context", {})
    if _contains_dynamic(context):
        return [f"{path}.action.event.context 必须是字面量 JSON"]
    schema = definitions[event["name"]].get("contextSchema")
    if isinstance(schema, dict):
        return [f"{path}.action.event.context：{error}" for error in _literal_schema_errors(context, schema)]
    return []


def _contains_dynamic(value: Any) -> bool:
    if isinstance(value, str):
        return EXPR_RE.fullmatch(value) is not None
    if isinstance(value, dict):
        if set(value) in ({"path"}, {"functionCall"}):
            return True
        return any(_contains_dynamic(child) for child in value.values())
    if isinstance(value, list):
        return any(_contains_dynamic(child) for child in value)
    return False


def _literal_schema_errors(value: Any, schema: dict[str, Any], path: str = "context") -> list[str]:
    """Small JSON Schema subset for host event context; expressions are not literals."""
    if not isinstance(schema, dict):
        return ["contextSchema 必须是对象"]
    if isinstance(value, str) and EXPR_RE.fullmatch(value):
        return [f"{path} 不得包含表达式"]
    if isinstance(value, dict):
        if set(value) == {"path"} or set(value) == {"functionCall"}:
            return [f"{path} 不得包含动态绑定或函数调用"]
        for key, item in value.items():
            nested = _literal_schema_errors(item, {}, f"{path}.{key}")
            if nested: return nested
    if isinstance(value, list):
        for index, item in enumerate(value):
            nested = _literal_schema_errors(item, {}, f"{path}[{index}]")
            if nested: return nested
    typ = schema.get("type")
    valid = {"object": isinstance(value, dict), "array": isinstance(value, list), "string": isinstance(value, str), "number": isinstance(value, (int, float)) and not isinstance(value, bool), "integer": isinstance(value, int) and not isinstance(value, bool), "boolean": isinstance(value, bool), "null": value is None}
    if typ in valid and not valid[typ]:
        return [f"{path} 预期类型为 {typ}"]
    errors: list[str] = []
    if "const" in schema and value != schema["const"]: errors.append(f"{path} 不匹配 const")
    if "enum" in schema and value not in schema["enum"]: errors.append(f"{path} 不在 enum 中")
    if isinstance(value, dict):
        properties = schema.get("properties", {}) if isinstance(schema.get("properties"), dict) else {}
        for key in schema.get("required", []) or []:
            if key not in value: errors.append(f"{path} 缺少 {key}")
        if schema.get("additionalProperties") is False:
            errors.extend(f"{path} 不支持属性 {key!r}" for key in value if key not in properties)
        for key, child in properties.items():
            if key in value: errors.extend(_literal_schema_errors(value[key], child, f"{path}.{key}"))
    if isinstance(value, list) and isinstance(schema.get("items"), dict):
        for index, item in enumerate(value): errors.extend(_literal_schema_errors(item, schema["items"], f"{path}[{index}]"))
    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]: errors.append(f"{path} 长度不足")
        if "pattern" in schema and not re.search(schema["pattern"], value): errors.append(f"{path} 格式不匹配")
    return errors


def _children(node: dict[str, Any]) -> list[str]:
    result: list[str] = []
    for key in ("children", "childrenIf", "childrenElse"):
        value = node.get(key, [])
        if isinstance(value, list):
            result.extend(item for item in value if isinstance(item, str))
        elif isinstance(value, dict):
            template = value.get("componentId") or value.get("template")
            if isinstance(template, str):
                result.append(template)
    return result


def validate_messages(messages: list[Any], catalog: dict[str, Any], allowed_ui_events: list[dict[str, Any]] | None = None, a2ui: dict[str, Any] | None = None) -> list[str]:
    errors: list[str] = []
    allowed_ui_events = allowed_ui_events or []
    a2ui = a2ui or {}
    if not isinstance(catalog, dict) or catalog.get("catalogId") != CHAT_CATALOG_ID:
        return [f"catalog 必须是 A2UIRender Extended catalog {CHAT_CATALOG_ID!r}"]
    if not isinstance(messages, list) or not messages:
        return ["流内容为空"]
    if not isinstance(messages[0], dict) or set(messages[0]) != {"version", "createSurface"}:
        return ["第 1 行必须是 v0.9 createSurface 消息"]
    create = messages[0].get("createSurface")
    if messages[0].get("version") != PROTOCOL_VERSION or not _obj(create):
        return ["第 1 行 createSurface 必须使用 v0.9"]
    if set(messages[0]) != {"version", "createSurface"} or set(create) != {"surfaceId", "catalogId"}:
        errors.append("createSurface envelope 只允许 version、surfaceId 和 catalogId")
    surface_id = create.get("surfaceId")
    if not _id(surface_id) or create.get("catalogId") != CHAT_CATALOG_ID:
        errors.append(f"createSurface 必须包含有效 surfaceId，catalogId 固定为 {CHAT_CATALOG_ID!r}")
    capabilities = set(a2ui.get("capabilities", [])) if isinstance(a2ui.get("capabilities", []), list) else set()
    functions = set(a2ui.get("allowedFunctions", [])) if isinstance(a2ui.get("allowedFunctions", []), list) else set()
    nodes: dict[str, dict[str, Any]] = {}
    root_seen = False
    deleted = False
    for line, message in enumerate(messages[1:], start=2):
        prefix = f"line {line}"
        if not isinstance(message, dict) or message.get("version") != PROTOCOL_VERSION:
            errors.append(f"{prefix}：消息必须使用 {PROTOCOL_VERSION}"); continue
        kinds = [key for key in ("updateComponents", "updateDataModel", "deleteSurface") if key in message]
        if len(kinds) != 1:
            errors.append(f"{prefix}：每条消息必须恰好包含一种标准 A2UI 操作"); continue
        kind, payload = kinds[0], message[kinds[0]]
        if set(message) != {"version", kind}:
            errors.append(f"{prefix}：envelope 不支持额外字段")
        if not _obj(payload) or payload.get("surfaceId") != surface_id:
            errors.append(f"{prefix}：surfaceId 与 createSurface 不一致"); continue
        if deleted:
            errors.append(f"{prefix}：deleteSurface 后不得继续更新 surface"); continue
        if kind == "deleteSurface":
            if set(payload) != {"surfaceId"}:
                errors.append(f"{prefix}：deleteSurface 只能包含 surfaceId")
            deleted = True; continue
        if kind == "updateDataModel":
            pointer = payload.get("path", "/")
            if set(payload) - {"surfaceId", "path", "value"} or not _valid_pointer(pointer):
                errors.append(f"{prefix}：updateDataModel 可选合法 JSON Pointer path 和 value")
            continue
        if set(payload) != {"surfaceId", "components"} or not isinstance(payload.get("components"), list) or not payload["components"]:
            errors.append(f"{prefix}：updateComponents 必须包含一个或多个 components"); continue
        batch_ids: set[str] = set()
        for index, node in enumerate(payload["components"]):
            path = f"{prefix}.components[{index}]"
            if not _obj(node):
                errors.append(f"{path} 必须是对象"); continue
            name, node_id = node.get("component"), node.get("id")
            if name not in COMPONENTS:
                errors.append(f"{path} 组件 {name!r} 不在官方 Extended catalog 中"); continue
            if not _id(node_id):
                errors.append(f"{path}.id 必须是非空稳定字符串"); continue
            errors.extend(_schema_errors(node, catalog.get("components", {}).get(name), catalog, path)[0])
            errors.extend(_dynamic_authorization_errors(node, functions, catalog, path))
            if name == "If" and not (isinstance(node.get("condition"), str) and EXPR_RE.fullmatch(node["condition"])):
                errors.append(f"{path}.condition 必须是 {{...}} 表达式")
            if name in CONTAINERS and "children" in node and not isinstance(node["children"], (list, dict)):
                errors.append(f"{path}.children 必须是组件 ID 数组或模板对象")
            errors.extend(_event_errors(node, allowed_ui_events, path, functions))
            action_event = node.get("action", {}).get("event", {}) if isinstance(node.get("action"), dict) else {}
            event_name = action_event.get("name") if isinstance(action_event, dict) else None
            capability = {"submit_selection_query": "selection-query-v1", "submit_form_query": "form-reactivity-v1"}.get(event_name)
            if capability and capability not in capabilities:
                errors.append(f"{path} 事件 {event_name!r} 需要 a2ui.capabilities 中声明 {capability!r}")
            if name == "Web" and not isinstance(node.get("url"), str):
                errors.append(f"{path}.url 必须是 URL 字符串")
            if name == "Image":
                image_src = node.get("src")
                if isinstance(image_src, str) and image_src.startswith(("http://", "https://")):
                    from urllib.parse import urlsplit
                    host = urlsplit(image_src).hostname
                    domains = set(a2ui.get("allowedResourceDomains", [])) if isinstance(a2ui.get("allowedResourceDomains", []), list) else set()
                    if not host or host not in domains:
                        errors.append(f"{path}.src 的主机不在 allowedResourceDomains 中")
            if name == "Web" and isinstance(node.get("url"), str):
                from urllib.parse import urlsplit
                host = urlsplit(node["url"]).hostname
                domains = set(a2ui.get("allowedResourceDomains", [])) if isinstance(a2ui.get("allowedResourceDomains", []), list) else set()
                if host and host not in domains:
                    errors.append(f"{path}.url 的主机不在 allowedResourceDomains 中")
            if node_id == "root":
                root_seen = True
                if name not in LAYOUTS: errors.append(f"{path} root 必须是布局组件")
            if node_id in batch_ids:
                errors.append(f"{path} 同一批 updateComponents 中组件 ID {node_id!r} 重复")
            batch_ids.add(node_id)
            if node_id in nodes and nodes[node_id].get("component") != name:
                errors.append(f"{path} 组件 {node_id!r} 不能更改类型")
            nodes[node_id] = node
    if not root_seen or "root" not in nodes:
        errors.append("最终组件树必须定义一个 root"); return errors
    parents = {node_id: [] for node_id in nodes}
    for node_id, node in nodes.items():
        children = _children(node)
        if len(children) != len(set(children)): errors.append(f"组件 {node_id!r} 不得重复引用子节点")
        for child in children:
            if child not in nodes: errors.append(f"组件 {node_id!r} 引用了未定义子节点 {child!r}")
            else: parents[child].append(node_id)
    for node_id, parent_list in parents.items():
        if node_id != "root" and len(parent_list) > 1: errors.append(f"组件 {node_id!r} 只能有一个父节点")
        if node_id == "root" and parent_list: errors.append("root 不能作为其他组件的子节点")
    visited, active = set(), set()
    def visit(node_id: str) -> None:
        if node_id in active: errors.append(f"组件树在 {node_id!r} 处存在循环"); return
        if node_id in visited or node_id not in nodes: return
        active.add(node_id); visited.add(node_id)
        for child in _children(nodes[node_id]): visit(child)
        active.remove(node_id)
    visit("root")
    errors.extend(f"组件 {node_id!r} 无法从 root 到达" for node_id in set(nodes) - visited)
    if not any(nodes[node_id].get("component") == "Text" for node_id in visited): errors.append("最终回答必须包含 Text 组件")
    return errors


def validate_jsonl(path: Path, catalog: dict[str, Any], allowed_ui_events: list[dict[str, Any]] | None = None, a2ui: dict[str, Any] | None = None) -> list[str]:
    messages: list[Any] = []
    errors: list[str] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip(): errors.append(f"第 {line_number} 行：JSONL 不允许空行"); continue
        try: messages.append(json.loads(line))
        except json.JSONDecodeError as exc: errors.append(f"第 {line_number} 行：JSON 无效：{exc.msg}")
    return errors + validate_messages(messages, catalog, allowed_ui_events, a2ui)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("jsonl", type=Path); parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG); parser.add_argument("--events", type=Path); parser.add_argument("--context", type=Path); args = parser.parse_args(argv)
    try:
        catalog = json.loads(args.catalog.read_text(encoding="utf-8")); context = json.loads(args.context.read_text(encoding="utf-8")) if args.context else {}
        if not isinstance(context, dict): raise ValueError("--context 文件必须是对象")
        events = json.loads(args.events.read_text(encoding="utf-8")) if args.events else context.get("allowedUiEvents", []); errors = validate_jsonl(args.jsonl, catalog, events, context.get("a2ui", {}))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"错误：{exc}", file=sys.stderr); return 2
    for error in errors: print(f"错误：{error}")
    return 1 if errors else 0


if __name__ == "__main__": raise SystemExit(main())
