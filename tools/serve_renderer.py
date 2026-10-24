"""Serve the standalone A2UIRender-compatible browser preview."""

from __future__ import annotations

import argparse
import ast
import json
import math
import mimetypes
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from validate_a2ui_chat import validate_messages

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "renderer"
CATALOG = json.loads((ROOT / "references/a2ui/official/extended_catalog.json").read_text(encoding="utf-8"))
SCENARIOS = json.loads((ROOT / "examples/scenarios.json").read_text(encoding="utf-8"))
MAX_BODY = 8 * 1024 * 1024


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def default_context():
    return {"a2ui": {"catalogId": CATALOG["catalogId"], "capabilities": ["selection-query-v1", "form-reactivity-v1"]}, "allowedUiEvents": read_json(ROOT / "examples/allowed-ui-events.json")}


def example(example_id: str):
    scenario = next((item for item in SCENARIOS if item["id"] == example_id), None)
    if scenario is None:
        raise ValueError("样例不存在")
    context = read_json(ROOT / "examples" / scenario["runtimeContext"]) if scenario.get("runtimeContext") else {"a2ui": default_context()["a2ui"], "allowedUiEvents": [event for event in default_context()["allowedUiEvents"] if event.get("name") in scenario.get("events", [])]}
    return {"text": (ROOT / "examples" / f"{example_id}.jsonl").read_text(encoding="utf-8"), "context": context, "query": scenario["query"]}


def prepare(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get("messages"), list) or not isinstance(payload.get("context"), dict):
        raise ValueError("必须提供 messages 数组和 context 对象")
    context = payload["context"]
    errors = validate_messages(payload["messages"], CATALOG, context.get("allowedUiEvents", []), context.get("a2ui", {}))
    if errors:
        raise ValueError("\n".join(errors))
    nodes, model = {}, {}
    for message in payload["messages"]:
        if "updateComponents" in message:
            nodes.update({node["id"]: node for node in message["updateComponents"]["components"]})
        elif "updateDataModel" in message:
            update = message["updateDataModel"]
            model = update_path(model, update.get("path", "/"), update.get("value"), "value" not in update)
        elif "deleteSurface" in message:
            nodes, model = {}, {}
    return nodes, model


def pointer_tokens(path):
    if not isinstance(path, str) or not path.startswith("/") or any(re.search(r"~(?![01])", token) for token in path.split("/")[1:]):
        raise ValueError("JSON Pointer 无效")
    if path == "/": return []
    return [token.replace("~1", "/").replace("~0", "~") for token in path[1:].split("/")]


def update_path(model, path, value, remove=False):
    tokens = pointer_tokens(path)
    if not tokens: return {} if remove else value
    if not isinstance(model, (dict, list)): model = {}
    current = model
    for index, token in enumerate(tokens[:-1]):
        next_token = tokens[index + 1]
        if isinstance(current, list):
            try: position = int(token)
            except ValueError as error: raise ValueError("数组 JSON Pointer 索引无效") from error
            if position < 0: raise ValueError("数组 JSON Pointer 索引无效")
            while len(current) <= position: current.append(None)
            if not isinstance(current[position], (dict, list)): current[position] = [] if next_token.isdigit() else {}
            current = current[position]
        else:
            if token not in current or not isinstance(current[token], (dict, list)): current[token] = [] if next_token.isdigit() else {}
            current = current[token]
    leaf = tokens[-1]
    if isinstance(current, list):
        try: position = int(leaf)
        except ValueError as error: raise ValueError("数组 JSON Pointer 索引无效") from error
        if position < 0: raise ValueError("数组 JSON Pointer 索引无效")
        if remove:
            if position < len(current): current.pop(position)
        else:
            while len(current) <= position: current.append(None)
            current[position] = value
    elif remove: current.pop(leaf, None)
    else: current[leaf] = value
    return model


def read_path(model, path):
    value = model
    for token in pointer_tokens(path):
        if isinstance(value, dict): value = value.get(token)
        elif isinstance(value, list):
            try: value = value[int(token)]
            except (ValueError, IndexError): return None
        else: return None
    return value


def resolved(value, model):
    if isinstance(value, dict) and set(value) == {"path"}: return read_path(model, value["path"])
    return value


