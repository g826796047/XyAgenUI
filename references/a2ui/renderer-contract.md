# 浏览器参考 Renderer 合同

`renderer/` 面向 A2UIRender Extended catalog 的浏览器参考实现，固定使用 A2UI `v0.9` 与 `ohos.a2ui.extended.catalog`。它逐行解析 JSONL，处理 `createSurface`、多组件 `updateComponents`、局部 JSON Pointer `updateDataModel` 和 `deleteSurface`，并以 DOM `textContent` 渲染模型文本。

参考实现覆盖 catalog 中的布局、展示、输入、选择、Tabs、条件分支和 Web 组件名称，并实现常用字段、样式与数据绑定。输入回写数据模型，Radio/Checkbox/Select/Toggle 状态按 surface 隔离；流结束且 validator 通过后才能操作。表达式使用受限解析器，不执行任意代码；FunctionCall 只执行项目函数合同中的安全模拟，不执行任意插件或网络代码，Web 使用受控占位展示。

按钮的 FunctionCall 必须通过 validator 的 `a2ui.allowedFunctions` 和函数合同检查。工作台 `/api/submit` 根据实际数据模型和控件状态执行安全函数模拟；`sendMsgToXiaoyi` 按 `${name}` 参数模板生成 query，链接函数只展示受控调用参数。`window.xyA2uiHost.onFunctionCall(detail)` 可供宿主接入真实函数注册。参考 renderer 的结果不能替代 A2UIRender `SurfaceController` 的组件 schema、HarmonyOS 布局、辅助功能或设备交互验收。
