# XyAgenUI A2UI Skill 与端侧实现方案

本文说明本项目的 A2UI 方案和实现边界。项目的主要交付是指导模型稳定生成 A2UI；浏览器 renderer 是协议预览和验证工具，HarmonyOS 端侧 renderer 与宿主应用需要按第二部分单独实现和验收。

## 范围与依据

- 协议版本：A2UI `v0.9`。
- 默认组件目录：A2UIRender Extended catalog，`catalogId` 固定为 `ohos.a2ui.extended.catalog`。
- 协议字段基线：[A2UIRender 快照](../references/a2ui/official/README.md)，来源为 `GenerativeUI/A2UIRender` `develop` 分支提交 `20a32b91edc4ccdb02b248a08e856f95f83f9800`。
- 模型输出规则：[根目录 SKILL.md](../SKILL.md)。本方案中的“支持”首先指 Skill 可指导生成、仓库 validator 可校验；只有明确标为浏览器 renderer 已实现或 HarmonyOS 已验收时，才表示相应运行时能力。
- 鸿蒙协议设计对照：[鸿蒙A2UI协议设计.md](../鸿蒙A2UI协议设计.md)。该文件包含原生 catalog 和早期扩展设计；组件同名不代表字段、事件或运行时语义相同。

# 第一部分：Skill 方案设计

## 1. 目标与生成策略

每个用户 query 的回答都必须使用 A2UI JSONL，包括简单文本回答；简单内容通过布局根节点和 `Text` 承载。Skill 先识别用户目标、约束、未知信息、替代方案、风险和可执行的下一步，再按信息关系组织答案。摘要、比较、清单、步骤和真实图片等内容应主动使用合适的丰富组件，让用户更容易理解和决策；不得为了增加组件数量编造事实、图片、状态或交互。

消息采用标准 `createSurface`、`updateComponents`、`updateDataModel`、`deleteSurface`。支持同一 surface 上增量更新和一个更新消息中定义多个组件。回答 profile 固定一个 surface 和上述 `catalogId`；组件字段严格遵循仓库内的 pinned Extended catalog。动态值只用官方数据路径绑定和 Skill 明确允许的安全表达式子集，不输出任意脚本或 `eval`。

Skill 负责生成约束、组件选择、FunctionCall 参数映射和动态值。`tools/validate_a2ui_chat.py` 负责对 JSONL、catalog schema、组件图、表达式子集、函数合同、`a2ui.allowedFunctions` 和资源策略作离线校验。二者都不等同于 HarmonyOS renderer 的运行时实现。

## 2. 当前支持的组件

以下 21 个组件属于当前 Skill/validator 允许的 Extended catalog 组件。属性和样式以 [官方快照](../references/a2ui/official/extended_catalog.json) 为准。“浏览器参考实现”仅描述仓库的预览 renderer；HarmonyOS 设备能力状态见第二部分。

