---
name: xy-a2ui-chat
description: 始终使用 xy-a2ui-chat-basic 组件目录，将每个用户 query 的回答生成为 A2UI v0.9 对话界面并流式输出。
metadata:
  short-description: 始终通过对话 A2UI 作答
---

# XyAgenUI 对话回复

对用户 query 的每个回答都必须由 A2UI 组件树承载。即使是简单问题、拒绝回答或简短回复，也不得切换为纯文本输出。先组织准确、完整的答案，再根据内容关系尽可能使用端侧支持的丰富组件表达层次、分组、比较和后续操作。错误、取消和传输状态属于宿主消息生命周期，不属于纯文本答案回退路径。

组件应服务于信息理解，不为增加数量制造装饰、图片或动作。摘要和多主题回答主动使用 `Extended.Card`、`Extended.Column`、`Extended.Divider` 与文本样式形成层次；比较和标签值内容优先使用 `Extended.Row`，窄容器改用纵向分组；步骤、清单和状态使用布局组件组织；可信图片组合 `Extended.Image`、说明和图注。问候或单一事实可以使用布局根节点和一个 `Extended.Text`，这是协议下限，不是复杂回答的默认结构。`Extended.Stack` 仅用于真实叠层。

消息和流式规则见[对话协议 Profile](references/a2ui/profile.md)。组件实现依据见[Extended renderer 合同](references/a2ui/renderer-contract.md)，交互依据见[选择交互合同](references/a2ui/interaction.md)，机器可读组件和属性白名单见 [v1.1 组件目录](catalogs/xy-a2ui-chat-basic/v1/catalog.json)。

## 必需输出

只能输出换行分隔的 JSON 消息，每行必须是一个完整 JSON 对象；不得在流外输出 Markdown 围栏或说明文字。使用宿主提供的运行时 `surfaceId`，并将消息中的 `catalogId` 固定为 `ohos.a2ui.extended.catalog.form`。宿主必须在生成前提供 `surfaceId`，或在 renderer 解析流之前注入。本仓库中的 catalog 名称是组件合同标识，不得替代固定的协议 `catalogId`。

每个回答先发送 `createSurface`，再在第一条 `updateComponents` 消息中定义 `root`。每条更新消息只定义一个组件。短答的最小答案如下；其他内容应按信息关系扩展为卡片、分组、并列、步骤或交互组件：

```jsonl
{"version":"v0.9","createSurface":{"surfaceId":"<runtime-surface-id>","catalogId":"ohos.a2ui.extended.catalog.form"}}
{"version":"v0.9","updateComponents":{"surfaceId":"<same-surface-id>","component":{"id":"root","component":"Extended.Column","children":["answer"]}}}
{"version":"v0.9","updateComponents":{"surfaceId":"<same-surface-id>","component":{"id":"answer","component":"Extended.Text","content":"答案内容放在这里。"}}}
```

以上占位符是说明，不是可直接用于生产的值。不得重复定义 `root`：当前 graph 实现会将 `root` 的新定义视为新树。流式输出文本时，沿用同一个非 root 组件 ID，并发送截至当前的完整累计文本及完整 props。结构化流式输出时，先定义稳定的子容器，再随着新增区块更新该非 root 容器。组件 ID 在同一 surface 中必须稳定且唯一。

## 组件选择

- 简短回答：`Extended.Column` 根节点，包含一个 `Extended.Text` 子节点。
- 长篇说明：按主题或段落分组，可使用 `Card`、`Column` 和 `Divider`；每个区块使用一个或多个 `Text`，流式更新携带完整累计内容。
- 摘要和清单：用 `Card`/`Column` 分出标题、结论、细节和状态；步骤按顺序组织，保留每一步的说明和条件。
- 比较：并列维度适合时使用 `Row`，窄对话容器使用带标签的 `Column`；必须保留比较标准、差异、限制和结论。
- 图片回答：仅在用户或可信工具提供真实图片时使用 `Extended.Image`，组合说明和图注；不得编造媒体 URL。
- 后续操作：存在精确匹配的白名单事件时使用 `Extended.Button`；需要用户选择时按下述双门控生成 `Extended.ChoiceGroup` 和确认按钮。
- `Extended.Stack` 只用于真实的叠层场景；它会让子组件相互覆盖，不是通用纵向布局容器。

所有实质答案、限定条件和用户要求的细节必须保留在组件内容中。解释性正文使用 `Extended.Text.content`；ChoiceGroup 的选项标签和说明由选择组件承载，无需重复复制一份完整文本答案。不得用省略号、截断或仅靠样式隐藏重要事实。

## 操作按钮

只有当本轮上下文提供 `allowedUiEvents`，且其中某个事件与目标操作直接匹配时，才使用 `Extended.Button`。`action.event.name` 必须与白名单中的名称完全一致，`action.event.context` 必须符合该事件的 `contextSchema`。仅使用 schema 支持的字面量 JSON 参数。没有精确匹配的事件时省略按钮。不得创建事件名、臆造 context 字段或生成 `functionCall`。

### 选择组件与确认提交

组件目录为 `1.1.0` 时可使用 `Extended.ChoiceGroup`，但必须同时满足：宿主上下文的 `a2ui.capabilities` 包含 `selection-query-v1`，并且 `allowedUiEvents` 中存在匹配的 `submit_selection_query` 事件。缺少任一条件时，不生成选择组或确认按钮，改用普通 A2UI 组件说明内容。

ChoiceGroup 的 `label` 必须非空，`mode` 为 `single` 或 `multiple`，`options` 至少两个；每项的 `value` 在组内唯一且非空，`label` 非空，`description` 可选。`minSelected` 默认 1 且不小于 1；单选的 `maxSelected` 必须为 1，多选默认等于选项数量。初始不得预填选择，也不得输出 `selected`、数据绑定、`updateDataModel` 或表达式。

确认按钮只能绑定白名单事件，`context` 恰好包含非空 `choiceGroupId` 和 `prompt`。每个选择组必须有对应按钮；引用必须指向同一 surface 中最终可达的 ChoiceGroup。流式回答完成前选择组和按钮不可操作，端侧按 `(surfaceId, choiceGroupId)` 隔离本地状态，确认时读取实际选择并防止重复发送。

端侧按固定格式组装同一对话的新 query：`prompt` 一行、选择组 `label` 一行，然后按选项展示顺序逐项输出；无说明为 `- label`，有非空说明为 `- label：description`。用户勾选本身不发送请求，确认成功后下一轮回答仍必须使用 A2UI；明确失败时保留选择并允许重试。完整规则见 [选择交互合同](references/a2ui/interaction.md)。

清单中的阶段、价格等补充信息可放在选项 `description` 中；整体进度文本是静态回答内容，不会因勾选自动更新。不要用未支持的绑定或数据模型伪造动态状态；需要实时进度、数量/规格联动或多级选项时，等待端侧声明新的组件能力。

## 禁止输出

- 在 A2UI 流之外输出纯文本答案，包括简短答案。
- 使用 v1.1 白名单之外的组件、不支持的 props，或臆测 catalog 能力。
- 重复定义 `root`、输出不完整的 JSONL 行，或生成无法解析子节点引用的组件树。
- 使用 `functionCall`、自行命名事件、通用数据绑定、自由文本输入，或没有匹配 `allowedUiEvents` 条目的按钮/选择确认操作。
- 编造事实、图片 URL、操作参数，或遗漏限定条件。
