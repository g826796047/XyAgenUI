# XyAgenUI

本仓库维护对话式 A2UI Skill、v1 组件目录，以及用于验证端侧 renderer 合同的样例。

- `docs/a2ui-chat-skill-and-components-plan.md`：独立的设计与实施方案。
- `SKILL.md`：回答生成 Skill。
- `catalogs/xy-a2ui-chat-basic/v1/catalog.json`：版本化组件白名单。
- `references/a2ui/`：本项目使用的 A2UI 协议 Profile、renderer 合同和统一索引。
- `examples/`：经验证的 JSONL fixtures 和本地图片资源。
- `tools/validate_a2ui_chat.py` 与 `tests/`：profile 和 fixtures 的校验工具及测试。

A2UI 回复中的 `createSurface.catalogId` 固定为 `ohos.a2ui.extended.catalog.form`。宿主按每条回复提供 `surfaceId`。该固定值是 wire 协议字段，与本仓库的组件合同 ID `xy-a2ui-chat-basic` 不同。对话组件使用 `Extended.*` 名称；据现有客户端实现合同，parser 会丢弃 `catalogId` 并使用静态 Extended registry。如果目标宿主按 `catalogId` 选择目录，必须将固定值映射到包含本项目 Chat v1 组件的 Extended registry。本仓库 validator 只校验固定字段值和传入 catalog 的组件/属性，不验证宿主路由；目标端映射需要集成验收。

在项目根目录使用 Python 3 运行校验：

```powershell
python -m unittest discover -s tests -v
python tools/validate_a2ui_chat.py examples/short-answer.jsonl
python tools/validate_a2ui_chat.py examples/allowed-event.jsonl --events examples/allowed-ui-events.json
```
