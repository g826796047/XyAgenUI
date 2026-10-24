# XyAgenUI

XyAgenUI 是一个中文 A2UI 对话 Skill 与离线参考工具。模型的每个回答都使用 A2UI v0.9 JSONL，端侧按流逐条更新 surface；简单回答也由 `Text` 组件承载。目标组件目录是 A2UIRender `develop` 分支提交 `20a32b91edc4ccdb02b248a08e856f95f83f9800` 的 Extended catalog，固定 `catalogId` 为 `ohos.a2ui.extended.catalog`。

## 目录

- `SKILL.md`：模型输出规则和内容组织策略。
- `references/a2ui/official/`：A2UI v0.9、基础 catalog、Extended catalog 和来源快照，唯一协议依据。
- `references/a2ui/profile.md`、`interaction.md`、`forms.md`：对话、交互和安全数据联动合同。
- `references/a2ui/legacy/`：旧 `.form`/`Extended.*` 合同的历史材料，仅用于迁移对照。
- `catalogs/xy-a2ui-chat-basic/v1/catalog.json`：官方 Extended catalog 的本地副本。
- `tools/validate_a2ui_chat.py`：离线 JSONL、组件图、动态值和白名单事件校验器。
- `renderer/`：可粘贴 A2UI JSONL 并逐行流式渲染的浏览器参考工作台，支持选择、表单联动和 query 预览。
- `examples/`：中文回答、比较、图片、选择和数据绑定样例。

## 校验

需要 Python 3：

```powershell
python tools/validate_a2ui_chat.py examples/short-answer.jsonl
python -m unittest discover -s tests -v
```

校验器默认加载官方 Extended catalog，拒绝旧 `Extended.*` 组件、`.form` catalog、`functionCall` 和不安全表达式。官方 schema 快照和 A2UIRender 来源记录见 `references/a2ui/official/README.md`。

## 浏览器渲染器

```powershell
python tools/serve_renderer.py
```

打开 <http://127.0.0.1:8765>，选择样例或粘贴 JSONL，使用流式、单步或即时渲染。校验通过且流结束后可操作选择和表单；确认按钮会根据当前状态生成本地 query 预览。宿主可通过 `window.xyA2uiHost.onEvent(detail)` 接入实际对话发送。浏览器参考渲染不能替代 HarmonyOS `SurfaceController`、扩展函数、资源域名、辅助功能和设备交互验收。
