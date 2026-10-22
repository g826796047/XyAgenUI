# XyAgenUI 对话 A2UI v0.9 Profile

本 profile 定义 XyAgenUI 对话回答使用的 A2UI v0.9 消息、组件图增量更新和事件规则。生成答案时以本 profile、[对话 Skill](../../skills/xy-a2ui-chat/SKILL.md) 和 [Chat v1 组件目录](../../catalogs/xy-a2ui-chat-basic/v1/catalog.json) 为准。端侧 parser/renderer 源码不在本仓库，相关运行时行为是现有实现合同的记录，仍需在目标部署中验收。

组件运行行为见[Extended Renderer 合同](renderer-contract.md)。

## 运行时上下文

每轮生成时，宿主提供：

```json
{
  "a2ui": {
    "surfaceId": "由宿主生成的 surface ID",
    "catalogId": "ohos.a2ui.extended.catalog.form"
  },
  "allowedUiEvents": []
}
```

以上示例是提示上下文合同，不是 A2UI 消息。宿主必须提供运行时 `surfaceId`；`catalogId` 始终固定为 `ohos.a2ui.extended.catalog.form`。按现有客户端实现合同，parser 会将 `createSurface` 归一化为仅含 `surfaceId`，静态 renderer 也不会按该字段选择 registry。若目标宿主依据 `catalogId` 路由组件目录，必须将此固定值映射到包含 Chat v1 `Extended.*` 组件的 registry。实际可用组件由已部署的 registry 决定，而非本项目的 catalog 标识。

## 消息合同

- 协议版本固定为 `v0.9`。
- 回复使用 JSONL，每行是一个完整 JSON 对象。只有完整行写入后才能 flush；不得将尚未写完的 JSON 对象交给 parser。
- 第一行是 `createSurface`，包含运行时 `surfaceId` 和固定值 `ohos.a2ui.extended.catalog.form` 作为 `catalogId`。
- 后续各行是针对同一 surface 的 `updateComponents` 消息。
- 每条 `updateComponents` 消息恰好包含一个 `component` 对象。客户端 parser 也可接受批量更新；对话 profile 约定每行一个组件，以支持流式处理。
- 首先且仅定义一次组件 ID `root`。它必须是布局组件或 `Extended.Card`。graph renderer 将 `root` 的首次定义作为重置操作，并把它渲染为 surface 根节点。
- 子节点以有序组件 ID 引用。流式期间允许先引用后定义，但回复结束时每个引用都必须可解析；最终树必须无环，且所有输出组件都能从 `root` 到达。
- 非 root 组件 ID 可以重新定义以流式更新。重新定义会替换该节点的属性，因此每次都必须发送完整的当前属性集合。文本更新携带累计内容，不是等待追加的片段。
- `updateDataModel`、`deleteSurface` 和 A2UI 输入控件不属于本回答 profile。用户 query 的回答文本是静态的 `Extended.Text.content`。

最小答案树包含 `createSurface`、一个引用 `Extended.Text` 的 `Extended.Column` 根节点，随后是文本组件定义。这样即使回答很短，首次渲染也有实际内容。

## 组件

catalog v1 仅允许以下组件名：

- 布局：`Extended.Card`、`Extended.Row`、`Extended.Column`、`Extended.Stack`。
- 基础：`Extended.Text`、`Extended.Image`、`Extended.Divider`、`Extended.Button`。

v1 schema 是 renderer 已实现 props 的保守子集，并有意排除本 profile 不需要的字段。样式嵌套在 A2UI 组件对象的 `styles` 字段下；当前 renderer 会在渲染组件前将其展开。

## 事件合同

宿主可以提供 `allowedUiEvents` 数组，其中每个对象包含 `name`、`description` 和对象类型的 `contextSchema`。仓库 validator 支持以下 JSON Schema 子集：`type`、`const`、`enum`、本地 `$ref`、`allOf`、`oneOf`、`properties`、`required`、`additionalProperties`、`unevaluatedProperties`、`items`、数值边界、字符串长度和 `pattern`、数组边界。v1 宿主事件 schema 应限制在此子集内，以便 fixtures 可在本地校验。按钮 action 格式如下：

```json
{
  "action": {
    "event": {
      "name": "与 allowedUiEvents.name 完全一致的事件名",
      "context": {}
    }
  }
}
```

`context` 必须通过匹配事件的 `contextSchema` 校验。本 profile 只使用字面量 JSON 值，以避免无法解析的数据模型或函数绑定。禁止使用 `action.functionCall`。没有匹配事件时，答案不带操作按钮。v1 不包含文本输入或其他有状态控件。