| 组件 | 用途 | 用户交互 | 当前浏览器参考实现 |
| --- | --- | --- | --- |
| `Text` | 标题、正文、说明或绑定后的动态结果 | 无 | 支持文本和项目安全表达式子集 |
| `Image` | 展示真实图片资源及说明 | 无 | 支持受允许域名策略约束的图片 URL |
| `Divider` | 分隔回答中的信息组 | 无 | 支持 |
| `Progress` | 展示数值进度或状态 | 无 | 支持常用 value/total |
| `Button` | 确认、继续或触发宿主动作 | 点击后调用运行时白名单中的本地函数 | 支持 `action.functionCall`、query/链接预览和 `onFunctionCall` 宿主回调 |
| `TextInput` | 收集文本、整数或小数 | 输入并更新本地控件/绑定状态 | 支持常用文本、数字输入和数据模型回写 |
| `Toggle` | 收集布尔开关状态 | 点击开/关 | 支持本地状态及绑定回写 |
| `Radio` | 在同一 `group` 内单选 | 选择一个选项 | 支持组内单选和本地状态 |
| `Checkbox` | 提供一个可选项 | 勾选或取消 | 支持组内多选和本地状态 |
| `CheckboxGroup` | 对同组 Checkbox 执行全选/取消全选 | 全选或清空 | 支持 |
| `Select` | 从下拉选项中选择一项 | 选择选项 | 支持常用选项和绑定回写 |
| `Row` | 横向排列内容，适用于并列信息 | 子节点按需交互 | 支持基础布局 |
| `Column` | 纵向分组，是常用根布局 | 子节点按需交互 | 支持基础布局 |
| `List` | 展示纵向清单/容器内容 | 子节点按需交互 | 支持普通子节点容器；不支持模板循环实例化或列表滚动事件合同 |
| `Stack` | 叠放需要空间重叠的内容 | 子节点按需交互 | 支持基础布局呈现 |
| `Grid` | 网格排列比较项或同类条目 | 子节点按需交互 | 支持基础自适应网格 |
| `NavContainer` | 承载导航页面内容 | 只有实现导航行为的运行时才有导航交互 | 目前按普通容器展示，不实现页面导航语义 |
| `Tabs` | 在多个视图间切换 | 点击 Tab 切换内容 | 支持基本切换 |
| `TabContent` | 定义 `Tabs` 的单个面板及标题 | 由所属 Tabs 切换 | 支持基本面板呈现 |
| `Web` | 声明网页资源区域 | 网页内部交互需浏览器/宿主实现 | 只显示受控占位，不加载网页 |
| `If` | 根据条件显示一个分支 | 条件随受支持的数据变化而重新计算 | 支持项目安全表达式子集的条件分支 |

组件被允许生成或通过 schema 校验，只能说明协议形状受支持。浏览器 renderer 对组件的呈现仍是参考实现，且不保证覆盖 catalog 每一个属性、样式或 HarmonyOS 原生行为。

## 3. 交互组件和 query 的工作原理

交互分为两类：组件本地状态变化和提交后的本地函数调用。Radio、Checkbox、Select、TextInput、Toggle 的编辑只更新 renderer 当前 surface 的选择状态或数据模型，不自动向模型发送 query。按钮使用 `action.functionCall`；函数必须由本轮 `a2ui.allowedFunctions` 声明，且符合端侧函数合同或官方 Extended catalog schema。需要数据联动时，Skill 可按 catalog 合同生成 `onChange` 等本地 handler；没有所需函数时退化为静态 A2UI。

对于灵活的自然语言 query，推荐使用模板合同，详见[模板化 Query 合同](../references/a2ui/query-template.md)：

1. 宿主在 `a2ui.allowedFunctions` 声明并注册 `sendMsgToXiaoyi`，以及参数所需的 `getCheckboxGroupValues`、`getRadioValue` 等官方 catalog 函数。
2. Skill 在按钮的 `action.functionCall.args` 中生成 query 模板和命名参数，例如“我想吃 `${food}`，需要 `${number}` 人一起合作”。参数值使用 `{ "call": "getCheckboxGroupValues", "args": {"group":"foods"} }`、数据路径或安全表达式描述。
3. 用户修改控件时，renderer 保存实际值。模型不得预测、预填用户选择，也不得把动态选择值写进 JSONL。
4. 回答流完成后，用户点击确认；端侧 renderer/宿主按当前 surface 状态解析 FunctionCall 参数，校验引用和值，再按模板占位符生成最终 query。编辑与 `onChange` 联动不发送 query。
5. 宿主将 `sendMsgToXiaoyi` 生成的最终 query 作为同一对话的新用户消息发送。A2UI v0.9 定义 UI 消息和组件，不定义 `${name}` 插值或对话发送；这是本项目与宿主约定的应用层合同。

该合同实现的是“在端侧按当前组件值组装 query”，不是模型端动态监听，也不是 A2UI 协议内置的 prompt 拼接能力。query 模板只接受简单命名占位符；参数读取可使用官方动态值/扩展函数，不支持模板内条件或脚本。

表单联动与 query 提交相互独立：输入改变数据模型路径，renderer 重新计算支持的表达式并刷新绑定内容；确认时再读取当前输入/计算结果生成 query。详细合同见[交互](../references/a2ui/interaction.md)、[表单](../references/a2ui/forms.md)和[模板 query](../references/a2ui/query-template.md)。

