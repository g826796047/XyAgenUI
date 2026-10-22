# 对话 Extended Renderer 合同（v1）

本文记录用于定义对话组件目录的端侧 renderer 行为。机器可读属性白名单见 [`../../catalogs/xy-a2ui-chat-basic/v1/catalog.json`](../../catalogs/xy-a2ui-chat-basic/v1/catalog.json)。生成规则以对话 Skill、[协议 Profile](profile.md) 和组件目录为准；本文说明它们所依赖的 renderer 行为。端侧实现不在本仓库中，因此部署前仍需在目标客户端核实这些行为。

## Registry 映射

默认 Extended registry 对 v1 对话组件的映射如下：

| A2UI 组件 | Renderer 组件 | 本 profile 依赖的行为 |
| --- | --- | --- |
| `Extended.Card` | `Card` | 可选分组容器，支持标题/说明、填充、描边、布局、间距、内边距、圆角和背景图属性。 |
| `Extended.Row` | `ExtendedRow` | 水平 flex 容器；`itemMargin` 优先于 `space`，二者都会设置子项间距。 |
| `Extended.Column` | `ExtendedColumn` | 垂直 flex 容器，间距规则与 Row 相同；默认沿交叉轴拉伸子项。 |
| `Extended.Stack` | `ExtendedStack` | 叠层容器，子项位于绝对定位的全尺寸图层中；它不是纵向布局容器。 |
| `Extended.Text` | `ExtendedText` | 展示 `content`；默认字号为 14px、行高为 1.2，默认自动换行。 |
| `Extended.Image` | `ExtendedImage` | 展示 `src`，默认使用响应式最大宽度和 cover 裁切；SVG 图片支持 `fillColor`。 |
| `Extended.Divider` | `ExtendedDivider` | 默认水平分隔线；默认粗细为 1，默认颜色为 `#E5E5E5`。 |
| `Extended.Button` | `ExtendedButton` | 展示 `label`，默认启用；只有配置交互宿主时 renderer 才会附加动作。 |

对话 catalog 有意只开放组件 props 和通用样式的保守子集。具体名称、类型、枚举和必需字段以 catalog schema 为准；不要根据更宽泛的 renderer 能力推断额外 props。

## 样式与动作处理

渲染前，tree renderer 会把组件嵌套的 `styles` 对象展开为传给 Extended 组件的 props。通用样式覆盖尺寸、flex 行为、间距、边框、颜色、显隐、裁切和背景。各组件 renderer 再解释其支持的样式键；未列入 chat catalog 的键不属于对话合同。

配置交互宿主时，renderer 支持 `action.event` 和 `action.functionCall`。对话生成只使用本轮 `allowedUiEvents` 中的 `action.event`，并提供通过对应 schema 校验的字面量 context。Skill 不得输出 `functionCall`，也不得依赖 renderer 推断事件。

## 流式与组件图语义

- v0.9 parser 接受 `createSurface`、单组件 `updateComponents.component`、批量 `updateComponents.components` 和 `updateDataModel`。本 profile 每条更新只发送一个组件，且不使用 `updateDataModel`。
- parser 会将 `createSurface` 归一化为组件图使用的 `surfaceId`。`catalogId` 仍是必需的 wire 元数据，但 parser 和当前静态 renderer registry 不会用它选择组件目录。
- 定义组件 ID `root` 会创建新组件图并清空旧节点；每个回答只定义一次。
- 子 ID 可以早于对应组件定义到达，组件图会跟踪尚未解析的父子关系。回答结束时必须解析所有子节点引用。
- 重新定义非 root 组件会替换其 props。每次都要发送完整的当前 props，包括累计文本。再次发送 `children` 会替换原有子节点列表，并删除已移除的子树。

客户端仍需部署对应的 Extended registry 和交互宿主，才能渲染这些组件并分发白名单 UI 事件。
