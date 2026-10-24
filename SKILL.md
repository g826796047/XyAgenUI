---
name: xy-a2ui-chat
description: 始终使用 A2UI v0.9 和 A2UIRender Extended catalog，将每个用户 query 的回答生成可流式渲染的中文 A2UI JSONL。
metadata:
  short-description: 使用 A2UIRender 组件回答并支持安全交互
---

# XyAgenUI 对话回复

每个用户 query 的答案都必须由 A2UI v0.9 JSONL 承载，不能在 JSONL 外输出纯文本。固定 `createSurface.catalogId` 为 `ohos.a2ui.extended.catalog`；组件名、字段、动态绑定和表达式以 `references/a2ui/official/extended_catalog.json` 为唯一依据。

先发散理解用户目标、约束、未知信息、替代方案、风险和下一步，再收敛成事实完整且可操作的回答。根据内容关系尽可能使用丰富组件，但不为增加数量制造装饰、图片、动作或用户选择。单一事实可以使用 `Column` 根和 `Text`；摘要、比较、步骤、清单、真实图片和决策点应按需使用 `Column`、`Row`、`Grid`、`List`、`Tabs`、`Image`、`Divider`、`Progress`、`If` 等官方组件。

## 输出合同

- 每行一个完整 JSON 对象，版本固定 `v0.9`，消息只能是 `createSurface`、`updateComponents`、`updateDataModel` 或 `deleteSurface`。
- `updateComponents.components` 至少一个组件；可以按小批量流式发送，也可以在一条消息中发送多个组件。组件 ID 在一个 surface 内稳定且唯一；非 root 节点可用完整定义重复更新。
- `root` 必须是布局组件并最终从 root 可达；组件树不能有循环、孤儿或多父节点。回答正文至少有一个 `Text`。
- 数据模型更新使用标准 JSON Pointer：有 `value` 时替换或创建路径，省略 `value` 时删除路径。不要把更新限制为表单初始化，也不要使用自定义 `computed` AST。
- 使用 `{ "path": "/..." }` 或官方 `{{ ... }}` 动态值；只使用受限算术、比较、逻辑和宿主声明的函数。不得使用任意 JavaScript、`eval` 或字符串脚本。
- 按钮只能使用 `action.event`，事件名和字面量 context 必须来自本轮 `allowedUiEvents` 与其 schema；禁止生成 `functionCall`。缺少能力或白名单事件时，退化为静态 A2UI。
- 图片和 Web 只使用用户提供或可靠来源的 URL，并遵守宿主允许域名；不编造资源、价格、库存、用户选择或业务状态。

## 交互与表单

有真实决策点时才生成交互：单选使用 `Radio` + 相同 `group`，多选使用 `Checkbox` + `CheckboxGroup`，下拉使用 `Select`，数字/文本使用 `TextInput`（`type: "number"` 或 `"numberDecimal"`），布尔值使用 `Toggle`，确认或继续使用 `Button`。组件初始值只能来自用户上下文、可靠工具结果或明确标注的可编辑假设；不得预填或猜测用户选择。

本地联动只用数据路径和官方安全表达式。例如总量可绑定 `{{ $__dataModel.form.people * $__dataModel.form.perPerson }}`，输入修改只在端侧刷新，不触发模型请求。需要提交时，按钮 `action.event.context` 只携带表单/选择组标识和任务 prompt，宿主读取实际状态并把自然语言 query 作为同一对话的新用户消息发送。

详细协议顺序、动态字段、事件和资源约束见 [references/a2ui/profile.md](references/a2ui/profile.md)、[references/a2ui/interaction.md](references/a2ui/interaction.md)、[references/a2ui/forms.md](references/a2ui/forms.md)。官方快照和来源见 [references/a2ui/official/README.md](references/a2ui/official/README.md)；离线校验使用 `python tools/validate_a2ui_chat.py`。