def evaluate_expression(value, model):
    match = re.fullmatch(r"\{\{\s*(.+?)\s*\}\}", value) if isinstance(value, str) else None
    if not match: return value
    expression = match.group(1)
    token_pattern = re.compile(r"\s*(\$__dataModel(?:\.[A-Za-z_$][\w$]*)*|(?:\d+\.\d+|\d+)|'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"|true|false|null|===|!==|==|!=|<=|>=|&&|\|\||[()+\-*/%<>!?])")
    tokens, offset = [], 0
    while offset < len(expression):
        if expression[offset:].isspace(): break
        found = token_pattern.match(expression, offset)
        if not found: raise ValueError("表达式语法无效或不在安全子集内")
        tokens.append(found.group(1)); offset = found.end()
    translated = []
    for token in tokens:
        if token.startswith("$__dataModel"): translated.append("dataModel" + token[len("$__dataModel"):])
        else: translated.append({"true": "True", "false": "False", "null": "None", "===": "==", "!==": "!=", "&&": "and", "||": "or", "!": "not"}.get(token, token))
    source = " ".join(translated)
    tree = ast.parse(source, mode="eval")

    def visit(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (str, int, float, bool, type(None))): return node.value
        if isinstance(node, ast.Name) and node.id == "dataModel": return model
        if isinstance(node, ast.Attribute):
            parent = visit(node.value)
            if isinstance(parent, dict): return parent.get(node.attr)
            raise ValueError("表达式只能读取数据模型对象字段")
        if isinstance(node, ast.BinOp) and type(node.op) in {ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod}:
            left, right = visit(node.left), visit(node.right)
            if type(node.op) in {ast.Div, ast.Mod} and right == 0: raise ValueError("表达式不能除以零")
            result = {ast.Add: lambda: left + right, ast.Sub: lambda: left - right, ast.Mult: lambda: left * right, ast.Div: lambda: left / right, ast.Mod: lambda: left % right}[type(node.op)]()
            if isinstance(result, float) and not math.isfinite(result): raise ValueError("表达式结果不是有限数值")
            return result
        if isinstance(node, ast.UnaryOp) and type(node.op) in {ast.Not, ast.UAdd, ast.USub}:
            value = visit(node.operand)
            return not value if isinstance(node.op, ast.Not) else (+value if isinstance(node.op, ast.UAdd) else -value)
        if isinstance(node, ast.BoolOp) and type(node.op) in {ast.And, ast.Or}:
            values = [visit(item) for item in node.values]
            return all(values) if isinstance(node.op, ast.And) else any(values)
        if isinstance(node, ast.Compare) and all(type(op) in {ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE} for op in node.ops):
            values = [visit(node.left), *(visit(item) for item in node.comparators)]
            operations = {ast.Eq: lambda a, b: a == b, ast.NotEq: lambda a, b: a != b, ast.Lt: lambda a, b: a < b, ast.LtE: lambda a, b: a <= b, ast.Gt: lambda a, b: a > b, ast.GtE: lambda a, b: a >= b}
            return all(operations[type(op)](left, right) for op, left, right in zip(node.ops, values, values[1:]))
        raise ValueError("表达式不符合服务端安全计算子集")

    return visit(tree.body)


def _selection_snapshot(value):
    if not isinstance(value, dict): raise ValueError("selections 必须是对象")
    result = {}
    for kind in ("radio", "checkbox", "select", "toggle"):
        entry = value.get(kind, {})
        if not isinstance(entry, dict): raise ValueError(f"selections.{kind} 必须是对象")
        result[kind] = entry
    return result


def _query_from_state(event, nodes, model, selections, inputs):
    name = event.get("name")
    if name not in {"submit_selection_query", "submit_form_query"}: return None
    context = event.get("context", {})
    prompt = context.get("prompt", "")
    if not isinstance(prompt, str) or not prompt.strip(): raise ValueError("交互事件 context.prompt 不能为空")
    lines = [prompt.strip()]
    if name == "submit_selection_query":
        group_filter = context.get("choiceGroupId")
        radio_values = selections["radio"]
        for group, selected in radio_values.items():
            if group_filter and group != group_filter: continue
            choices = [node for node in nodes.values() if node.get("component") == "Radio" and resolved(node.get("group"), model) == group]
            values = {str(resolved(node.get("value"), model)) for node in choices}
            if selected not in values: raise ValueError(f"单选组 {group!r} 的当前值不是有效选项")
            lines.append(f"单选（{group}）：{selected}")
        for group, selected in selections["checkbox"].items():
            if group_filter and group != group_filter: continue
            if not isinstance(selected, list) or len(selected) != len(set(selected)): raise ValueError(f"多选组 {group!r} 的值无效")
            choices = [node for node in nodes.values() if node.get("component") == "Checkbox" and resolved(node.get("group"), model) == group]
            by_value = {str(resolved(node.get("value"), model)): str(resolved(node.get("label"), model) or resolved(node.get("value"), model)) for node in choices}
            if any(value not in by_value for value in selected): raise ValueError(f"多选组 {group!r} 包含未知选项")
            if selected: lines.append(f"多选（{group}）：{', '.join(by_value[value] for value in by_value if value in selected)}")
        for component_id, selected in selections["select"].items():
            node = nodes.get(component_id)
            if not node or node.get("component") != "Select": raise ValueError(f"下拉组件 {component_id!r} 不存在")
            options = node.get("options", [])
            if not isinstance(selected, int) or isinstance(selected, bool) or not 0 <= selected < len(options): raise ValueError(f"下拉组件 {component_id!r} 的索引无效")
            value = resolved(options[selected].get("value"), model)
            label = node.get("accessibility", {}).get("label") or node.get("id")
            lines.append(f"{label}：{value}")
    else:
        for node in nodes.values():
            if node.get("component") == "TextInput":
                binding = node.get("text")
                value = read_path(model, binding["path"]) if isinstance(binding, dict) and isinstance(binding.get("path"), str) else inputs.get(node.get("id"))
                if value not in (None, ""):
                    label = node.get("accessibility", {}).get("label") or resolved(node.get("placeholder"), model) or node.get("id")
                    lines.append(f"{label}：{value}")
            elif node.get("component") == "Text":
                content = node.get("content")
                if isinstance(content, str) and re.fullmatch(r"\{\{[^{}]+\}\}", content):
                    label = node.get("accessibility", {}).get("label") or "计算结果"
                    lines.append(f"{label}：{evaluate_expression(content, model)}")
            elif node.get("component") == "Toggle":
                binding = node.get("isOn")
                value = read_path(model, binding["path"]) if isinstance(binding, dict) and isinstance(binding.get("path"), str) else selections["toggle"].get(node.get("id"))
                if value is not None:
                    label = resolved(node.get("label"), model) or node.get("id")
                    lines.append(f"{label}：{'是' if value else '否'}")
        for component_id, selected in selections["select"].items():
            node = nodes.get(component_id)
            if node and node.get("component") == "Select" and isinstance(selected, int) and not isinstance(selected, bool) and 0 <= selected < len(node.get("options", [])):
                label = node.get("accessibility", {}).get("label") or node.get("id")
                lines.append(f"{label}：{resolved(node['options'][selected].get('value'), model)}")
    if len(lines) == 1: raise ValueError("尚未提供可提交的选择或表单数据")
    return "\n".join(lines)


