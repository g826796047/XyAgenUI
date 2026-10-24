# A2UIRender 表单与联动

表单由数据模型命名空间和官方布局组件组成，不定义独立的 `Form` 组件。输入使用 `TextInput`、`Toggle`、`Radio`、`Checkbox` 或 `Select`；只读计算值使用绑定的 `Text` 或 `Progress`。输入的 `text`、`isOn`、选择状态等动态字段使用官方 `{ "path": "/..." }` 数据绑定。初始化和后续局部更新均使用标准 `updateDataModel`。

端侧可在 `Text.content`、`If.condition` 和支持动态值的 catalog 属性中使用完整表达式，例如 `{{ $__dataModel.form.people * $__dataModel.form.perPerson }}`。项目 validator 和浏览器参考 renderer 限制表达式为数据模型字段读取、算术/比较/逻辑运算和官方三元表达式；不执行 `eval`、任意脚本或未授权扩展函数。表达式必须独占属性值，不能把 `{{...}}` 拼接进普通文本。除零、非法类型或非有限数结果会锁定交互，修正输入后恢复。

提交按钮使用 `action.functionCall`。确认时端侧依据当前数据模型、用户选择和输入解析 `sendMsgToXiaoyi.args`，再将 `${name}` 参数嵌入自然语言 query。数值和布尔值应先用官方表达式转换为字符串；可选字段应使用表达式提供明确默认值，避免生成空 query。只读计算项应使用有意义的 `accessibility.label`；计算值也可直接通过绑定表达式作为函数参数。用户编辑不触发模型请求。没有匹配的已授权函数时只展示静态说明。

`examples/form-ingredients.jsonl` 展示人数、每人用量、口味、备注、餐具开关和自动计算总量。浏览器工作台可预览并生成 query，但真实输入行为、表达式兼容、可访问性和下一轮消息发送仍需在 A2UIRender/HarmonyOS 端验收。
