# FunctionCall 函数合同

函数调用发生在 AGenUI renderer/宿主端。函数名不是任意代码；模型只能生成运行时已注册、且由 `a2ui.allowedFunctions` 声明的函数。Skill 只生成 `action.functionCall`，不生成 `action.event`。

## AGenUI catalog 函数

官方 catalog 提供：`required`、`regex`、`length`、`numeric`、`email`、`formatString`、`formatNumber`、`formatCurrency`、`formatDate`、`pluralize`、`openUrl`、`token`、`and`、`or`、`not`。这些函数的精确参数和返回类型以 `references/agenui/agenui_catalog.json` 的 `functions` 与 `$defs` 为准。

## 项目宿主函数

当前迁移保留端侧已有函数：

| 函数 | 参数 | 用途 |
| --- | --- | --- |
| `sendMsgToXiaoyi` | `query` 字符串及 `${name}` 对应的动态参数 | 读取当前表单/选择状态，拼成下一轮 query 并发送同一会话的新用户消息 |
| `openSuperlink` | `url` | 打开超级链接 |
| `openApplink` | `url` | 跳转 AppLink |
| `openDeeplink` | `bundleName`、`url` | 跳转指定应用 DeepLink |

这些函数不是 A2UI 核心内置函数，而是宿主通过 AGenUI `registerFunction` 注册的端侧扩展。真机必须用 HarmonyOS 对应 `IFunctionCall` 实现并注册，浏览器参考 renderer 只模拟调用。

## query 模板

```json
{
  "id": "confirm",
  "component": "Button",
  "child": "confirm-text",
  "action": {
    "functionCall": {
      "call": "sendMsgToXiaoyi",
      "args": {
        "foods": {"path": "/meal/foods"},
        "people": {"path": "/meal/people"},
        "query": "我想吃${foods}，需要${people}人一起合作"
      }
    }
  }
}
```

`${name}` 只能是简单名称，且必须与 `args` 中的参数键一一对应。renderer 在按钮点击时读取最新数据；模型不能把用户选择预先写进 JSONL。端侧函数合同要求占位符解析为非空字符串或字符串数组：数组由宿主按现有中文连接规则转换，数字/布尔值应先通过返回字符串的 catalog 函数或宿主转换函数转换。空值、未知参数、重复占位符和未闭合占位符应拒绝发送。

## 自定义计算函数

需要人数联动食材总量时，端侧可注册：

```json
{
  "call": "calculateNumber",
  "returnType": "number",
  "args": {
    "left": {"path": "/form/people"},
    "right": {"path": "/form/perPerson"},
    "operator": "multiply"
  }
}
```

这不是本目录默认内置函数；只有运行时注册并扩展 catalog 后才允许生成。否则使用宿主计算后的 `updateDataModel`，不得把它当作 AGenUI 原生四则运算。

本项目 overlay 已声明 `calculateNumber` 的参数 schema，但不代表任何端侧已注册。输入来自 TextField 路径时可能是数字字符串，宿主需按数值格式严格检查后转换；拒绝空值、布尔值、非法类型、除零与非有限结果。返回值始终是数值，再由 `formatNumber` 转成展示文本或 query 字符串。
