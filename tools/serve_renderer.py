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
    return {"a2ui": {"catalogId": CATALOG["catalogId"], "allowedFunctions": ["sendMsgToXiaoyi", "openSuperlink", "openApplink", "openDeeplink", "getRadioValue", "getCheckboxGroupValues", "getToggleValue", "getSelectValue", "setDataModel", "setAttributes", "navigate", "break"]}}


def example(example_id: str):
    scenario = next((item for item in SCENARIOS if item["id"] == example_id), None)
    if scenario is None:
        raise ValueError("样例不存在")
    context = read_json(ROOT / "examples" / scenario["runtimeContext"]) if scenario.get("runtimeContext") else default_context()
    return {"text": (ROOT / "examples" / f"{example_id}.jsonl").read_text(encoding="utf-8"), "context": context, "query": scenario["query"]}


def prepare(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get("messages"), list) or not isinstance(payload.get("context"), dict):
        raise ValueError("必须提供 messages 数组和 context 对象")
    context = payload["context"]
    errors = validate_messages(payload["messages"], CATALOG, context.get("a2ui", {}).get("allowedFunctions", []), context.get("a2ui", {}))
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
    token_pattern = re.compile(r"\s*(\$__dataModel(?:\.[A-Za-z_$][\w$]*)*|(?:\d+\.\d+|\d+)|'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"|true|false|null|===|!==|==|!=|<=|>=|&&|\|\||[()+\-*/%<>?!:])")
    tokens, offset = [], 0
    while offset < len(expression):
        if expression[offset:].isspace(): break
        found = token_pattern.match(expression, offset)
        if not found: raise ValueError("表达式语法无效或不在安全子集内")
        tokens.append(found.group(1)); offset = found.end()
    cursor = 0
    operators = {"true": "True", "false": "False", "null": "None", "===": "==", "!==": "!=", "&&": "and", "||": "or", "!": "not"}

    def atom():
        nonlocal cursor
        if cursor >= len(tokens): raise ValueError("表达式不完整")
        token = tokens[cursor]
        if token in {"!", "+", "-"}:
            cursor += 1
            return operators.get(token, token) + " " + atom()
        if token == "(":
            cursor += 1
            value = conditional()
            if cursor >= len(tokens) or tokens[cursor] != ")": raise ValueError("表达式括号不匹配")
            cursor += 1
            return "(" + value + ")"
        cursor += 1
        return "dataModel" + token[len("$__dataModel"):] if token.startswith("$__dataModel") else operators.get(token, token)

    def binary(next_level, accepted):
        nonlocal cursor
        value = next_level()
        while cursor < len(tokens) and tokens[cursor] in accepted:
            operator = operators.get(tokens[cursor], tokens[cursor])
            cursor += 1
            value = "(" + value + " " + operator + " " + next_level() + ")"
        return value

    def multiplicative(): return binary(atom, {"*", "/", "%"})
    def additive(): return binary(multiplicative, {"+", "-"})
    def relational(): return binary(additive, {">", ">=", "<", "<="})
    def equality(): return binary(relational, {"==", "!=", "===", "!=="})
    def logical_and(): return binary(equality, {"&&"})
    def logical_or(): return binary(logical_and, {"||"})

    def conditional():
        nonlocal cursor
        condition = logical_or()
        if cursor < len(tokens) and tokens[cursor] == "?":
            cursor += 1
            when_true = conditional()
            if cursor >= len(tokens) or tokens[cursor] != ":": raise ValueError("条件表达式缺少冒号")
            cursor += 1
            when_false = conditional()
            return "(" + when_true + " if " + condition + " else " + when_false + ")"
        return condition

    source = conditional()
    if cursor != len(tokens): raise ValueError("表达式包含多余 token")
    tree = ast.parse(source, mode="eval")

    def visit(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (str, int, float, bool, type(None))): return node.value
        if isinstance(node, ast.IfExp): return visit(node.body) if visit(node.test) else visit(node.orelse)
        if isinstance(node, ast.Name) and node.id == "dataModel": return model
        if isinstance(node, ast.Attribute):
            parent = visit(node.value)
            if isinstance(parent, dict): return parent.get(node.attr)
            raise ValueError("表达式只能读取数据模型对象字段")
        if isinstance(node, ast.BinOp) and type(node.op) in {ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod}:
            left, right = visit(node.left), visit(node.right)
            if type(node.op) in {ast.Div, ast.Mod} and right == 0: raise ValueError("表达式不能除以零")
            if type(node.op) is ast.Add and (isinstance(left, str) or isinstance(right, str)):
                def js_string(item):
                    if item is None: return "null"
                    if item is True: return "true"
                    if item is False: return "false"
                    return str(item)
                return js_string(left) + js_string(right)
            result = {ast.Add: lambda: left + right, ast.Sub: lambda: left - right, ast.Mult: lambda: left * right, ast.Div: lambda: left / right, ast.Mod: lambda: left % right}[type(node.op)]()
            if isinstance(result, float) and not math.isfinite(result): raise ValueError("表达式结果不是有限数值")
            return result
        if isinstance(node, ast.UnaryOp) and type(node.op) in {ast.Not, ast.UAdd, ast.USub}:
            value = visit(node.operand)
            return not value if isinstance(node.op, ast.Not) else (+value if isinstance(node.op, ast.UAdd) else -value)
        if isinstance(node, ast.BoolOp) and type(node.op) in {ast.And, ast.Or}:
            values = [visit(item) for item in node.values]
            if isinstance(node.op, ast.And):
                for item in values:
                    if not item: return item
                return values[-1] if values else None
            for item in values:
                if item: return item
            return values[-1] if values else None
        if isinstance(node, ast.Compare) and all(type(op) in {ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE} for op in node.ops):
            values = [visit(node.left), *(visit(item) for item in node.comparators)]
            operations = {ast.Eq: lambda a, b: a == b, ast.NotEq: lambda a, b: a != b, ast.Lt: lambda a, b: a < b, ast.LtE: lambda a, b: a <= b, ast.Gt: lambda a, b: a > b, ast.GtE: lambda a, b: a >= b}
            try:
                return all(operations[type(op)](left, right) for op, left, right in zip(node.ops, values, values[1:]))
            except TypeError as exc:
                raise ValueError("表达式比较了不兼容的值类型") from exc
        raise ValueError("表达式不符合服务端安全计算子集")

    return visit(tree.body)


