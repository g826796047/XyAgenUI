# XyAgenUI 对话 A2UI v0.9 Profile

本 profile 定义 XyAgenUI 对话回答使用的 A2UI v0.9 消息、组件图增量更新和事件规则。生成答案时以本 profile、[对话 Skill](../../SKILL.md)、[选择交互合同](interaction.md)、[表单联动合同](forms.md) 和 [Chat v1.2 组件目录](../../catalogs/xy-a2ui-chat-basic/v1/catalog.json) 为准。本仓库包含[浏览器参考渲染器](../../renderer/README.md)；Harmony/OHOS 端侧 parser/renderer 源码不在本仓库，已有行为和新增交互要求均需在目标部署中验收。

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

`a2ui.capabilities` 是可选的字符串数组。选择交互须同时具备 `selection-query-v1` 和白名单事件 `submit_selection_query`；表单联动须同时具备 `form-reactivity-v1` 和白名单事件 `submit_form_query`。宿主只在实现对应合同的全部行为后才声明能力。两类能力彼此独立，缺少某类能力或事件时，模型不生成该类交互，继续用已有布局和展示组件完整回答。

## 消息合同

- 协议版本固定为 `v0.9`。
- 回复使用 JSONL，每行是一个完整 JSON 对象。只有完整行写入后才能 flush；不得将尚未写完的 JSON 对象交给 parser。
- 第一行是 `createSurface`，包含运行时 `surfaceId` 和固定值 `ohos.a2ui.extended.catalog.form` 作为 `catalogId`。
- 后续各行针对同一 surface 发送 `updateComponents`；满足表单双门控时，还须按[表单联动合同](forms.md)发送一次 `updateDataModel` 初始化。
- 每条 `updateComponents` 消息必须包含 `components` 数组，且本对话 profile 约定数组恰好包含一个组件，以支持流式处理。`updateComponents.component` 单对象是旧的非 canonical 形状，不属于本项目输出合同。
- 首先且仅定义一次组件 ID `root`。它必须是布局组件或 `Extended.Card`。graph renderer 将 `root` 的首次定义作为重置操作，并把它渲染为 surface 根节点。
- 子节点以有序组件 ID 引用。流式期间允许先引用后定义，但回复结束时每个引用都必须可解析；最终结构必须是一棵无环树，所有输出组件都能从 `root` 到达，且每个非 root 组件只能有一个父节点、同一父节点不得重复引用同一子节点。
- 非 root 组件 ID 可以重新定义以流式更新。重新定义会替换该节点的属性，因此每次都必须发送完整的当前属性集合。文本更新携带累计内容，不是等待追加的片段。
- `updateDataModel` 只用于受能力门控的表单初始化：紧跟首次 root 定义、位于其他组件定义之前，且一轮恰好一次。结构与路径范围见[表单联动合同](forms.md)。无表单时禁用该消息；`deleteSurface`、任意数据模型回写和任意表达式仍不属于本回答 profile。
- 解释性正文使用静态的 `Extended.Text.content`；选择项文字使用选择组件标签与说明。表单的可编辑值及只读动态结果使用专用表单控件，不向 Text 或 ChoiceGroup 添加绑定字段。

最小答案树包含 `createSurface`、一个引用 `Extended.Text` 的 `Extended.Column` 根节点，随后是文本组件定义。这是问候或单一事实的协议下限；摘要、多主题说明、比较与步骤回答应主动组合组件表达内容关系，不将最小树作为所有回答的默认结构。

## 组件

catalog v1.2.0 仅允许以下组件名：

- 布局：`Extended.Card`、`Extended.Row`、`Extended.Column`、`Extended.Stack`。
- 基础：`Extended.Text`、`Extended.Image`、`Extended.Divider`、`Extended.Button`。
- 选择交互：`Extended.ChoiceGroup`，仅在能力和提交事件均可用时使用。
- 表单联动：`Extended.Form`、`Extended.NumberInput`、`Extended.TextInput`、`Extended.Select`、`Extended.Toggle`、`Extended.Output`，仅在表单能力和提交事件均可用时使用。Form 不能作为 root 或嵌套。

布局与基础组件 schema 是已有 renderer props 的保守子集；选择与表单组件是端侧需新增适配的组件。样式嵌套在 A2UI 组件对象的 `styles` 字段下；renderer 在渲染组件前将其展开。组件目录新增字段不会自动赋予旧 renderer 相应能力。表单数据、数值计算和状态生命周期集中见[表单联动合同](forms.md)。

内容优先采用清晰分组：摘要和多主题使用 `Card`、`Column`、`Divider` 与文本样式区分层次；比较和标签值可用 `Row`，窄屏改用纵向分组；步骤使用布局组件组织；可信图片搭配说明。尽可能发挥组件表达力，同时保留事实完整性，不为增加组件数量制造装饰、图片或操作。`Stack` 仅用于真实叠层。

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

`context` 必须通过匹配事件的 `contextSchema` 校验，并只使用字面量 JSON 值；即使已启用表单，事件参数也不能放绑定对象、计算表达式或函数调用。禁止使用 `action.functionCall`。没有匹配事件时，答案不带操作按钮。选择提交的状态和 query 规则见[选择交互合同](interaction.md)，表单确认见[表单联动合同](forms.md)；其他事件继续按宿主提供的白名单处理。
