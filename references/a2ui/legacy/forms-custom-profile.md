# 表单与本地联动合同（form-reactivity-v1）

本合同为对话回答增加可编辑表单和确定性的本地数值联动。协议仍为 A2UI `v0.9`，wire `catalogId` 固定为 `ohos.a2ui.extended.catalog.form`；组件合同升级为 `xy-a2ui-chat-basic` `1.2.0`。消息和树结构遵循 [Profile](profile.md)，组件字段以 [catalog](../../catalogs/xy-a2ui-chat-basic/v1/catalog.json) 为准。本文件集中定义表单语义；既有 [ChoiceGroup 选择交互](interaction.md) 仍独立使用 `selection-query-v1`。

本仓库提供 Skill、合同、样例、离线校验、参考计算逻辑及[浏览器参考渲染器](../../renderer/README.md)，后者支持本地编辑、联动和确认 query 预览。Harmony/OHOS 设备 renderer 和真实消息发送仍需目标端适配。宿主完成本合同后才能声明能力；仅支持 A2UI parser 或已有选择控件不足以声明支持表单联动。

## 能力与事件双门控

宿主同时声明 `form-reactivity-v1` 并提供匹配的 `submit_form_query` 白名单事件后，模型才能生成表单、绑定、计算规则及初始化数据。运行时上下文示例：

```json
{
  "a2ui": {
    "surfaceId": "answer-42",
    "catalogId": "ohos.a2ui.extended.catalog.form",
    "capabilities": ["form-reactivity-v1"]
  },
  "allowedUiEvents": [
    {
      "name": "submit_form_query",
      "description": "确认当前表单，将有效输入及派生结果作为同一对话的新 query 发送。",
      "contextSchema": {
        "type": "object",
        "properties": {
          "formId": {"type": "string", "minLength": 1},
          "prompt": {"type": "string", "minLength": 1, "pattern": "\\S"}
        },
        "required": ["formId", "prompt"],
        "additionalProperties": false
      }
    }
  ]
}
```

缺少能力或事件任一项时，继续用 `Card`、`Row`、`Column`、`Text` 等展示组件完整回答，不输出不可用的表单、绑定或数据消息。用户只需选择、无需数据联动时，也可在独立满足其双门控的前提下使用 ChoiceGroup。模型不得自行声明能力、创造事件或猜测用户填写结果。

## 组件与表单范围

| 组件 | 字段与用途 |
| --- | --- |
| `Extended.Form` | `id`、非空 `label`、有序 `children`，以及可选 `computed`；提供表单范围与分组容器。不能作为 `root`，不能嵌套。 |
| `Extended.NumberInput` | `label`、`value: {"path": "..."}`；可选 `min`、`max`、正数 `step`（默认 `1`）、`unit`。保存数字输入；步长从 `min`（缺省为 `0`）起算，用十进制精确校验倍数。 |
| `Extended.TextInput` | `label`、`value: {"path": "..."}`；可选 `required`（默认 `false`）、`maxLength`（默认 `1000`）。保存字符串输入。 |
| `Extended.Select` | `label`、`value: {"path": "..."}`、`mode: "single" | "multiple"`、`options`；可选 `minSelected`（默认 `1`）、`maxSelected`（单选为 `1`，多选默认为全部选项）。 |
| `Extended.Toggle` | `label`、`value: {"path": "..."}`。保存布尔输入。 |
| `Extended.Output` | `label`、`value: {"path": "..."}`；可选 `unit`。只读展示同表单任意类型输入的可读值，或数值计算结果。 |

这些组件具有通用 `id`、`component` 和 catalog 允许的 `styles`。`Form.children` 可经 `Card`、`Row`、`Column` 等已有布局组织控件；最终仍是一棵树。每个输入或 Output 只能属于一个 Form，不能位于表单外。确认按钮必须引用当前表单；一个表单必须有至少一个对应的确认按钮。

Select 的 `options` 至少两项，各项具有唯一且非空的 `value`、可读 `label` 和可选 `description`。单选保存一个字符串，多选保存不重复的字符串数组；非空选中值必须来自选项。`minSelected` 允许 `0`，默认 `1`；单选 `maxSelected` 固定为 `1`，多选默认全部选项，须满足 `0 <= minSelected <= maxSelected <= options.length`。数字、文本、选择和布尔值不能相互隐式转换。

输入草稿可保留 TextInput 空字符串、单选空字符串或多选空数组，使用户能够逐项填写。初始化与本地计算不因尚未填写必填文本或未达到最少选择数量而失败；确认前必须校验这些要求。`required: true` 的文本按去除首尾空白后非空判断。NumberInput 始终必须是符合类型、范围和步长的数值；不存在把空字符串当作数字的规则。

