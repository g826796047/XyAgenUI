# A2UIRender 官方协议快照

本目录是 XyAgenUI 的唯一协议依据，快照来自 [GenerativeUI/A2UIRender](https://gitcode.com/GenerativeUI/A2UIRender) `develop` 分支，提交 `20a32b91edc4ccdb02b248a08e856f95f83f9800`。

- `server_to_client.json`：A2UI v0.9 消息 envelope，包含 `createSurface`、`updateComponents`、`updateDataModel` 和 `deleteSurface`。
- `common_types.json`：A2UI v0.9 公共类型。
- `basic_catalog.json`、`basic_rules.txt`：基础 catalog 参考。
- `extended_catalog.json`：A2UIRender Extended catalog，固定 `catalogId` 为 `ohos.a2ui.extended.catalog`。
- `consumer-rules.txt`：A2UIRender 消费端约束。

快照目录中 `consumer-rules.txt` 在该提交为空文件；Extended catalog 自身的表达式限制、动态值和函数合同以 `extended_catalog.json` 为准。

组件字段、动态值和函数合同以 `extended_catalog.json` 为准；Skill、validator 和样例只使用当前 Extended catalog。