def process_request(route: str, payload: dict):
    nodes, model = prepare(payload)
    surface_id = payload["messages"][0]["createSurface"]["surfaceId"]
    if route == "/api/validate":
        return {"valid": True, "componentCount": len(nodes), "nodes": nodes, "dataModel": model}
    if route == "/api/submit":
        button = nodes.get(payload.get("buttonId"))
        if not button or button.get("component") != "Button":
            raise ValueError("只能提交当前 surface 中有效的 Button")
        event = button.get("action", {}).get("event")
        if not event:
            raise ValueError("Button 没有 action.event")
        model = payload.get("dataModel", model)
        if not isinstance(model, dict): raise ValueError("dataModel 必须是对象")
        if evaluate_expression(button.get("enabled", True), model) is False:
            raise ValueError("当前表单数据不满足提交条件")
        selections = _selection_snapshot(payload.get("selections", {}))
        inputs = payload.get("inputs", {})
        if not isinstance(inputs, dict): raise ValueError("inputs 必须是对象")
        result = {"query": _query_from_state(event, nodes, model, selections, inputs), "event": event, "surfaceId": surface_id}
        return result
    raise ValueError("未知 API")


class RendererHandler(BaseHTTPRequestHandler):
    def reply(self, status, data, content_type="application/json; charset=utf-8"):
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8") if isinstance(data, (dict, list)) else data
        self.send_response(status); self.send_header("Content-Type", content_type); self.send_header("Content-Length", str(len(raw))); self.send_header("Cache-Control", "no-store"); self.send_header("X-Content-Type-Options", "nosniff"); self.end_headers(); self.wfile.write(raw)

    def do_GET(self):
        parsed = urlsplit(self.path)
        try:
            if parsed.path == "/api/bootstrap": return self.reply(200, {"catalog": CATALOG, "context": default_context(), "scenarios": SCENARIOS})
            if parsed.path == "/api/example": return self.reply(200, example(parse_qs(parsed.query).get("id", [""])[0]))
            paths = {"/": WEB / "index.html", "/index.html": WEB / "index.html", "/app.js": WEB / "app.js", "/styles.css": WEB / "styles.css", "/interactive.css": WEB / "interactive.css", "/favicon.svg": WEB / "favicon.svg"}
            path = paths.get(parsed.path)
            if parsed.path.startswith("/examples/"):
                candidate = (ROOT / parsed.path.lstrip("/")).resolve()
                if candidate.is_relative_to((ROOT / "examples").resolve()): path = candidate
            if path is None or not path.is_file(): return self.reply(404, {"error": "文件不存在"})
            content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
            return self.reply(200, path.read_bytes(), content_type + ("; charset=utf-8" if content_type.startswith("text/") else ""))
        except (OSError, ValueError) as error: return self.reply(404, {"error": str(error)})

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_BODY: raise ValueError("请求大小无效")
            payload = json.loads(self.rfile.read(length))
            return self.reply(200, process_request(urlsplit(self.path).path, payload))
        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as error: return self.reply(422, {"error": str(error)})


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--port", type=int, default=8765); args = parser.parse_args(); server = ThreadingHTTPServer(("127.0.0.1", args.port), RendererHandler); print(f"XyAgenUI 网页渲染工作台：http://127.0.0.1:{server.server_port}", flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()


if __name__ == "__main__": main()
