# XyAgenUI A2UIRender 方案与实现边界

## 目标与当前基线

所有用户 query 的回答都输出 A2UI v0.9 JSONL。简单回答使用 `Column` + `Text`；复杂回答根据内容关系组合布局、展示与交互组件。组件目录和 wire `catalogId` 固定为 A2UIRender Extended catalog `ohos.a2ui.extended.catalog`，协议快照来自 `develop` 提交 `20a32b91edc4ccdb02b248a08e856f95f83f9800`。

本方案描述当前仓库已实现内容及明确边界，不代表 HarmonyOS 设备端的全部 A2UI 能力。协议依据见 [`references/a2ui/official/`](../references/a2ui/official/)，模型输出规则见 [`SKILL.md`](../SKILL.md)。

## 已实现

- **Skill**：要求每个答案使用 A2UI；按信息关系发散考虑并选择丰富组件；保留事实；只在有实际决策点和运行时能力时生成交互。
- **消息与组件校验**：validator 面向 A2UI v0.9 和固定 Extended catalog，检查 JSONL envelope、组件 schema、组件图、动态值、表达式、白名单事件及资源域名。
- **消息类型**：接受 `createSurface`、`updateComponents`、`updateDataModel`、`deleteSurface`；支持多组件更新、数据路径替换/创建/删除和组件增量定义。profile 将回答约束为单个 surface 与固定 catalog。
- **组件目录**：Skill/validator 允许官方 Extended catalog 中的 21 种组件：`Text`、`Image`、`Divider`、`Progress`、`Button`、`TextInput`、`Toggle`、`Radio`、`Checkbox`、`CheckboxGroup`、`Select`、`Row`、`Column`、`List`、`Stack`、`Grid`、`NavContainer`、`Tabs`、`TabContent`、`Web`、`If`。字段和 schema 以 pinned catalog 为准，不沿用旧 `Extended.*` 命名。
- **交互与表单合同**：支持由白名单和能力声明约束的 `Button.action.event`；浏览器工作台支持常用输入、选择、开关、表单数据更新、表单 query 预览。模型不能生成自定义事件或 `functionCall`。
- **表达式子集**：validator 和浏览器 renderer 支持数据模型绑定及受限算术、比较、逻辑表达式；示例覆盖人数变化后自动计算食材总量。浏览器不使用 `eval`。
- **浏览器工作台**：支持粘贴 JSONL、逐条流式处理、样例预览、schema 校验、常见组件展示和交互结果预览。实现合同见 [`references/a2ui/renderer-contract.md`](../references/a2ui/renderer-contract.md)。

## 鸿蒙协议设计文档对照

对照文件为项目根目录 [`鸿蒙A2UI协议设计.md`](../鸿蒙A2UI协议设计.md)。该文档包含原生 catalog 和早期 `Extended.*` 扩展合同；当前项目迁移到 A2UIRender 官方 Extended catalog，因此文档中的名称、字段或运行时语义只有与 pinned snapshot 相符时才适用。

| 设计文档能力 | 当前状态 | 实现边界 |
| --- | --- | --- |
| A2UI v0.9 消息与增量更新 | 已支持 | 支持四种消息及局部数据更新；项目回答 profile 固定单 surface，`createSurface` 只接受固定 `catalogId` 和 `surfaceId`。 |
| Catalog 能力协商 | 不支持 | 不交换多个 catalog 能力，不动态选择 catalog。 |
| 原生 18 组件 catalog | 不支持 | 当前只按官方 Extended catalog 校验和生成。扩展组件同名不等于原生组件的 schema、属性和行为也兼容。 |
| 21 个官方 Extended 组件定义 | Skill/validator 支持 | 组件名和字段来自快照；这不表示浏览器 renderer 已完整实现所有字段，也不证明 HarmonyOS 设备端已验收。 |
| 旧版 `Extended.*` 命名和旧字段 | 不支持 | 只保存在 `references/a2ui/legacy/` 供迁移查阅。 |
| 文档中的 `theme`、`send__DataModel` 等 createSurface 扩展字段 | 不支持 | 当前 profile/validator 拒绝这些额外字段。 |
| 白名单服务端 `action.event` | 部分支持 | 校验事件名及 context schema；浏览器工作台可在确认后产生结果/query 预览，真实发送由宿主接入。 |
| `listeners.handlerGroups` 事件链 | 不支持 | 旧设计文档的 listeners 合同与当前 catalog/profile 不同。 |
| `action.functionCall` 和本地扩展行为 | 不支持 | validator 拒绝 `functionCall`；参考 renderer 不执行 catalog 扩展函数或自定义行为。 |
| 表单本地输入、选择与联动 | 部分支持 | 有浏览器样例与 query 预览；只覆盖项目定义的安全动态值子集，HarmonyOS 端的输入回写和响应式刷新仍需设备验证。 |
| 文档中全部表达式语法、变量与函数 | 不支持 | 不实现模板字符串、三元表达式、循环/事件局部变量、窗口/主题变量及 `format`、`size` 等函数；只支持明确实现的表达式子集。 |
| 模板 children 和循环实例化 | 不支持 | 当前参考 renderer 按组件 ID 列表渲染，不实例化 `children` 模板对象或循环作用域。 |
| 响应式断点与多设备变量 | 不支持 | 未实现 `__WindowSize`、`__WindowBreakpoint`、`__ColorMode` 及断点变化响应。 |
| `If` 条件组件 | 部分支持 | 浏览器可按当前受限表达式选择分支；不支持基于窗口/主题变量的响应式设备布局。 |
| 通用与组件专属样式 | 部分支持 | catalog schema 校验官方字段；浏览器 renderer 仅映射部分常用样式。HarmonyOS 原生布局、完整组件样式和设备适配未由本仓库验证。 |
| `Web` 组件 | 部分支持 | validator 检查 URL/资源域；浏览器仅显示受控占位，不加载网页。 |
| `NavContainer` 导航行为 | 部分支持 | 浏览器按普通容器展示子节点，未实现页面导航语义。 |
| HarmonyOS `SurfaceController` 真机/模拟器兼容 | 未验证 | 仓库没有设备侧 renderer 集成测试；需在实际 A2UIRender/HarmonyOS 环境单独验收。 |

## 行为策略

回答前识别目标、约束、未知信息、替代方案、风险和下一步，再收敛成事实完整、可操作的内容。摘要使用分组，比较使用 `Row`/`Grid`/`Tabs`，步骤使用 `Column`/`List`/`Progress`，真实图片使用 `Image` 与说明。有实际决策且宿主能力可用时才生成输入或选择；不得编造资源、价格、库存、选择或业务状态。

按钮只使用 `action.event`，事件名和 context 必须符合本轮宿主白名单与 schema。没有匹配能力或事件时静态呈现。表单输入只改变端侧状态；确认后由宿主读取当前值并将 query 作为同一对话的新用户消息发送。

## 已知差距与后续验收

当前明确未覆盖项包括原生 18 组件合同、catalog 协商、旧版 `Extended.*`/`listeners` 事件链、扩展函数执行、完整表达式和循环模板、响应式窗口变量、多 surface 管理、完整样式映射，以及 `Web` 加载和 `NavContainer` 导航语义。它们不能从“schema 可通过”或“组件名有渲染分支”推断为运行时已支持。

后续如需宣称 HarmonyOS 端兼容，应在目标 A2UIRender `SurfaceController` 与 `CatalogFactory.extended()` 环境中逐项验证组件 schema、动态绑定、表达式刷新、事件回调、资源策略、无障碍和多 surface 生命周期。本地浏览器测试只验证本仓库的参考实现，不能替代设备验收。