## 4. 鸿蒙协议设计对照：Skill 当前未支持的能力

本表按项目目标（指导模型生成当前 A2UIRender Extended profile）判断支持情况，不表示原鸿蒙设计文档的实现完整性。它覆盖《鸿蒙A2UI协议设计.md》第 3 章扩展设计和第 4 章附件合同；对于组件，“支持”是可生成并由 validator 按 pinned catalog 校验，不能推导出 HarmonyOS 端已验收。表中未支持的原生组件不会因为名称相似而自动兼容。

| 章节 | 鸿蒙协议设计内容 | 当前 Skill/validator 状态 | 说明 |
| --- | --- | --- | --- |
| 第 2/3 章 | A2UI v0.9 的四种消息和增量组件/数据更新 | 支持，profile 有收窄 | 接受 `createSurface`、`updateComponents`、`updateDataModel`、`deleteSurface`；项目回答固定单 surface 和固定 Extended catalog，不实现 catalog 协商。 |
| 第 2 章 | 原生基础 catalog 的 18 个组件及其原生字段/语义 | 不支持 | 当前目标是 Extended catalog；原生组件合同与同名扩展组件合同不视作等价。 |
| 第 3/4 章 | Extended catalog 的 21 个组件 | 支持生成和 schema 校验 | 具体运行时行为按第二部分区分；不代表每项均已 HarmonyOS 验收。 |
| 第 3/4 章 | 非当前 Extended catalog 的组件名、catalog 和卡片专用字段 | 不支持 | Skill 和 validator 只接受当前 `ohos.a2ui.extended.catalog` 及其组件字段。 |
| 第 2 章 | 多 catalog 能力协商、动态选择 catalog | 不支持 | 固定 `ohos.a2ui.extended.catalog`。 |
| 第 3/4 章 | 旧设计中的 `createSurface.theme`、`send__DataModel` 等扩展字段 | 不支持 | 当前项目 profile/validator 不接受这类旧扩展。 |
| 第 3/4 章 | 基于 `listeners.handlerGroups` 的监听链 | 部分支持 | Skill/validator 只开放 catalog 声明的组件 handler 和白名单函数；浏览器参考 renderer 尚未执行通用 handler 链，HarmonyOS 需验证 handlerGroups/顺序/局部变量语义。 |
| 第 3/4 章 | catalog 扩展函数作为 UI 事件链执行 | 部分支持 | Skill 可生成并由 validator 校验官方函数和 `a2ui.allowedFunctions`；浏览器参考实现只模拟 getter/query/链接预览，不执行 `setDataModel` 等任意本地 handler；HarmonyOS 端需确认函数注册与调用时机。 |
| 第 3/4 章 | 完整表达式语法、完整内置变量和全部扩展函数 | 部分支持 | Skill、validator 和浏览器参考 renderer 覆盖数据路径、算术/比较/逻辑及三元表达式；模板字符串、循环/事件局部变量、窗口/主题变量、内置函数全量覆盖和全部扩展函数仍不支持。 |
| 第 3/4 章 | 模板 children、数组循环实例化和局部循环变量 | 不支持 | `List` 当前按显式组件 ID 子节点渲染，不实例化 catalog `TemplateChildren`。 |
| 第 3/4 章 | 设备窗口断点、主题/颜色模式变量和响应式规则 | 不支持 | 不实现 `__WindowSize`、`__WindowBreakpoint`、`__ColorMode` 等设备上下文响应。 |
| 第 3/4 章 | 原生 `Button.action.event` 服务端事件 | 不支持（有意禁用） | 项目只使用 `Button.action.functionCall`；validator 拒绝 `action.event`，交互参数经运行时函数注册合同约束。 |
| 第 3/4 章 | 原生组件 change/appear handler 与完整事件链语义 | 部分支持 | Skill/validator 接受受 catalog schema 约束且函数已授权的 handler；浏览器 renderer 当前不执行通用 handlerGroups，端侧仍需核验事件载荷、顺序和状态更新语义。 |
| 第 3/4 章 | 原协议中超出 pinned Extended catalog 的专有属性、样式和语义 | 不支持或需逐项确认 | Skill 只能使用 catalog snapshot 声明的字段；浏览器 renderer 也只映射常用子集。 |

