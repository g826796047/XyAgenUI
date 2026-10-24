# A2UIRender 浏览器参考工作台

启动本地服务：

```powershell
python tools/serve_renderer.py
```

打开 <http://127.0.0.1:8765>，可粘贴 A2UI v0.9 JSONL、逐条流式渲染，或加载仓库样例。默认 profile 固定使用 `ohos.a2ui.extended.catalog`。

工作台解析标准 JSONL 消息、组件增量、局部 `updateDataModel` 和 `deleteSurface`，并提供布局、文本、图片、进度、Tabs、选择、输入、开关和按钮的浏览器参考展示。控件仅在流完整且 validator 校验通过后启用。输入、选择和表单联动在本地更新；点击有效按钮后，工作台按真实表单/选择快照生成下一轮 query 并展示在“交互结果”区域。宿主可设置 `window.xyA2uiHost.onEvent(detail)` 接收确认结果并接入实际对话发送。

表达式使用本项目限制的安全子集和专用 parser，不执行 `eval` 或任意 JavaScript；遇到运行时无效表达式时会禁用交互。Web 资源不内嵌加载，图片和外部资源按 `allowedResourceDomains` 策略处理。浏览器工作台是参考实现，不能替代 A2UIRender `SurfaceController` 在 HarmonyOS 上的校验。

## 分块接入

```javascript
const preview = window.xyA2uiPreview;
preview.start(runtimeContext);
preview.push(jsonlChunk);
await preview.finish();
```

`runtimeContext` 应由宿主提供 `a2ui.capabilities`、资源策略和 `allowedUiEvents`。`getState()` 可读取流完成状态、消息数和 surface ID。交互事件回调只在用户确认后触发；工作台本身不会调用模型服务。
