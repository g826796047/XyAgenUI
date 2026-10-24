# FunctionCall 函数合同

XyAgenUI 的交互只使用 A2UIRender Extended catalog 的 `functionCall`。运行时在 `context.a2ui.allowedFunctions` 中声明本轮可以执行的函数；Skill、validator 和 renderer 都必须拒绝未声明或未知函数。函数调用发生在端侧，模型输出的函数名和参数只是受校验的声明，不是任意代码。

## 按钮调用

按钮使用：

```json
{
  "id": "confirm",
  "component": "Button",
  "label": "确认并继续",
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

`action.event`、服务端事件白名单和 `allowedUiEvents` 不属于本项目交互合同。按钮调用必须等流结束、组件校验通过和 `enabled` 条件满足后才执行；端侧应防止重复调用，失败可重试。

## 端侧自定义函数

以下函数来自 `端侧当前已支持的functioncall.txt`，只有出现在 `allowedFunctions` 中时才可生成：

| 函数 | 参数 | 用途 |
| --- | --- | --- |
| `sendMsgToXiaoyi` | `query` 字符串；可带 `${name}` 对应的非空字符串、非空字符串数组或受支持的动态函数参数 | 按 query 模板读取当前控件值并发送同一对话的新用户消息 |
| `openSuperlink` | `url` 字符串 | 打开超级链接 |
| `openApplink` | `url` 字符串 | 跳转 AppLink |
| `openDeeplink` | `bundleName`、`url` 字符串 | 跳转指定应用 DeepLink |

`sendMsgToXiaoyi` 的 `${name}` 只允许简单名称，且必须与 `args` 中的参数键完全对应。参数值在调用时解析；不把用户实际选择写入 JSONL。数组由端侧按现有实现转换为中文列表，数字和布尔值应先通过安全表达式转换为字符串。当前端侧函数对缺失值会替换为空串；为避免发送不完整 query，本项目 validator、参考 renderer 和宿主接入层都应在调用前拒绝空值、未知参数、重复或未闭合占位符。

## 官方 Extended 函数

只有目标 A2UIRenderer 已注册并且 `a2ui.allowedFunctions` 声明后，才可使用官方 catalog 中的函数：

- `getRadioValue({"group": "..."})`
- `getCheckboxGroupValues({"group": "..."})`
- `getToggleValue({"componentId": "..."})`
- `getSelectValue({"componentId": "..."})`
- `setDataModel({"path": "...", "value": ...})`
- `setAttributes({"componentId": "...", "value": {...}})`
- `navigate({"componentId": "...", "targetComponentId": "..."})`
- `break({})`

这些函数可作为组件 `onChange`、`onClick` 或 `onAppear` 的本地 handler，也可作为动态值中的嵌套 `functionCall`，但只能用于其 catalog 定义的属性和事件。`sendMsgToXiaoyi` 只可放在确认按钮的 `action.functionCall` 中，不能作为控件变化 handler。项目浏览器 renderer 对 query 和链接函数提供安全模拟；不执行任意插件、网络请求或 JavaScript。

## 运行时上下文示例

```json
{
  "a2ui": {
    "catalogId": "ohos.a2ui.extended.catalog",
    "allowedFunctions": ["sendMsgToXiaoyi", "getCheckboxGroupValues"]
  }
}
```

`${name}` 是 `sendMsgToXiaoyi` 的参数替换格式，不需要额外 query-template capability；运行时函数授权由 `a2ui.allowedFunctions` 控制。所有函数调用的参数、组件引用和可执行函数仍需 validator 二次校验。