# 第二部分：端侧及渲染器方案设计

## 1. 实现层次与当前状态

本仓库包含离线 validator 和一个浏览器参考 renderer，不包含 HarmonyOS 应用内的 `SurfaceController` 集成。浏览器参考 renderer 适合粘贴/流式播放 JSONL、验证 schema 和查看本地交互/query 预览；它不能证明 A2UIRender 在 HarmonyOS 设备上的布局、输入、表达式、无障碍或生命周期正确。

| 层 | 当前已有 | 仍需端侧/产品实现或设备验收 |
| --- | --- | --- |
| Skill 与 validator | 生成规则、21 组件 schema 检查、组件树/动态值/白名单/context/query 模板验证 | 根据目标业务继续维护 prompt 与兼容性用例；validator 通过不代替 renderer 测试 |
| 浏览器参考 renderer | JSONL 流式解析、四类消息、常用组件呈现、局部数据更新、安全表达式子集、交互状态、FunctionCall query/链接预览和 `window.xyA2uiHost.onFunctionCall(detail)` 回调 | 不执行通用 catalog handler；Web 是占位；NavContainer 无导航；样式和组件属性非完整实现；不是 HarmonyOS UI |
| HarmonyOS A2UIRender renderer | 本仓库没有设备侧实现或集成测试证据 | 按 `CatalogFactory.extended()` 和 `SurfaceController` 接入后逐项实现并验证下列能力 |
| 宿主对话应用 | 本仓库仅定义 `a2ui.allowedFunctions`、FunctionCall 参数合同和浏览器回调接口 | 注册并执行已声明函数；将 `sendMsgToXiaoyi` 生成的最终 query 作为同一会话 user 消息发送，处理请求生命周期、错误、取消和会话状态 |

## 2. HarmonyOS 端侧 renderer 需要支持的功能

### 消息流与 surface 生命周期

- 从模型流中按 JSONL 行增量解析，处理不完整 chunk、消息错误、结束、取消和恢复；仅在 `createSurface` 后应用组件更新。
- 按 A2UI v0.9 实现 `createSurface`、多组件 `updateComponents`、可重复/局部 `updateDataModel` 和 `deleteSurface`；管理 surface 隔离和组件 ID。
- 在最终树尚未完整时显示合法的增量内容；校验 root、子引用和组件定义，失败时提供可诊断状态，避免白屏或将错误数据继续用于交互。
- 对话 profile 默认 catalog 固定为 `ohos.a2ui.extended.catalog`。若宿主未来要允许其他 catalog，需另行设计能力协商，当前 Skill 不会生成该流程。

### 组件、布局与可访问性

- 接入 Extended catalog 21 个组件，逐组件验证 schema、属性、动态值、样式和布局表现；特别确认 `List`、`Tabs`/`TabContent`、`If`、`Web`、`NavContainer` 的宿主语义。
- 在窄屏和动态字体下验证 `Row`、`Grid`、文本换行、图片比例和内容滚动；提供无障碍 label/description、焦点顺序、键盘/屏幕阅读器操作和可触控尺寸。
- 对未实现的组件或字段提供明确降级/错误状态，不静默丢弃会改变业务含义的交互。
- 对图片和 Web 执行 URL scheme、域名、网络权限、内容安全与加载失败策略；Web 导航和外部打开规则由宿主明确控制。

### 数据模型、输入与联动

- 按 A2UI 数据路径语义维护每个 surface 的 DataModel，支持初始化、局部创建/替换/删除和组件绑定。
- 让 `TextInput`、`Toggle`、`Radio`、`Checkbox`、`CheckboxGroup`、`Select` 的用户修改写回端侧真实状态，并触发绑定值、表达式和 `If` 分支刷新；输入变化本身不调用模型。
- 对 `Text.content`、`If.condition` 和 catalog 声明支持动态值的字段实现所采用的表达式子集；校验类型、除零、非有限结果、路径缺失和错误恢复。若直接采用 A2UIRender runtime，则确认其支持范围与本项目 Skill 子集一致。
- 若业务需要完整 HarmonyOS 协议设计中的 listeners、扩展函数或模板 children，应作为额外 runtime 能力设计、声明和安全评审；不能假定本项目当前合同已具备。

