# XyAgenUI

XyAgenUI 是一个中文 A2UI 对话 Skill 与离线参考工具。模型的每个回答都使用 A2UI v0.9 JSONL，端侧按流逐条更新 surface；简单回答也由 `Text` 组件承载。目标组件目录是 A2UIRender `develop` 分支提交 `20a32b91edc4ccdb02b248a08e856f95f83f9800` 的 Extended catalog，固定 `catalogId` 为 `ohos.a2ui.extended.catalog`。

## 目录

- `SKILL.md`：模型输出规则和内容组织策略。
- `references/a2ui/official/`：A2UI v0.9、基础 catalog、Extended catalog 和来源快照，唯一协议依据。
- `references/a2ui/profile.md`、`interaction.md`、`forms.md`：对话、交互和安全数据联动合同。
- `references/a2ui/official/extended_catalog.json`：官方 Extended catalog 的 pinned 本地快照，Skill 和 validator 的唯一组件依据。
- `tools/validate_a2ui_chat.py`：离线 JSONL、组件图、动态值、FunctionCall 和运行时函数白名单校验器。
- `renderer/`：可粘贴 A2UI JSONL 并逐行流式渲染的浏览器参考工作台，支持选择、表单联动、模板化 query 组装和函数调用预览。
- `examples/`：中文回答、比较、图片、选择和数据绑定样例。

## 校验

需要 Python 3：

```powershell
python tools/validate_a2ui_chat.py examples/short-answer.jsonl
python -m unittest discover -s tests -v
```

校验器默认加载官方 Extended catalog，拒绝不在当前 catalog 中的组件、`.form` catalog、`action.event`、未知或未授权函数及不安全表达式。官方 schema 快照和 A2UIRender 来源记录见 `references/a2ui/official/README.md`。

## 浏览器渲染器

```powershell
python tools/serve_renderer.py
```

打开 <http://127.0.0.1:8765>，选择样例或粘贴 JSONL，使用流式、单步或即时渲染。校验通过且流结束后可操作选择和表单；确认按钮按当前状态解析 `functionCall` 并显示 query 或链接参数。宿主可通过 `window.xyA2uiHost.onFunctionCall(detail)` 接入端侧函数。浏览器参考渲染不能替代 HarmonyOS `SurfaceController`、扩展函数、资源域名、辅助功能和设备交互验收。
