# AGenUI 协议依据

GdXyAentUI 只维护生成 Skill 所需要的协议合同，运行时由高德 AGenUI 三端 SDK 渲染。线协议是 Google A2UI `v0.9`；组件目录是 AGenUI 的独立 catalog。

## 本地快照

- `server_to_client.json`：A2UI v0.9 服务端到客户端消息结构。
- `common_types.json`：A2UI v0.9 公共类型。
- `../agenui/agenui_catalog.json`：高德 AGenUI 官方组件和函数目录，包含 18 个协议组件、4 个 SDK 扩展组件和 3 个 Playground/宿主注册组件。
- `../agenui/gdxy_catalog.json`：GdXyAentUI 项目 overlay；原样保留官方组件定义，只增加 `sendMsgToXiaoyi`、链接函数和可选的 `calculateNumber` 合同。

来源：`https://github.com/AGenUI/AGenUI`，`main` 分支，提交 `5c347a8352c1afff31879bcf5af4101df4f94137`（2026-10-19）。组件网页为 `https://genui.amap.com/components`。

## 固定 profile

```json
{
  "version": "v0.9",
  "createSurface": {
    "surfaceId": "answer-001",
    "catalogId": "urn:a2ui:catalog:agenui_catalog"
  }
}
```

支持的消息类型仍是 `createSurface`、`updateComponents`、`updateDataModel` 和 `deleteSurface`。组件更新可以包含一个或多个组件；流式发送只是传输方式，不改变消息结构。`children`、`Card.child`、`Tabs.tabs[].child`、`Modal.trigger/content` 都引用已定义或将要定义的组件 ID。

## 与旧项目的边界

本目录不接受 `ohos.a2ui.extended.catalog`、`ohos.a2ui.extended.catalog.form`、`Extended.*`、`Text.content`、`Image.src`、`TextInput`、`CheckboxGroup`、`getCheckboxGroupValues` 或卡片专用 tuple。高德目录的对应字段分别是 `Text.text`、`Image.url`、`TextField`、`ChoicePicker`/`CheckBox` 以及数据绑定值。

Skill 和 validator 默认读取 `gdxy_catalog.json`，并要求运行时声明允许使用的宿主函数。`action.event` 是 A2UI/AGenUI schema 允许的形状，但 GdXyAentUI Skill 有意只生成宿主已注册的 `action.functionCall`，以便在端侧明确控制函数权限。