### 交互提交与 query 发送

- 按回答流状态锁定控件；回答完成且校验通过后启用可操作组件，提交中禁用重复点击。
- `Button.action.functionCall` 只能调用当前 `a2ui.allowedFunctions` 中的已注册函数；validator 校验函数名、参数 schema、动态值和 Button 归属，宿主校验 session、surface、函数和参数。
- 选择/表单值由端侧按 surface 与组件 ID 保存。Radio、Checkbox、Select、输入和 Toggle 的变化只更新本地状态；切换 surface/回答时不能串值。
- `sendMsgToXiaoyi`：端侧读取实际选择和字段，解析 `args` 中的动态值，按 `${name}` 占位符形成 query。动态值来自当前状态，不信任模型预填内容；空值、失效引用和不合法选择应拒绝提交，不应发送部分 query。
- 当前 `端侧当前已支持的functioncall.txt` 实现会把空/缺失参数替换为空字符串，且对数字或布尔值也可能插入空字符串。端侧接入需先校验占位符和参数键完全对应、每个值非空且为字符串或字符串数组；数字/布尔值由 Skill 生成字符串表达式后再传入。
- query 组装成功后交给宿主作为同一会话的新 user 消息发送；网络请求不由 A2UI 组件或模型执行。失败保留用户输入并允许重试，成功后标记已提交并防止重复发送。
- 明确错误/取消的恢复方式和提交状态回写；敏感字段不得不加控制地写入日志或分析事件。

## 3. 交互落地验收

HarmonyOS 端侧验收至少覆盖以下路径；浏览器测试只能作为前置参考：

| 验收项 | 预期结果 |
| --- | --- |
| 流式 chunk 与四类消息 | 分片 JSONL 可正确组装；组件/数据更新和删除按 surface 生效；非法顺序有可诊断错误 |
| 基础与 Extended 组件 | 所有 Skill 开放组件逐项 schema/布局验收；未知属性或组件有明确处理；窄屏、动态字体和无障碍可用 |
| 数据绑定与表单联动 | 输入写回 DataModel；人数变化后计算展示同步刷新；表达式错误能恢复，输入修改不发模型请求 |
| 选择行为 | Radio 单选切换，Checkbox 多选/取消，CheckboxGroup 全选，Select/Toggle/TextInput 状态正确并按 surface 隔离 |
| 函数安全 | 未授权/未知函数或 schema 不匹配时不执行；回答未完成不能提交；连续点击只产生一次提交 |
| 模板 query | 例如实际选择披萨、沙拉且人数为 4 时生成“我想吃披萨、沙拉，需要4人一起合作”；更改选择后组装结果随之变化；不得使用模型推测值 |
| 提交生命周期 | 成功后状态可见并防重复；明确失败后保留输入并可重试；取消、超时和会话切换不串发 |
| 资源和页面行为 | 图片/Web 域名与失败策略有效；NavContainer 仅在真实导航实现并通过测试后才可由 Skill 用于导航工作流 |

建议使用 A2UIRender 的 `SurfaceController` 与 `CatalogFactory.extended()` 加载本仓库 fixtures，验证解析、组件、绑定、交互、action callback 和多 surface 隔离，再在实际 HarmonyOS 设备或模拟器检查原生布局及辅助功能。浏览器工作台、Python validator 和 schema 测试不能替代该验收。

## 4. 后续实现边界

本项目当前完成的是 Skill 合同、协议快照、离线校验和浏览器参考体验。HarmonyOS renderer 的完整组件、数据模型响应式刷新、事件处理和 query 发信需要端侧独立实现及验收。原生 catalog、listeners handlerGroups、完整表达式/函数、模板 children、断点/主题响应式和未列入当前 profile 的能力，只有在端侧确实需要且具备安全/兼容性验证后，才能扩充 Skill 与 validator 的允许范围。
