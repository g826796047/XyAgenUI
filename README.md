# XyAgenUI

本仓库维护对话式 A2UI Skill、v1.1 组件目录，以及用于验证端侧 renderer 合同的样例。

- `docs/a2ui-chat-skill-and-components-plan.md`：独立的设计与实施方案。
- `SKILL.md`：回答生成 Skill。
- `catalogs/xy-a2ui-chat-basic/v1/catalog.json`：版本化组件白名单。
- `references/a2ui/`：本项目使用的 A2UI 协议 Profile、选择交互合同、renderer 合同和统一索引。
- `examples/`：经验证的 JSONL fixtures 和本地图片资源。
- `tools/validate_a2ui_chat.py` 与 `tests/`：profile 和 fixtures 的校验工具及测试。

A2UI 回复中的 `createSurface.catalogId` 固定为 `ohos.a2ui.extended.catalog.form`。宿主按每条回复提供 `surfaceId`。该固定值是 wire 协议字段，与本仓库的组件合同 ID `xy-a2ui-chat-basic` 不同。对话组件使用 `Extended.*` 名称；据现有客户端实现合同，parser 会丢弃 `catalogId` 并使用静态 Extended registry。如果目标宿主按 `catalogId` 选择目录，必须将固定值映射到包含本项目 Chat v1.1 组件的 Extended registry。本仓库 validator 只校验固定字段值和传入 catalog 的组件/属性，不验证宿主路由；目标端映射需要集成验收。

在项目根目录使用 Python 3 运行校验：

```powershell
python -m unittest discover -s tests -v
python tools/validate_a2ui_chat.py examples/short-answer.jsonl
python tools/validate_a2ui_chat.py examples/allowed-event.jsonl --events examples/allowed-ui-events.json
python tools/validate_a2ui_chat.py examples/selection-single.jsonl --context examples/selection-runtime-context.json
```

Skill 的回答策略是“始终生成 A2UI，并尽可能使用丰富组件”。摘要、多主题内容、比较、步骤和图片会按内容关系组合 `Card`、`Row`、`Column`、`Divider`、`Image` 与 `Text`；一句话回答可以退化为最小 `Column` + `Text`。组件目录为 `xy-a2ui-chat-basic` v1.1.0，协议 wire `catalogId` 固定为 `ohos.a2ui.extended.catalog.form`。

当宿主同时在 `a2ui.capabilities` 声明 `selection-query-v1` 并在 `allowedUiEvents` 白名单提供 `submit_selection_query` 时，回答可以使用 `Extended.ChoiceGroup` 和确认按钮。用户的实际选择由端侧状态管理，确认后按 [选择交互合同](references/a2ui/interaction.md) 组装为同一对话的新 query；能力或事件缺失时不会生成不可用交互。ChoiceGroup、事件 context 和 query 格式以该合同为准。
