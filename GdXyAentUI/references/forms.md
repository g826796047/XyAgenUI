# AGenUI 表单和交互联动

## 选择

单选：`ChoicePicker` 使用 `variant: "mutuallyExclusive"`，`value` 绑定字符串数组，长度最多为 1。多选：使用 `variant: "multipleSelection"`，`value` 同样绑定字符串数组。两种模式初始都为 `[]`。选项的 `label` 和 `value` 必须同时存在，`value` 稳定且唯一。发送函数收到的是选项值；要输出中文 query，使用可读中文值，或由宿主明确提供编码转标签的映射。

```json
{"id":"foods","component":"ChoicePicker","label":"选择食物","variant":"multipleSelection","options":[{"label":"披萨","value":"pizza"},{"label":"沙拉","value":"salad"}],"value":{"path":"/meal/foods"},"displayStyle":"checkbox"}
```

使用 ChoicePicker 直接维护选择数组，不生成旧 CheckboxGroup 读取合同。当前 catalog 和 validator 不接受 getCheckboxGroupValues；兼容扩展需要同时修改项目 catalog、函数合同和端侧实现。

## 输入和确认

`TextField` 的 `variant` 可选 `shortText`、`longText`、`number`、`obscured`，它们的 `value` 均为字符串；`CheckBox` 通过布尔 `value`；`Slider` 通过数值 `value`；`DateTimeInput` 通过日期时间字符串 `value`。输入变化只更新本地数据模型。确认按钮的 FunctionCall 才是 query 发送边界。

## 实时计算

如果宿主声明了 `calculateNumber`，展示组件可以把 `text` 或其他动态字段绑定为该函数调用的返回值；修改输入后 AGenUI 会按其 FunctionCall 解析和刷新机制重算。若宿主没有该函数，Skill 必须生成静态说明或等待宿主更新数据模型，不能生成不可执行的运算表达式。

数字字段参与 `sendMsgToXiaoyi` 模板时，参数用 `formatNumber` 等返回字符串的函数转换后再交给宿主发送函数；布尔值要用 `formatString` 或宿主字符串转换函数转换。不要直接把 number/boolean 当作 `${name}` 插值参数。

## 端侧必须保证

- 每个 surface 独立保存输入和选择；切换回答不能串状态。
- 流结束前控件不可确认；提交中防重复，失败可重试。
- 校验失败、空选项、错误路径和函数未授权时不发送部分 query。
- 组件校验采用 catalog 的 `checks: [{condition, message}]`，TextField 也可使用 `validationRegexp`。按钮执行前应同时检查相关输入；不得忽略校验而发送 query。
- 宿主注册 `sendMsgToXiaoyi` 前，对 `${name}` 参数做完整性和类型校验。
