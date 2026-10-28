# AGenUI 组件合同（中文摘要）

完整字段以同目录的 `agenui_catalog.json` 为准。下面按生成决策说明用途和交互；不在这里发明 schema 外字段。

## A2UI 协议组件

| 组件 | 作用 | 主要字段 | 用户交互 |
| --- | --- | --- | --- |
| `Text` | 标题、正文、说明 | `text`、`variant` | 无；支持简单 Markdown 的基础文本能力 |
| `Image` | 图片 | `url`、`description`、`fit`、`variant` | 无；宿主负责网络/资源策略 |
| `Icon` | 内置或 SVG 图标 | `name` | 无 |
| `Video` | 视频播放器 | `url` | 播放器原生交互 |
| `AudioPlayer` | 音频播放器 | `url`、`description` | 播放、暂停和进度由原生端处理 |
| `Row` | 横向布局 | `children`、`justify`、`align` | 子组件决定 |
| `Column` | 纵向布局 | `children`、`justify`、`align` | 子组件决定 |
| `List` | 可滚动/模板列表 | `children`、`direction`、`align` | 子组件决定 |
| `Card` | 单子节点卡片容器 | `child` | 子组件决定 |
| `Tabs` | 标签页 | `tabs`（每项 `title`、`child`） | 切换标签 |
| `Modal` | 浮层对话框 | `trigger`、`content` | 由触发组件打开/关闭 |
| `Divider` | 分隔线 | `axis` | 无 |
| `Button` | 操作入口 | `child`、`variant`、`action` | 点击执行 FunctionCall |
| `TextField` | 文本、数字、密码输入 | `label`、`value`、`variant`、`validationRegexp` | 输入并回写绑定值 |
| `CheckBox` | 布尔勾选 | `label`、`value` | 勾选/取消并回写绑定值 |
| `ChoicePicker` | 单选/多选 | `label`、`variant`、`options`、`value`、`displayStyle`、`filterable` | 选择；单选与多选的值都是字符串数组 |
| `Slider` | 范围数值 | `label`、`min`、`max`、`value` | 拖动并回写数值 |
| `DateTimeInput` | 日期/时间输入 | `label`、`value`、`enableDate`、`enableTime`、`min`、`max` | 选择日期/时间 |

## AGenUI SDK 扩展

`Table` 展示字符串列和行；`Carousel` 展示图片/内容轮播；`Web` 展示宿主允许的网页；`RichText` 展示受 renderer 支持的 HTML 富文本。它们随 AGenUI SDK 提供，但网页、链接、媒体权限仍由宿主控制。

## Playground 或宿主注册组件

`Markdown` 支持标准 Markdown 和增量流式追加；`Chart` 支持 `line`、`donut`、`bar` 数据；`Lottie` 播放动画。这三个组件只有在运行时注册并在能力上下文中声明时才可生成；没有声明时使用 `Text`/`RichText`/`Image`/`Table` 降级。

## 通用样式

AGenUI 使用 `styles` 的 CSS 风格字段，例如 `background-color`、`border-radius`、`padding`、`margin`、`font-size`、`font-weight`、`color`、`flex-grow`。尺寸使用 `px`，四值 `padding`/`margin` 使用完整四值写法；组件专用字段仍以 catalog schema 为准。不要把旧 Extended 的 `itemMargin`、`fontColor`、`content`、`src` 带入新输出。

## 生成边界

不得生成 catalog 没有的组件或字段；不得编造媒体 URL、图表数据、库存、价格和用户选择。横向关系超过三项时用多行、纵向分组、`Tabs` 或 `Table`，避免窄屏溢出。按钮必须有可见的 `Text` 子节点和真实 `action`，不能用 Text 冒充按钮。