初始化值必须来自用户上下文、可靠工具结果或明确标注的可编辑假设。人数、每人份量等可分别设置为输入；由它们计算的食材总量为只读 Output。不要把模型预测的用户选择伪装成已填写的事实。普通 `Extended.Text.content` 和既有 ChoiceGroup 均不增加绑定语义；需要展示动态数值时使用 Output。

## 数据模型与消息顺序

每个表单字段的绑定路径固定为 `/forms/<formId>/<key>`。`formId` 是 Form 的组件 ID；它和 `key` 均匹配 `^[A-Za-z][A-Za-z0-9_-]*$`。禁止跨表单引用、数组下标、其他根路径、转义路径段或任意对象遍历。

含表单的回答必须严格依次发送：

1. `createSurface`。
2. 首次且唯一的 `root` 组件定义；root 使用已有布局组件。
3. 恰好一条根数据初始化消息 `updateDataModel`。
4. 其余组件的单组件 `updateComponents.components` 消息。

例如：

```json
{"version":"v0.9","updateDataModel":{"surfaceId":"answer-42","path":"/","value":{"forms":{"meal":{"people":4,"portionGrams":200}}}}}
```

`value` 只包含 `forms`；其下表单集合与最终 Form 集合完全一致。每个表单对象的初始 key 集合恰好等于其输入字段集合，值为对应类型的字面量。不得初始化派生字段、未使用字段或其他状态。每个输入字段只能有一个写入控件；计算目标不得覆盖输入，也不得由多个规则写入。没有表单时不发送 `updateDataModel`。

该消息只用于每轮初始化，不是模型在用户编辑后持续回写的通道。组件树和数据校验完整后，宿主计算初始派生值；用户修改只在本地更新。再次定义非 root 组件仍须遵守完整属性替换语义，不能借流式替换重置已开放的用户状态。

## 受限计算表达式

`Form.computed` 是可选规则数组，每条恰好包含 `path` 和 `expression`。目标 path 位于当前表单。每个派生字段都必须恰好由一个 Output 展示，且只读；Output 也可直接展示同表单任意类型的输入。Output 的展示能力不扩展计算表达式的类型，计算依赖仍仅允许数字。例：

```json
{
  "id": "meal",
  "component": "Extended.Form",
  "label": "聚餐食材估算",
  "children": ["people", "portion", "ingredients", "confirm"],
  "computed": [
    {
      "path": "/forms/meal/ingredientGrams",
      "expression": {
        "op": "multiply",
        "args": [
          {"path": "/forms/meal/people"},
          {"path": "/forms/meal/portionGrams"}
        ]
      }
    }
  ]
}
```

表达式只能是数值字面量、`{"path":"..."}` 或 `{"op":"...","args":[...]}`。不接受字符串表达式、模板插值、`call`、`functionCall` 或任意 JavaScript；宿主不得用 `eval` 执行模型输出。

| `op` | 参数与语义 |
| --- | --- |
| `add`、`multiply`、`min`、`max` | `2..16` 个数值参数；依次求和、相乘、取最小或最大。 |
| `subtract`、`divide` | 恰好两个数值参数，按参数顺序相减或相除；除数为零无效。 |
| `ceil`、`floor` | 恰好一个数值参数，分别向正无穷取整和向负无穷取整。 |
| `round` | 恰好两个参数；第二项必须是 `0..6` 的字面量整数，指定小数位，使用 half-up 舍入，不使用银行家舍入。 |

每个表单最多 `32` 条规则；每条表达式最多 `128` 个节点、嵌套深度最多 `12`。所有参与计算的数值及中间、最终结果必须有限且绝对值不超过 `10^12`，布尔值不能作为数字使用。不得静默截断、以零代替错误或让不支持的运算继续执行。

引用只允许当前 Form 的数字输入或数值派生字段；不能引用字符串、Select、Toggle、其他表单或未知字段。宿主须先验证全部依赖、目标唯一性和无环性，再按拓扑顺序计算。支持多级派生，例如人数与每人克数得出总克数，再除以 `1000` 得出千克数。

调整 `people` 从 `4` 到 `6`、`portionGrams` 保持 `200` 时，总量从 `800 g` 变为 `1200 g`。此处 `200 g/人` 是演示中的可编辑假设，实际食材比例应使用用户提供的数据或可靠来源；不得当作通用食用建议。

## 本地事务与提交生命周期

