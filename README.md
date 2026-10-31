# 麦botの优化提示词

在不修改 AstrBot 原有系统提示词的前提下，以追加方式注入 MaiBot 风格的拟人化优化规则。

## 工作原理

插件通过 `on_llm_request` 钩子拦截 LLM 请求，将启用的提示词模块拼装后追加到请求中，不会替换或删除任何已有内容。追加内容带有明确的起止标记，避免与原始提示词混淆。

## 提示词模块

| 模块 | 说明 |
|------|------|
| 身份认知 | 角色一致性、自我认知和真实感 |
| 行为风格 | 自然互动、发言时机、错误处理 |
| 群聊行为 | 群聊发言策略、刷屏规避、私聊适配 |
| 回复风格 | 口语化表达、格式净化、观点独立性 |
| 上下文理解 | 历史关系推断、歧义处理、对话连贯性 |
| 工具使用 | 工具调用策略、并行调用、错误恢复 |

各模块可在插件配置中独立开关，也支持追加自定义规则文本。

## 注入位置

- **系统提示词追加**：将规则追加到 `system_prompt`，适合稳定、长期生效的设定。
- **用户消息追加**：将规则通过 `extra_user_content_parts` 放在本轮用户输入之后，不影响系统提示词缓存。

## 指令

| 指令 | 别名 | 说明 |
|------|------|------|
| `/maibot_prompt` | `/mbprompt`、`/麦麦提示` | 查看模块状态和注入位置 |
| `/maibot_preview` | `/mbpreview` | 预览当前拼装的完整提示词 |

指令仅管理员可用。

## 管理页面

插件内置一个简洁的 WebUI 页面，可查看模块状态、运行信息和提示词预览。模块开关在插件配置页修改。

## 文件结构

代码文件直接位于仓库根目录：

```
.
├── main.py
├── metadata.yaml
├── logo.png
├── _conf_schema.json
├── prompts/
│   ├── identity_block.prompt
│   ├── behavior_block.prompt
│   ├── group_chat_block.prompt
│   ├── reply_style_block.prompt
│   ├── context_block.prompt
│   └── tool_usage_block.prompt
└── views/
    └── prompt-manager/
        └── index.html
```
