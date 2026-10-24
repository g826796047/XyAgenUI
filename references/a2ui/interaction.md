# A2UIRender FunctionCall 交互合同

交互组件必须使用官方 catalog 字段和宿主实际声明的函数。按钮统一使用 `Button.action.functionCall`；函数名必须出现在 `a2ui.allowedFunctions`，并符合 [函数合同](functions.md)。本项目不生成 `Button.action.event`、`allowedUiEvents` 或服务端事件 context。

- 单选使用同一 `group` 的 `Radio`；多选使用 `Checkbox`，调用 `getCheckboxGroupValues` 时必须同时提供同 `group` 的 `CheckboxGroup`；下拉使用 `Select`。
- 文本或数字使用 `TextInput`，布尔选项使用 `Toggle`。有明确提交目的和对应的已授权 FunctionCall 时才提供 `Button`。
- 仅当宿主通过 `a2ui.allowedFunctions` 声明并注册相应函数时才生成对应交互。否则回答仍使用静态 A2UI 展示组件。
- 模型不预填用户选择。初始值只来自明确上下文、可靠工具结果或清楚标注的可编辑默认值。
- 输入和选择只更新端侧状态，不发起模型请求。回答流结束且校验通过后才可操作；提交期间锁定控件，失败保留内容并可重试，成功后同一按钮防重复提交。
- 确认时由端侧读取真实选择或表单数据，调用 `sendMsgToXiaoyi` 组装并发送同一对话的新用户消息。`sendMsgToXiaoyi.args.query` 支持 `${name}` 占位符；每个占位符对应一个同名参数，参数值由 `getCheckboxGroupValues`、`getRadioValue`、数据路径或安全表达式提供。模板与参数映射是静态定义，renderer 在确认时读取当前状态再替换；动态值不能由模型预填。详细字段和替换顺序见 [query-template.md](query-template.md)。

参考工作台在本地模拟安全函数调用，展示最终 query 或链接参数，并可通过 `window.xyA2uiHost.onFunctionCall(detail)` 接入宿主函数注册。

本项目不定义自定义 `ChoiceGroup`、表单提交 wire 字段、服务端事件或任意模型调用函数；`sendMsgToXiaoyi` 是端侧已注册的应用函数。表单联动见 [forms.md](forms.md)。
