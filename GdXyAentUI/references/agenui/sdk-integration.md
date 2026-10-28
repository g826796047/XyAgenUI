# 高德 AGenUI 原生端接入

本文件记录固定快照 `5c347a8352c1afff31879bcf5af4101df4f94137`（v1.7.0）的接入接口。AGenUI 提供 HarmonyOS、Android、iOS 原生 SDK；本仓库的网页工作台是参考预览器。组件和宿主函数校验通过，不等于 SDK 构建或设备验收通过。

## HarmonyOS 流式生命周期

使用 `@agenui/agenui` 的 `SurfaceManager`、`ISurfaceManagerListener`、`Surface` 和 `AGenUIContainer`：

1. 创建 `new SurfaceManager(context)`，注册创建、删除、错误监听。
2. 创建 surface 回调保存 `surface.surfaceId`，用 `AGenUIContainer({surfaceId})` 挂载页面。
3. 每轮调用 `beginTextStream()`，逐片调用 `receiveTextChunk(chunk)`，最后调用 `endTextStream()`。不要把 JSONL 包成单引号字符串数组或把任意传输分片当作完整 JSON。
4. 会话结束或页面销毁时按 SDK 生命周期释放 `SurfaceManager`，不同回复独立管理 surface 与控件状态。

这是高德 SDK 的接口，不能照搬旧鸿蒙 A2UIRender 的 `CatalogFactory.extended()`、`SurfaceController`、`addClientFunction`。

## 函数适配

HarmonyOS 通过 `AGenUI.registerFunction(func: IFunctionCall)` 注册函数；实现接口：

```typescript
execute(context: FunctionCallContext, paramsJson: string): FunctionResult
getConfig(): FunctionConfig
```

`paramsJson` 是 JSON 字符串，需要解析后校验。`getConfig()` 返回函数名，执行成功用 `FunctionResult.createSuccess(...)`，失败用 `FunctionResult.createError(...)`。本项目的 `sendMsgToXiaoyi`、三个链接函数、`calculateNumber` 需要分别适配该接口。旧 renderer 中 `context.resolver.evaluateValue` 不应原样复制到高德接口。

AGenUI v1.7.0 支持对 action 注册深层解析，以及 `resolveCalls` 递归解析函数。宿主必须确认本次 action 参数中的 `{path}` 和嵌套函数是在点击时以最新状态解析，而不是提前固化值。`resolveCalls` 未包含在此固定 catalog 的 functions 列表中，因此 Skill 不生成它；它属于宿主接入机制。

函数 schema 以项目 `gdxy_catalog.json` 为校验 overlay，组件定义保持官方不变。上线前要确保客户端实际注册的 catalog/函数与下发的能力上下文一致，不能只改 `catalogId` 就认为注册完成。

## 状态、query 和计算

- `ChoicePicker` 两种模式均绑定字符串数组，未选择为 `[]`；单选最多一项。
- `TextField` 包括数字键盘都绑定字符串；`CheckBox` 绑定布尔值；`Slider` 绑定数字；`DateTimeInput` 绑定 ISO 字符串。
- 本地状态改变不触发模型。确认时执行白名单 `sendMsgToXiaoyi`，解析当前值，按 `${name}` 规则组装 query，再交给同一会话的消息发送层。
- `sendMsgToXiaoyi` 的历史合同接收字符串/字符串数组。数值先用 `formatNumber` 等转换，布尔值用 `formatString` 或宿主明确提供的转换函数。
- 宿主必须在确认前执行 checks、拒绝空参数/非法数据、锁定流未结束与提交中的控件，失败允许重试，成功避免重复发送。
- `calculateNumber` 是可选宿主函数；实现有限运算、数值检查、除零和溢出处理，并保证绑定刷新。未注册时由业务层计算后更新数据模型。
- 图片需要注册 SDK 图片加载器；Web、媒体、AppLink、DeepLink 的网络、资源与权限策略由应用负责。

## 固定版本来源

- 仓库：`https://github.com/AGenUI/AGenUI`
- 接入指南：`https://github.com/AGenUI/AGenUI/blob/5c347a8352c1afff31879bcf5af4101df4f94137/docs/QuickStart.md`
- API：`https://github.com/AGenUI/AGenUI/blob/5c347a8352c1afff31879bcf5af4101df4f94137/docs/API.md`
- 组件定义：本目录的 `agenui_catalog.json`（与固定 commit 的根目录 catalog 结构一致）。

验收应使用本仓库同一份 JSONL，覆盖单选、多选、输入、动态计算、action 参数实时解析、错误重试、多 surface 隔离与真实资源加载。设备或模拟器验收由端侧项目执行。