1. 按 `(surfaceId, formId)` 隔离状态。回答流结束且完整图、数据、计算与事件校验通过前，全部表单控件和确认按钮不可操作。取消、解析失败或未完成的回答不能提交。
2. 每次编辑先校验输入类型、数值范围与步长及选项有效性，再以当前输入快照重算全部受影响依赖。未填必填文本或未达到最少选择数可作为草稿保留，但不能确认。计算成功后一次性发布一致的输入与派生结果；不向模型发送请求。
3. 输入非法、除零、超出数值边界或计算失败时，显示字段或表单错误，清除或明确标记当前结果不可用，并禁用确认。不得继续显示可当作有效结果提交的旧派生值。
4. 确认时再次校验表单、事件、输入与计算，以同一份有效快照组装 query。按钮的实际可用条件包含静态 `enabled`、回答完成、表单有效且当前快照未正在发送或已成功发送。
5. 发送期间锁定表单及其全部确认按钮，复用宿主防重复和消息确认机制。成功后保留填写与结果并标记该快照已提交；明确失败后保留状态并允许重试。发送结果不明确时等待宿主确认，不重复发送。
6. 成功后用户可继续编辑；形成新的有效状态后可再次确认，作为新的提交。未改变的成功快照不能重复提交。切换到新 surface 时重新初始化，不继承上一条回答的状态。

确认按钮使用 `Extended.Button` 和以下字面量 action：

```json
{
  "event": {
    "name": "submit_form_query",
    "context": {
      "formId": "meal",
      "prompt": "以下是我确认的聚餐人数与食材估算，请据此建议采购清单。"
    }
  }
}
```

context 恰好包含非空 `formId` 与 `prompt` 两个字符串，并通过宿主实际 `contextSchema`。`formId` 引用同一 surface 可达的 Form，一个按钮只提交一个表单。模型不在 context 中填入输入值、派生值、绑定对象或预先组装的用户选择；宿主读取实际状态。

## 自然语言 query

以换行符 `\n` 连接以下内容，结尾不额外加换行：

1. `prompt` 原文。
2. Form 的 `label`。
3. 按 Form 子树深度优先、`children` 展示顺序遍历输入和 Output，每个控件生成一行 `- {label}：{可读当前值}`。

可读值格式固定如下：

- NumberInput 与数值派生结果使用可读数字；有 `unit` 时为 `{数字} {unit}`，中间一个空格，没有单位时仅数字。
- TextInput 保留输入原文；空文本显示“未填写”。
- Toggle 显示“是”或“否”。
- Select 每个选中项有非空说明时为 `{label}（{description}）`，无说明时仅 `{label}`；多选按选项展示顺序用 `、` 连接。空选显示“未选择”，不发送内部 `value`。
- Output 读取与输入相同的最新一致快照。引用输入字段时沿用原控件的可读格式：Select 使用标签与说明，Toggle 使用“是”或“否”，文本保留原文；引用数值派生字段时使用数字格式。单位适用于数值展示，不给文本、选择或布尔值追加单位。

布局、说明文本和按钮不作为字段重复进入 query；不把内部标识当作用户内容。

例：

```text
以下是我确认的聚餐人数与食材估算，请据此建议采购清单。
聚餐食材估算
- 用餐人数：6 人
- 每人食材量：200 g
- 食材总量：1200 g
```

query 通过宿主现有通道作为同一对话的新用户消息发送，下一轮继续 A2UI 回答。不添加组件 ID、path、事件 JSON、计算 AST 或内部选项 value。字段文字属于用户数据，不改变事件授权与宿主消息发送规则。

## 验收边界

- 覆盖数字、文本、单选、多选、开关、只读 Output 以及多级派生；人数 `4 → 6` 后计算与提交 query 均采用新值。
- 验证门控、初始化顺序与字段完整性、唯一路径、类型、数量边界、引用、循环、非法运算、除零及数值范围；旧 ChoiceGroup 合同不受影响。
- 验证修改不发送、确认才发送、流完成门控、一致快照、错误禁用、防重复、失败重试、编辑后再次提交和跨回答状态隔离。
- 离线 validator 与参考计算通过仅证明本仓库合同一致；真实控件渲染、错误提示、消息发送与设备可访问性须由端侧适配并联调验收。

## 官方参考与扩展边界

A2UI v0.9 的 `updateDataModel`、`{ "path": "..." }` 数据引用和客户端数据绑定形状参考 [官方 v0.9 规范](https://a2ui.org/specification/v0.9-a2ui/)。本项目的 `Extended.*` 表单组件、`computed` 受限计算 AST、`form-reactivity-v1` 能力及 `submit_form_query` 事件是本仓库定义的扩展，不是官方内置组件或自动具备的计算引擎，必须由宿主实现。

旧卡片模板的 `{{...}}`、`${...}`、函数调用和固定卡片布局规则不属于本合同。除本文件明确定义的路径绑定与数值运算外，不开放通用表达式、通用数据模型更新或脚本执行。