def _selection_snapshot(value):
    if not isinstance(value, dict):
        raise ValueError("selections 必须是对象")
    result = {}
    for kind in ("radio", "checkbox", "select", "toggle"):
        entry = value.get(kind, {})
        if not isinstance(entry, dict):
            raise ValueError(f"selections.{kind} 必须是对象")
        result[kind] = entry
    return result


def _ordered_choices(nodes, component, group, model):
    return [node for node in nodes.values() if node.get("component") == component and resolved(node.get("group"), model) == group]


def _function_value(call, args, nodes, model, selections, inputs):
    if not isinstance(args, dict):
        raise ValueError(f"{call} args 必须是对象")
    if call == "getRadioValue":
        group = args.get("group")
        choices = _ordered_choices(nodes, "Radio", group, model)
        selected = selections["radio"].get(group)
        if selected is None:
            selected = next((resolved(node.get("value"), model) for node in choices if resolved(node.get("checked"), model) is True), None)
        values = [str(resolved(node.get("value"), model)) for node in choices]
        if selected is None or str(selected) not in values:
            raise ValueError(f"Radio group {group!r} 尚未选择有效选项")
        return selected
    if call == "getCheckboxGroupValues":
        group = args.get("group")
        choices = _ordered_choices(nodes, "Checkbox", group, model)
        selected = selections["checkbox"].get(group)
        if selected is None:
            selected = [resolved(node.get("value"), model) for node in choices if resolved(node.get("select"), model) is True]
        if not isinstance(selected, list) or len(selected) != len(set(map(str, selected))):
            raise ValueError(f"Checkbox group {group!r} 的值无效")
        known = {str(resolved(node.get("value"), model)) for node in choices}
        if any(str(item) not in known for item in selected):
            raise ValueError(f"Checkbox group {group!r} 包含未知选项")
        if not selected:
            raise ValueError(f"Checkbox group {group!r} 尚未选择选项")
        selected_set = {str(item) for item in selected}
        return [resolved(node.get("value"), model) for node in choices if str(resolved(node.get("value"), model)) in selected_set]
    if call == "getSelectValue":
        component_id = args.get("componentId")
        node = nodes.get(component_id)
        if not node or node.get("component") != "Select":
            raise ValueError(f"Select 组件 {component_id!r} 不存在")
        index = selections["select"].get(component_id)
        if index is None and isinstance(node.get("selected"), dict):
            index = read_path(model, node["selected"].get("path", ""))
        options = node.get("options", [])
        if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(options):
            raise ValueError(f"Select 组件 {component_id!r} 尚未选择有效选项")
        return resolved(options[index].get("value"), model)
    if call == "getToggleValue":
        component_id = args.get("componentId")
        node = nodes.get(component_id)
        if not node or node.get("component") != "Toggle":
            raise ValueError(f"Toggle 组件 {component_id!r} 不存在")
        state = read_path(model, node["isOn"].get("path", "")) if isinstance(node.get("isOn"), dict) else selections["toggle"].get(component_id)
        if not isinstance(state, bool):
            raise ValueError(f"Toggle 组件 {component_id!r} 当前状态无效")
        return {"isOn": state, "label": resolved(node.get("label"), model) or component_id}
    if call in {"setDataModel", "setAttributes", "navigate", "break"}:
        return None
    raise ValueError(f"参考 renderer 不执行函数 {call}")


