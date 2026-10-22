# A2UI 协议参考

本目录集中维护 XyAgenUI 对话回答所需的协议和端侧行为参考。只保留本项目实际使用的 A2UI v0.9 消息结构、组件图更新、renderer 行为、白名单事件与选择提交规则。

## 阅读顺序

1. [对话 Skill](../../SKILL.md)：模型回答的生成规则。
2. [对话协议 Profile](profile.md)：JSONL 消息、流式组件图、事件和宿主上下文的权威合同。
3. [选择交互合同](interaction.md)：能力声明、单选/多选、确认提交和自然语言 query 组装。
4. [Chat v1.1 组件目录](../../catalogs/xy-a2ui-chat-basic/v1/catalog.json)：允许的组件、属性及数据类型。
5. [Extended Renderer 合同](renderer-contract.md)：组件映射、已有客户端行为和新增选择组件要求，用于端侧集成核对。

生成时以 Skill、Profile、选择交互合同和组件目录为准。Renderer 合同用于解释运行行为，不扩展组件目录或生成规则。目录声明不会自动注册端侧组件；只有宿主同时提供选择能力和对应事件时，模型才可输出选择交互。
