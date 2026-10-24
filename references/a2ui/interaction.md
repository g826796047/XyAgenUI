# A2UIRender 交互合同

交互组件必须使用官方 catalog 字段和宿主实际声明的能力。服务端操作使用 `Button.action.event`；事件名必须存在于本轮 `allowedUiEvents`，`context` 必须是符合该事件 `contextSchema` 的字面量 JSON。模型不得创造事件或参数，也不输出 `functionCall`。

- 单选使用同一 `group` 的 `Radio`；多选使用 `Checkbox` 和可选的 `CheckboxGroup`；下拉使用 `Select`。
- 文本或数字使用 `TextInput`，布尔选项使用 `Toggle`。有明确提交目的和匹配白名单事件时才提供 `Button`。
- 仅当宿主声明相应 `a2ui.capabilities` 并提供事件白名单时才生成交互。否则回答仍使用静态 A2UI 展示组件。
- 模型不预填用户选择。初始值只来自明确上下文、可靠工具结果或清楚标注的可编辑默认值。
- 输入和选择只更新端侧状态，不发起模型请求。回答流结束且校验通过后才可操作；提交期间锁定控件，失败保留内容并可重试，成功后同一按钮防重复提交。
- 确认时由宿主读取真实选择或表单数据，组装自然语言 query，并作为同一对话的新用户消息发送。参考工作台在本地展示 query 预览，并可通过 `window.xyA2uiHost.onEvent(detail)` 接入宿主发送逻辑。

本项目不定义自定义 `ChoiceGroup`、表单提交 wire 字段、通用数据绑定或模型调用函数。表单联动见 [forms.md](forms.md)。
