"""选择合同与 query 拼接的离线参考；不包含端侧控件或消息发送实现。"""

from __future__ import annotations

from typing import Any


SELECTION_CAPABILITY = "selection-query-v1"
SUBMIT_SELECTION_EVENT = "submit_selection_query"


def _nonblank(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def choice_group_errors(group: dict[str, Any]) -> list[str]:
    """校验选择组的内容和数量关系，字段白名单另由组件 catalog 校验。"""
    errors: list[str] = []
    if not isinstance(group, dict):
        return ["选择组必须是对象"]
    if group.get("component") != "Extended.ChoiceGroup":
        errors.append("选择组必须使用 Extended.ChoiceGroup")
    if not _nonblank(group.get("label")):
        errors.append("选择组 label 必须是非空白字符串")
    mode = group.get("mode")
    if mode not in ("single", "multiple"):
        errors.append("选择组 mode 必须是 single 或 multiple")

    options = group.get("options")
    if not isinstance(options, list):
        return errors + ["选择组 options 必须是数组"]
    if len(options) < 2:
        errors.append("选择组至少需要两个选项")
    values: set[str] = set()
    for index, option in enumerate(options):
        if not isinstance(option, dict):
            errors.append(f"选项 {index} 必须是对象")
            continue
        value = option.get("value")
        if not _nonblank(value):
            errors.append(f"选项 {index} 的 value 必须是非空白字符串")
        elif value in values:
            errors.append(f"选项 value 重复：{value!r}")
        else:
            values.add(value)
        if not _nonblank(option.get("label")):
            errors.append(f"选项 {index} 的 label 必须是非空白字符串")
        if "description" in option and not isinstance(option["description"], str):
            errors.append(f"选项 {index} 的 description 必须是字符串")

    minimum = group.get("minSelected", 1)
    maximum = group.get("maxSelected", 1 if mode == "single" else len(options))
    if type(minimum) is not int or type(maximum) is not int:
        return errors + ["minSelected 和 maxSelected 必须是整数"]
    if not 1 <= minimum <= maximum <= len(options):
        errors.append("选择数量必须满足 1 <= minSelected <= maxSelected <= 选项数量")
    if mode == "single" and (minimum != 1 or maximum != 1):
        errors.append("单选的 minSelected 和 maxSelected 必须为 1")
    return errors


def selection_context_errors(context: Any) -> list[str]:
    """保留事件的 context 只声明目标和任务，实际选择只能从端侧读取。"""
    if not isinstance(context, dict):
        return ["选择提交 context 必须是对象"]
    errors: list[str] = []
    if set(context) != {"choiceGroupId", "prompt"}:
        errors.append("选择提交 context 只能且必须包含 choiceGroupId 和 prompt")
    for key in ("choiceGroupId", "prompt"):
        if not _nonblank(context.get(key)):
            errors.append(f"选择提交 {key} 必须是非空白字符串")
    return errors


def build_selection_query(
    choice_group: dict[str, Any], selected_values: list[str], prompt: str
) -> str:
    """根据真实选择生成参考 query；调用方须先完成事件授权和 surface 校验。"""
    if not isinstance(choice_group, dict):
        raise ValueError("选择组必须是对象")
    errors = choice_group_errors(choice_group)
    if errors:
        raise ValueError("；".join(errors))
    if not _nonblank(prompt):
        raise ValueError("prompt 必须是非空白字符串")
    if not isinstance(selected_values, list) or any(not _nonblank(item) for item in selected_values):
        raise ValueError("selected_values 必须是非空白字符串数组")
    selected = set(selected_values)
    if len(selected) != len(selected_values):
        raise ValueError("selected_values 不得重复")
    options = choice_group["options"]
    if selected - {option["value"] for option in options}:
        raise ValueError("selected_values 包含未知选项")
    minimum = choice_group.get("minSelected", 1)
    maximum = choice_group.get("maxSelected", 1 if choice_group["mode"] == "single" else len(options))
    if not minimum <= len(selected) <= maximum:
        raise ValueError("实际选择数量不符合 minSelected/maxSelected")

    lines = [prompt, choice_group["label"]]
    for option in options:
        if option["value"] in selected:
            line = f"- {option['label']}"
            if option.get("description"):
                line += f"：{option['description']}"
            lines.append(line)
    return "\n".join(lines)
