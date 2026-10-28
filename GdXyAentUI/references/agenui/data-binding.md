# AGenUI 数据绑定与响应式联动

## 数据模型路径

动态值使用 A2UI JSON Pointer：

```json
{"id":"title","component":"Text","text":{"path":"/page/title"}}
```

对应数据：

```json
{"version":"v0.9","updateDataModel":{"surfaceId":"answer-001","path":"/page","value":{"title":"示例标题"}}}
```

路径只能使用 `/` 分隔，不能写 `/page.title`。列表模板中的字段使用相对路径，例如 `{"path":"name"}`。

## 输入回写

`TextField.value`、`CheckBox.value`、`ChoicePicker.value`、`Slider.value` 和 `DateTimeInput.value` 绑定到当前 surface 的数据模型。用户操作由 AGenUI renderer 写回该路径；修改本身不发送模型请求。`ChoicePicker` 两种模式都使用字符串数组：`mutuallyExclusive` 最多一项，`multipleSelection` 多项；未选中均为 `[]`。`TextField` 即使使用 `number` 键盘也回写字符串，计算函数负责检查和转换数值。

## 计算边界

A2UI v0.9 只规定数据绑定，不规定四则运算。AGenUI catalog 提供 `formatNumber`、`formatCurrency`、`formatDate`、校验和逻辑函数，但不提供乘法/加法的通用内置函数。人数变化自动更新食材量需要：

1. 端侧注册受限的 `calculateNumber`（或业务等价函数），在 catalog 扩展中声明参数和返回类型；或
2. 宿主收到输入回写后安全计算，再发 `updateDataModel`。

Skill 不生成 `eval`、任意 JavaScript、字符串代码或未注册函数。函数失败时保留输入并显示可解释的静态状态，不伪造结果。

## 深层 FunctionCall

按钮 action 中的参数可能包含数据路径或嵌套函数调用。AGenUI 端侧需要对 `action` 注册 `registerDeepParseProperty`，并在点击时解析嵌套动态值；否则嵌套对象可能按字面值传给函数。Skill 只声明合同，不替端侧绕过解析器。
