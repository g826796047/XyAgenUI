# FunctionCall Query 模板合同

`sendMsgToXiaoyi` 用于在用户确认时，把 A2UI 控件的当前值填入自然语言模板。宿主必须在 `a2ui.allowedFunctions` 中声明并注册 `sendMsgToXiaoyi`。`${name}` 是参数替换语法，不需要额外的 query-template capability。该合同是 `action.functionCall.args` 中的静态元数据；实际选择和输入只由 renderer/宿主在调用时读取。

```json
{
  "action": {
    "functionCall": {
      "call": "sendMsgToXiaoyi",
      "args": {
        "foods": {
          "call": "getCheckboxGroupValues",
          "args": {"group": "foods"}
        },
        "people": "{{ $__dataModel.meal.people + '' }}",
        "query": "我想吃${foods}，需要${people}人一起合作"
      }
    }
  }
}
```

`query` 只允许 `${name}` 形式的简单命名占位符（名称符合 `[A-Za-z][A-Za-z0-9_]*`），不支持嵌套、转义、条件、格式表达式或脚本。模板出现的占位符集合必须与 `args` 中除 `query` 外的参数键集合完全相同；插值按模板原文顺序完成，参数对象顺序不影响结果。参数只能是非空字符串或非空字符串数组；数字、布尔值必须先通过安全表达式转成字符串。空值或未定义值视为调用错误，不发送 query。

## 参数来源

参数值可以是：

| 形式 | 读取规则 |
| --- | --- |
| `{"call":"getCheckboxGroupValues","args":{"group":"..."}}` | 读取当前 group 选中的 Checkbox 值，按端侧已实现的中文连接规则生成字符串。至少选择一项。 |
| `{"call":"getRadioValue","args":{"group":"..."}}` | 读取当前 Radio group 的值；必须存在有效选择。 |
| `{"call":"getSelectValue","args":{"componentId":"..."}}` | 读取 Select 当前选项的显示值；必须存在有效选择。 |
| `{"call":"getToggleValue","args":{"componentId":"..."}}` | 读取 Toggle 的当前状态/标签；需要字符串时由调用函数或绑定表达式转换。 |
| `{"path":"/..."}` | 读取当前 DataModel JSON Pointer；必须指向当前 surface 的有效路径。 |
| `"{{ ... }}"` | 使用 Skill 允许的安全表达式计算，例如 `{{ $__dataModel.meal.people + '' }}`；不得调用任意函数。 |
| 字面量 | 只用于不依赖用户状态的固定片段或函数参数。 |

`sendMsgToXiaoyi` 的参数对象必须包含 `query`，并且除 `query` 外每个键都必须被 `${name}` 引用。多选数组由端侧函数按现有实现转换为“甲、乙和丙”形式；数字和布尔值须在参数中先转换为字符串。任何参数不得把用户的预选结果写死在 JSONL 中。

## 本地联动

组件 `onChange`、`onClick` 和 `onAppear` 的 handler 可以调用官方 catalog 函数，例如 `getCheckboxGroupValues` 后调用 `setDataModel` 更新计数。只有运行时已声明并注册的函数可以执行；联动不发送模型 query。query 发送必须由明确的 Button `action.functionCall` 触发。

## 示例结果

假设用户实际选中“披萨”和“沙拉”，人数输入 `4`，端侧调用 `sendMsgToXiaoyi` 后发送：

```text
我想吃披萨、沙拉，需要4人一起合作
```

参考 renderer 通过 `window.xyA2uiHost.onFunctionCall(detail)` 暴露调用结果；真正发送网络请求和创建下一轮用户消息仍由 HarmonyOS 宿主完成。
