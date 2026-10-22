---
name: xy-a2ui-chat
description: 始终使用 xy-a2ui-chat-basic 组件目录，将每个用户 query 的回答生成为 A2UI v0.9 对话界面并流式输出。
metadata:
  short-description: 始终通过对话 A2UI 作答
---

# XyAgenUI 对话回复

对用户 query 的每个回答都必须由 A2UI 组件树承载。即使是简单问题、拒绝回答或简短回复，也不得切换为纯文本输出。简单内容放在最小布局根节点下的一个 `Extended.Text` 中。错误、取消和传输状态属于宿主消息生命周期，不属于纯文本答案回退路径。

渲染前先组织准确答案，并保留所有重要事实、限定条件和用户要求的细节。然后选择适合内容和当前对话宽度的最小组件树。不要添加无助于阅读的 UI 装饰。

消息和流式规则见[对话协议 Profile](../../references/a2ui/profile.md)。组件实现依据见[Extended renderer 合同](../../references/a2ui/renderer-contract.md)，机器可读组件和属性白名单见 [v1 组件目录](../../catalogs/xy-a2ui-chat-basic/v1/catalog.json)。

## 必需输出

只能输出换行分隔的 JSON 消息，每行必须是一个完整 JSON 对象；不得在流外输出 Markdown 围栏或说明文字。使用宿主提供的运行时 `surfaceId`，并将消息中的 `catalogId` 固定为 `ohos.a2ui.extended.catalog.form`。宿主必须在生成前提供 `surfaceId`，或在 renderer 解析流之前注入。本仓库中的 catalog 名称是组件合同标识，不得替代固定的协议 `catalogId`。

每个回答先发送 `createSurface`，再在第一条 `updateComponents` 消息中定义 `root`。每条更新消息只定义一个组件。最小答案如下：

```jsonl
{"version":"v0.9","createSurface":{"surfaceId":"<runtime-surface-id>","catalogId":"ohos.a2ui.extended.catalog.form"}}
{"version":"v0.9","updateComponents":{"surfaceId":"<same-surface-id>","component":{"id":"root","component":"Extended.Column","children":["answer"]}}}
{"version":"v0.9","updateComponents":{"surfaceId":"<same-surface-id>","component":{"id":"answer","component":"Extended.Text","content":"答案内容放在这里。"}}}
```

以上占位符是说明，不是可直接用于生产的值。不得重复定义 `root`：当前 graph 实现会将 `root` 的新定义视为新树。流式输出文本时，沿用同一个非 root 组件 ID，并发送截至当前的完整累计文本及完整 props。结构化流式输出时，先定义稳定的子容器，再随着新增区块更新该非 root 容器。组件 ID 在同一 surface 中必须稳定且唯一。

## 组件选择

- 简短回答：`Extended.Column` 根节点，包含一个 `Extended.Text` 子节点。
- 长篇说明：根节点使用 `Extended.Column`，其中嵌套一个 `Extended.Column`，每个段落或区块对应一个 `Extended.Text`。更新已有文本节点时，发送完整累计文本。
- 摘要：用 `Column` 组织区块；紧凑的标签/值组合可用 `Row`。
- 比较：只有双方都能放进当前对话宽度时才使用 `Row`；窄屏客户端使用带标签的 `Column` 区块。用文本保留比较标准和结论。
- 图片回答：仅在用户或可信工具提供真实图片时使用 `Extended.Image`，并用 `Extended.Text` 解释图片或添加图注。不得编造媒体 URL。
- `Extended.Card` 仅用于确实有益的分组。renderer 默认会绘制卡片外观；普通对话回答使用简单布局根节点。
- `Extended.Stack` 仅用于真实的叠层场景。它会让子组件相互覆盖，不是通用的纵向布局容器。

完整答案必须保留在 `Extended.Text.content` 中。保留换行和用户要求的所有细节；不得用省略号或截断隐藏重要内容。优先使用少量易读的文本节点，避免不必要的嵌套。

## 操作按钮

只有当本轮上下文提供 `allowedUiEvents`，且其中某个事件与目标操作直接匹配时，才使用 `Extended.Button`。`action.event.name` 必须与白名单中的名称完全一致，`action.event.context` 必须符合该事件的 `contextSchema`。仅使用 schema 支持的字面量 JSON 参数。没有精确匹配的事件时省略按钮。不得创建事件名、臆造 context 字段、生成 `functionCall` 或添加输入控件。

## 禁止输出

- 在 A2UI 流之外输出纯文本答案，包括简短答案。
- 使用 v1 白名单之外的组件、不支持的 props，或臆测 catalog 能力。
- 重复定义 `root`、输出不完整的 JSONL 行，或生成无法解析子节点引用的组件树。
- 使用 `functionCall`、自行命名事件、不支持的输入控件，或没有匹配 `allowedUiEvents` 条目的按钮。
- 编造事实、图片 URL、操作参数，或遗漏限定条件。
