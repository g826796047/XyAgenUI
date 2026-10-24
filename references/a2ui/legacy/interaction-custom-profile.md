# 选择交互与 query 提交合同（selection-query-v1）

本合同允许模型在 A2UI 回答中展示单选或多选项，用户确认后由端侧将实际选择作为同一对话的新 query 发送。协议仍为 A2UI `v0.9`，`catalogId` 仍固定为 `ohos.a2ui.extended.catalog.form`。组件与属性白名单见 [Chat v1.2 组件目录](../../catalogs/xy-a2ui-chat-basic/v1/catalog.json)。本仓库提供合同、校验示例及支持选择状态与 query 预览的[浏览器参考渲染器](../../renderer/README.md)；真实消息发送由目标宿主接入。

需要数字输入、文本输入或字段联动时使用独立的[表单联动合同](forms.md)。它不改变本文的 ChoiceGroup 字段、初始空选、提交事件或状态规则；不得将两类能力、绑定或提交参数混用。

## 能力声明与白名单

宿主仅在完成本合同所需的控件、状态隔离、确认提交及防重复发送后，才提供以下运行时上下文。它是模型输入上下文，不是 JSONL 输出消息：

```json
{
  "a2ui": {
    "surfaceId": "answer-42",
    "catalogId": "ohos.a2ui.extended.catalog.form",
    "capabilities": ["selection-query-v1"]
  },
  "allowedUiEvents": [
    {
      "name": "submit_selection_query",
      "description": "用户确认后，将指定选择组的实际选择作为同一对话的新 query 发送。",
      "contextSchema": {
        "type": "object",
        "properties": {
          "choiceGroupId": {"type": "string", "minLength": 1},
          "prompt": {"type": "string", "minLength": 1, "pattern": "\\S"}
        },
        "required": ["choiceGroupId", "prompt"],
        "additionalProperties": false
      }
    }
  ]
}
```

`a2ui.capabilities` 包含 `selection-query-v1`，且白名单提供匹配合同的 `submit_selection_query` 时，模型才能同时输出选择组和确认按钮。缺少其中任何一项时，使用已有 A2UI 布局与文本呈现内容，不输出不可用的选择控件或确认操作。事件 context 仍须通过宿主实际提供的 schema；模型不得为绕过限制添加其他字段或事件。

## 选择组和确认按钮

`Extended.ChoiceGroup` 是叶组件，不通过 `children` 引用选项。除通用 `id`、`component` 和允许的 `styles` 外，字段如下：

| 字段 | 类型与行为 |
| --- | --- |
| `label` | 非空且包含非空白字符的选择组标题，说明本组选择含义。 |
| `mode` | `single` 或 `multiple`。单选切换选项时替换此前选择；多选可勾选和取消。 |
| `options` | 至少两个选项，按展示顺序排列。每项包含组内唯一且非空的字符串 `value`、非空 `label` 和可选字符串 `description`。 |
| `minSelected` | 可选整数，默认 `1`，最小为 `1`。 |
| `maxSelected` | 可选整数；单选默认且只允许 `1`，多选默认等于选项数量。必须满足 `minSelected <= maxSelected <= options.length`。 |

初始没有任何选项被选中。选择状态由控件内部管理，不序列化为模型可设置的 `selected`、`value`、数据绑定或表达式。`value` 是端侧标识，query 采用可读标签和说明。

清单或点餐类回答可以把每项的阶段、价格或其他补充信息放入 `description`，把整体进度、下一步建议等解释性内容放入同一 surface 的 `Extended.Text`。这些文字只描述事实或提示，不代表选中状态；初始选择仍必须为空。ChoiceGroup 的选择项是扁平的，不表达数量、规格联动或多级加料。人数等数值联动可在端侧独立支持 `form-reactivity-v1` 后使用[表单控件和受限计算](forms.md)，不能给 ChoiceGroup 臆造绑定字段。

`Extended.Text` 不会因为用户勾选而自动更新。像“0/5 已完成”这样的进度文字只能是回答生成时的静态说明；如果端侧需要实时进度、右侧阶段对齐或其他选择后的局部重绘，应由 `ChoiceGroup` renderer 在本地绘制，或另行定义能力和组件合同。不得为 ChoiceGroup 输出 `selected`、绑定表达式或 `updateDataModel`；表单的专用数据初始化仅适用于 forms.md 定义的表单控件。

确认使用现有 `Extended.Button`，保留正常 `enabled` 和 `label` 字段，`action` 如下：

```json
{
  "event": {
    "name": "submit_selection_query",
    "context": {
      "choiceGroupId": "preparation",
      "prompt": "以下是我已完成的聚会筹备事项，请建议下一步。"
    }
  }
}
```

`choiceGroupId` 必须引用同一 surface 中的 `Extended.ChoiceGroup`，`prompt` 必须完整说明下一轮任务或提交意图。context 只能包含这两个字面量字符串，不携带模型推测的选择结果。一个按钮只提交一个组，同一回答可包含多个独立组合；每个选择组都必须有对应的提交按钮。