def _resolve_call_value(value, nodes, model, selections, inputs):
    if isinstance(value, dict) and set(value) == {"path"}:
        return read_path(model, value["path"])
    if isinstance(value, dict) and set(value) == {"call", "args"}:
        return _function_value(value["call"], _resolve_call_args(value.get("args", {}), nodes, model, selections, inputs), nodes, model, selections, inputs)
    if isinstance(value, str):
        return evaluate_expression(value, model)
    return value


def _resolve_call_args(args, nodes, model, selections, inputs):
    if not isinstance(args, dict):
        raise ValueError("函数 args 必须是对象")
    return {key: _resolve_call_value(value, nodes, model, selections, inputs) for key, value in args.items()}


def _query_string(value):
    if value is None:
        raise ValueError("函数参数解析为空")
    if isinstance(value, list):
        if not value:
            raise ValueError("函数参数数组为空")
        if not all(isinstance(item, str) and item.strip() for item in value):
            raise ValueError("函数参数数组只能包含非空字符串")
        values = value
        if len(values) == 1:
            return values[0]
        if len(values) == 2:
            return f"{values[0]}和{values[1]}"
        return "、".join(values[:-1]) + "和" + values[-1]
    if isinstance(value, str):
        if not value.strip():
            raise ValueError("函数参数解析为空")
        return value
    raise ValueError("sendMsgToXiaoyi 只接受字符串或字符串数组；数字和布尔值必须先转换为字符串")


def _execute_function_call(function_call, nodes, model, selections, inputs):
    if not isinstance(function_call, dict) or not isinstance(function_call.get("call"), str):
        raise ValueError("Button functionCall 无效")
    call = function_call["call"]
    args = function_call.get("args", {})
    if call == "sendMsgToXiaoyi":
        if not isinstance(args, dict) or not isinstance(args.get("query"), str):
            raise ValueError("sendMsgToXiaoyi.query 必须是字符串")
        resolved_args = {key: _resolve_call_value(value, nodes, model, selections, inputs) for key, value in args.items() if key != "query"}
        query = args["query"]
        names = re.findall(r"\$\{([A-Za-z][A-Za-z0-9_]*)\}", query)
        if set(names) != set(resolved_args):
            raise ValueError("query 占位符与函数参数不匹配")
        rendered = query
        for name in names:
            rendered = rendered.replace("${" + name + "}", _query_string(resolved_args[name]))
        return {"query": rendered, "functionCall": {"call": call, "args": {**resolved_args, "query": rendered}}}
    if call in {"openSuperlink", "openApplink", "openDeeplink"}:
        resolved_args = _resolve_call_args(args, nodes, model, selections, inputs)
        return {"query": None, "functionCall": {"call": call, "args": resolved_args}, "link": resolved_args}
    raise ValueError(f"参考 renderer 不执行函数 {call}")


def process_request(route: str, payload: dict):
    nodes, model = prepare(payload)
    surface_id = payload["messages"][0]["createSurface"]["surfaceId"]
    if route == "/api/validate":
        return {"valid": True, "componentCount": len(nodes), "nodes": nodes, "dataModel": model}
    if route == "/api/submit":
        button = nodes.get(payload.get("buttonId"))
        if not button or button.get("component") != "Button":
            raise ValueError("只能提交当前 surface 中有效的 Button")
        function_call = button.get("action", {}).get("functionCall")
        if not function_call:
            raise ValueError("Button 没有 action.functionCall")
        model = payload.get("dataModel", model)
        if not isinstance(model, dict): raise ValueError("dataModel 必须是对象")
        if evaluate_expression(button.get("enabled", True), model) is False:
            raise ValueError("当前表单数据不满足提交条件")
        selections = _selection_snapshot(payload.get("selections", {}))
        inputs = payload.get("inputs", {})
        if not isinstance(inputs, dict): raise ValueError("inputs 必须是对象")
        result = _execute_function_call(function_call, nodes, model, selections, inputs)
        result["surfaceId"] = surface_id
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
