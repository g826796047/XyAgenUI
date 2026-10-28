# GdXyAentUI

GdXyAentUI 是独立的中文 A2UI Skill 与高德 AGenUI 参考工作区。它把用户 query 的每个回答都包装为 A2UI v0.9 JSONL，并使用高德 AGenUI catalog 的组件、数据绑定和 FunctionCall 语义。

本目录可整体复制后单独使用，无需父目录或 CreateMyCard。需要 Node.js 20 或以上；运行校验器和工作台无需安装 npm 依赖。高德原生 SDK 的构建、函数注册和真机联调单独见方案文档。

## 目录

- `SKILL.md`：模型生成规则，放在项目一层目录。
- `references/agenui/agenui_catalog.json`：高德 AGenUI catalog 快照。
- `references/agenui/component-catalog.md`：中文组件选择和字段说明。
- `references/protocol/`：A2UI v0.9 协议快照和来源记录。
- `references/functions.md`、`forms.md`：函数、query 模板、表单和联动合同。
- `docs/方案设计.md`：Skill 方案与端侧/renderer 方案。
- `references/agenui/sdk-integration.md`：固定版本的原生 SDK 接入接口与适配边界。
- `examples/`：可直接粘贴到 AGenUI 参考 renderer 的 JSONL 样例。
- `tools/validate_agenui.mjs`：独立 JSONL 校验器。
- `renderer/`：浏览器参考 renderer，模拟 AGenUI 交互，不替代 HarmonyOS 真机验收。

## 校验

```powershell
node tools/validate_agenui.mjs examples/short-answer.jsonl
node --test renderer/tests/*.test.mjs tests/*.test.mjs
```

## 浏览器参考 renderer

```powershell
node tools/serve_renderer.mjs
```

默认打开 <http://127.0.0.1:8766>，可以选择样例、粘贴 JSONL、流式播放，并在确认按钮后查看本地模拟的 query 或链接 FunctionCall。若端口已被占用，可在 PowerShell 中执行 `$env:GDXY_PORT='8767'` 后重新运行服务。

## HarmonyOS 接入边界

真实端侧需要使用高德 AGenUI 的 `SurfaceManager`/`Surface` 与 `AGenUIContainer`，加载相同 catalog，注册 `sendMsgToXiaoyi` 等宿主函数，并开启 `Button.action` 的深层动态值解析。浏览器工作台只证明协议和交互合同可预览。

当前参考工作台用原生 HTML 控件和安全函数模拟器预览合同，不是高德官方 Web SDK。`Lottie`/`Web` 显示占位提示，`RichText` 降级为纯文本，Markdown/图表仅提供预览子集；官方 25 种组件的 schema 支持与原生端实际支持分别记录在方案文档中。