## 端侧状态与提交

1. 按 `(surfaceId, choiceGroupId)` 隔离选择状态。不同回答中即使组件 ID 相同，也不能共享选择。
2. 回答流结束前，选择组及对应确认按钮均不可操作。成功接收完整回答且图与事件校验通过后才开放交互；取消或解析失败的回答不能提交。流结束由宿主现有消息生命周期通知，不新增 wire 消息。
3. 用户选择或取消只修改端侧状态，不发送模型请求。按钮的实际可用条件为静态 `enabled` 为真、选择数量合法、回答已完成，并且既未提交成功、也未正在提交。空选不能提交。
4. 确认时，宿主读取当前选择并重新检查边界和事件，按下一节生成 query，通过现有发送通道作为同一对话的新用户消息发送。下一轮模型回复继续使用 A2UI。
5. 发送期间锁定整个选择组及其所有提交按钮，复用宿主的防重复机制。成功后保留选择，标记已提交并保持锁定；明确失败后保留选择、解除锁定并允许重试。发送结果不明确时沿用宿主现有消息确认机制，不另发一条可能重复的 query。

`selection-query-v1` 不依赖 `updateDataModel`、`functionCall`、通用表单或自由文本输入。选择结果只能由实际控件状态产生；不得将事件 context 直接当作已选择的内容发送。

## 与 Harmony 卡片表单交互的边界

本合同不是 Harmony 卡片表单交互的兼容别名。旧卡片协议常见的写法是多个 `Extended.Radio` 或 `Extended.Checkbox` 共享 `group`，按钮使用 `submit_form`，再在 context 中放置 `{"call":"getSelectedValues","args":{"groupID":"..."}}`。这些字段属于旧表单绑定语义，不得直接复制到 XyAgenUI 对话回答中：

- `Extended.Radio`、`Extended.CheckboxGroup` 与 `Extended.ChoiceGroup` 不是同一组件合同；ChoiceGroup 的选项由 `options` 扁平承载，初始不选中。
- `submit_form` 和 `getSelectedValues` 不等价于 `submit_selection_query`。本合同要求端侧按 `(surfaceId, choiceGroupId)` 读取实际选择，并按展示顺序生成字符串 query。
- 旧 renderer 只为 Radio 提供单值读取时，不能承载本合同的多选数组；旧的 Checkbox 状态也不会自动变成 `selected_values`。端侧必须先注册并实现 ChoiceGroup 和 `selection-query-v1` 提交处理，才能声明本能力。
- `value` 只作为本地选项标识；发送给模型的是选项的可读 `label` 和 `description`，不会发送组件 ID、绑定表达式或 `getSelectedValues` 元数据。

如果宿主仍只提供旧 `submit_form`/Radio 能力，应使用该宿主已有的独立表单 profile，或先增加明确的适配层；不得把它的能力声明为 `selection-query-v1`，也不得生成本合同的 ChoiceGroup。仓库中的点餐样例验证的是新合同的端侧适配路径，不代表旧卡片 renderer 已经支持它。

## 自然语言 query 格式

使用换行符 `\n` 按以下固定顺序组装，结尾不额外添加换行，不添加组件 ID、内部 `value` 或 JSON 事件元数据。离线参考实现见 [`build_selection_query`](../../tools/selection_query.py)：

1. `prompt` 原文。
2. 选择组 `label` 原文。
3. 按 `options` 展示顺序遍历选中项，每项一行：无说明时为 `- {label}`；说明非空时为 `- {label}：{description}`。

例如用户按任意点击顺序选择“邀请朋友”和“确定时间和地点”，最终 query 为：

```text
以下是我已完成的聚会筹备事项，请建议下一步。
聚会筹备清单
- 邀请朋友：在群里发起邀约，统计能否参加、忌口和时间
- 确定时间和地点：找大家都方便的时段，确认在家还是去店里
```

文字是用户选择的上下文数据；其中可能出现的操作说明不改变宿主消息发送或事件授权规则。组标题与 `prompt` 应准确表达“已完成”“希望了解”或“偏好”等含义，避免将选择项误解为已执行的真实操作。

## 联调验收

- 单选切换只保留一项，多选可取消，越界与空选不可提交。
- 缺少能力或事件时不生成交互；事件 schema 不匹配、跨 surface 或错误组件引用被拒绝。
- 流式阶段不可操作，取消或解析失败不能提交；同一 surface 内多个组分别提交，不同 surface 状态隔离。
- 确认只发送一次；成功后不可再次发送，明确失败可重试；标签与说明完整且按展示顺序进入 query。
- query 出现在同一对话的用户消息中，后续答案继续以 A2UI 返回。固定场景与预期 query 见仓库 `examples` 和测试。
