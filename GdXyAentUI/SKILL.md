---
name: gd-xy-agenui
description: |
  使用高德 AGenUI catalog 生成可由 AGenUI 三端渲染的 A2UI v0.9 流式界面。适用于把用户问题转换成丰富的布局、内容、表单、选择、媒体、图表或 FunctionCall 交互；所有回答都必须由 A2UI 消息承载。
---

# GdXyAentUI A2UI Skill

本 Skill 是独立的高德 AGenUI 版本。生成协议以 `references/agenui/agenui_catalog.json` 为唯一组件合同，线协议使用 A2UI v0.9，固定 `catalogId` 为 `urn:a2ui:catalog:agenui_catalog`。不要使用原 XyAgenUI 的 `Extended.*`、`ohos.a2ui.extended.catalog`、`CheckboxGroup` 或旧字段。

## 输出边界

- 每个用户 query 都输出 A2UI v0.9 JSONL；JSONL 之外不输出解释性裸文本。
- 简单回答也必须建立 `root`，通常使用 `Column -> Text`。复杂回答根据内容关系组合布局、内容、媒体、表单和操作组件。
- 流式输出时每行都是一个可独立解析的 JSON 对象；通常先发送 `createSurface`，再发送一个或多个 `updateComponents` / `updateDataModel`，结束时由宿主结束流。
- `createSurface.catalogId` 必须是 `urn:a2ui:catalog:agenui_catalog`，所有后续消息使用同一 `surfaceId`。
- 组件树中的子组件只能通过 ID 引用。`Card` 的 `child` 只能引用一个组件；多个内容先放进 `Column` 或 `Row`。
- 同一个组件 ID 只放在一个父节点下。按钮的 `Text` 标签只由 `Button.child` 引用，不要同时把它放进根布局的 `children`，否则会重复显示或出现多父节点。

这是协议下限，不是复杂回答的固定模板：

```jsonl
{"version":"v0.9","createSurface":{"surfaceId":"answer-001","catalogId":"urn:a2ui:catalog:agenui_catalog"}}
{"version":"v0.9","updateComponents":{"surfaceId":"answer-001","components":[{"id":"root","component":"Column","children":["answer"]},{"id":"answer","component":"Text","text":"在这里承载完整回答。"}]}}
```

生成前读取组件中文摘要；对将使用的组件，检查 catalog 中对应定义。需要选择、表单或发送 query 时，读取函数合同和对应样例（`examples/selection-multiple.jsonl`、`examples/form-ingredients.jsonl`）。示例数据只展示协议结构，不能当作用户事实。

## 先发散，再收敛

回答前先识别用户目标、事实与不确定性、可选方案、风险、下一步和真实决策点，再选择能表达这些关系的最少层级。默认使用丰富但有理由的结构，不为了数量堆组件：

- 摘要或多主题：`Card` 包一层 `Column`，用 `Text` 标题、正文、`Divider` 和必要的 `Row` 指标分组。
- 比较：用 `Row`、`Card` 或 `Table` 表达相同维度；窄屏时改为纵向 `Column` 或 `Tabs`。
- 步骤和清单：用 `Column` / `List`，需要进度时使用 `Slider` 只表达可调整数值，不能把它伪装成进度条。
- 图片、音频、视频和网页：只有存在真实资源且运行时声明了对应组件/域名时才使用，并配说明文字。
- 富文本：运行时声明 `Markdown` 时可用它承载 Markdown 流；否则使用 `Text`、`RichText` 和结构化组件。不要把 HTML 塞进 `Text`。
- 没有实际决策点时不强行添加输入；有决策点时优先使用 `ChoicePicker`、`CheckBox`、`Slider`、`TextField`、`DateTimeInput` 或 `Button`。

## 当前可用组件

组件名称、字段和允许值以 catalog 为准：

- A2UI 协议组件：`Text`、`Image`、`Icon`、`Video`、`AudioPlayer`、`Button`、`Row`、`Column`、`Card`、`List`、`Tabs`、`Modal`、`Divider`、`TextField`、`CheckBox`、`Slider`、`ChoicePicker`、`DateTimeInput`。
- AGenUI SDK 扩展：`Table`、`Carousel`、`Web`、`RichText`。
- Playground/宿主注册组件：`Markdown`、`Chart`、`Lottie`。只有本轮能力声明包含这些名字时才能生成，否则降级为静态 A2UI 组件。

常用字段迁移如下：`Text.text`、`Image.url`、`Button.child`、`TextField.value`、`CheckBox.value`、`ChoicePicker.options/value`、`Slider.value`、`DateTimeInput.value`。按钮标签要创建一个 `Text` 子组件，不能使用旧的 `label` 字段。

本轮提供 `a2ui.allowedComponents` 时，它是完整的可用组件白名单，基础组件也不能超出此列表。未提供时可使用 22 个协议/SDK 组件，`Markdown`、`Chart`、`Lottie` 仍需明确声明。不要生成 catalog 未声明的 `onChange`/`listeners` 字段；输入绑定由 SDK 回写，联动由动态值/宿主函数完成。

