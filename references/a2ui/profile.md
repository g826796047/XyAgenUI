# XyAgenUI A2UIRender 对话 Profile

协议固定为 A2UI `v0.9`，组件目录固定为 `ohos.a2ui.extended.catalog`。所有用户答案都输出 JSONL；纯文本答案使用 `Column` 根和 `Text.content` 承载。

首条消息是 `createSurface`，至少包含 `surfaceId` 和 `catalogId`。随后针对同一 surface 发送标准 `updateComponents`、`updateDataModel` 或 `deleteSurface`。`updateComponents.components` 是至少一个组件的数组，允许多个组件一批发送和重复发送同一非 root 组件的完整定义。`updateDataModel` 可重复使用标准 JSON Pointer：带 `value` 替换/创建，省略 `value` 删除。`deleteSurface` 后不得继续更新。

组件 ID 在 surface 内唯一稳定；最终图从 `root` 可达，无循环、孤儿和多父节点。root 使用布局组件，正文至少包含 `Text`。组件和属性严格来自 [官方 Extended catalog](official/extended_catalog.json)，不得使用 `Extended.*`、`.form` catalog、`Form`、`ChoiceGroup`、`NumberInput`、`Output` 或 `computed`。

官方 catalog 支持字面量、`{"path":"/path"}` 数据绑定和 `{{ ... }}` 表达式。表达式只使用官方语法、数据模型变量、算术/比较/逻辑运算及宿主明确授权的扩展函数；最大长度和嵌套限制遵循快照。不得执行任意 JavaScript、`eval` 或未声明函数。数据路径是字面 JSON Pointer，不能把表达式放入 `path` 对象。

先完整保留事实，再按信息关系选择 `Column` 分组、`Row`/`Grid` 比较、`List` 清单、`Tabs` 多视图、`Divider` 分隔、`Progress` 状态、`Image` 真实资源和 `If` 条件分支。没有实际决策点时不强行生成输入；缺少宿主能力或事件时静态展示。