## 交互和 FunctionCall

只生成 `action.functionCall`，不生成 `action.event`。函数必须同时满足：存在于本轮 `a2ui.allowedFunctions`，并且属于 [函数合同](references/functions.md) 或 AGenUI catalog 的注册函数。

- `ChoicePicker` 单选使用 `variant: "mutuallyExclusive"`，多选使用 `variant: "multipleSelection"`；两种模式的 `value` 都绑定字符串数组（未选中为 `[]`，单选为 `["选项值"]`），不能把单选写成字符串。query 要呈现中文标签时，优先把选项 `value` 设置为可读中文；业务编码需要宿主显式映射。
- `CheckBox.value` 绑定布尔数据路径；不要把它当成旧 Checkbox group。多个复选框的选中值应由宿主读取绑定数组，或使用本轮声明的读取函数。
- `TextField`、`Slider`、`DateTimeInput` 的 `value` 绑定到数据模型。`TextField` 包括数字键盘类型都以字符串保存；`Slider` 保存数值；`DateTimeInput` 保存 ISO 字符串。修改只更新当前 surface 的本地状态，不自动发送 query。
- 有必填、范围或格式条件时使用官方 `checks: [{condition, message}]` 和 `validationRegexp`；条件使用已声明的 `required`、`numeric` 等函数。不要生成旧 `enabled`、`minSelected` 或 `onChange` 属性来模拟校验。
- 确认按钮使用 `Button + action.functionCall`，只有在流结束、校验通过和输入满足条件时可执行。宿主负责防重复、失败重试和发送边界。
- 本项目保留端侧已有的 `sendMsgToXiaoyi`、`openSuperlink`、`openApplink`、`openDeeplink` 作为自定义函数。它们未在运行时声明时，不得生成。
- `sendMsgToXiaoyi.args.query` 使用字面模板和 `${name}` 占位符；每个占位符必须对应一个同名参数。参数可使用数据路径或嵌套 `functionCall`，实际值在按钮点击时由 renderer 读取。用户选择不得被模型预填。
- `sendMsgToXiaoyi` 的占位符参数必须在最终插值时得到非空字符串或字符串数组。数字用已注册的 `formatNumber` 等字符串返回函数转换；布尔值用 `formatString` 对绑定路径插值，或使用宿主已注册的转换函数。不要把数字、布尔值直接传入只接受字符串的宿主函数。
- 区分两种插值：`sendMsgToXiaoyi.query` 的 `${name}` 引用同一 `args` 的命名参数；catalog `formatString.args.value` 中的 `${/form/name}` 引用数据路径。普通字符串不自动做计算。输出原始 JSONL，不加外层单引号或模板字符串，不使用旧 `{{ ... }}` 表达式。
- 使用 `ChoicePicker.value` 绑定数组并作为 query 参数，不生成旧 `getCheckboxGroupValues`。若将来需要兼容函数，必须先扩展本项目 catalog、函数合同和端侧注册；仅在上下文中增加名字不能使当前 validator 接受未知函数。
- 链接优先使用宿主声明的 `openSuperlink` / `openApplink` / `openDeeplink`；若宿主只注册 AGenUI 的 `openUrl`，才使用 `openUrl`。

## 表单和联动

组件之间通过数据模型路径共享状态，不直接引用另一个组件 ID。人数、单价、每人用量等输入写入 `/form/...`，展示组件通过 `{ "path": "/form/..." }` 读取。

AGenUI 官方 catalog 提供校验、格式化和逻辑函数，但没有通用四则运算函数。需要实时计算时只能使用宿主声明的安全函数（例如 `calculateNumber`）或由宿主在数据模型更新时计算；不得生成 `eval`、任意 JavaScript 或未经注册的函数。若宿主没有计算能力，显示输入和说明，不能伪造计算结果。

需要深度解析按钮 action 中嵌套动态参数时，宿主必须对 `Button.action` 注册 AGenUI 的 deep-parse 属性，并注册相应 FunctionCall；Skill 不把解析逻辑写成代码。

## 校验和参考资料

生成后按需读取并执行：

- [组件目录](references/agenui/component-catalog.md)：组件、字段、样式和布局约束。
- [数据绑定](references/agenui/data-binding.md)：JSON Pointer、模板相对路径和动态值。
- [交互函数合同](references/functions.md)：`sendMsgToXiaoyi`、链接、自定义计算和运行时白名单。
- [表单联动](references/forms.md)：ChoicePicker、TextField 和本地状态/计算边界。
- [协议参考](references/protocol/README.md)：A2UI v0.9 与 AGenUI 来源快照。
- [方案设计](docs/方案设计.md)：Skill、组件能力、宿主/renderer 适配和迁移边界。

使用 `node tools/validate_agenui.mjs <jsonl> [context.json]` 校验消息。失败时修正 JSONL、组件字段、引用、数据路径、FunctionCall 和能力白名单后再交付。
