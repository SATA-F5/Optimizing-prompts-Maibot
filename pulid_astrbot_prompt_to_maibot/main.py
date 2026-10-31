import os
from pathlib import Path
from typing import Dict, List

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star
from astrbot.api.provider import ProviderRequest

PLUGIN_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = PLUGIN_DIR / "prompts"

BLOCK_REGISTRY: Dict[str, str] = {
    "enable_identity": "identity_block.prompt",
    "enable_behavior": "behavior_block.prompt",
    "enable_group_chat": "group_chat_block.prompt",
    "enable_reply_style": "reply_style_block.prompt",
    "enable_context": "context_block.prompt",
    "enable_tool_usage": "tool_usage_block.prompt",
}

BLOCK_LABELS: Dict[str, str] = {
    "enable_identity": "身份认知",
    "enable_behavior": "行为风格",
    "enable_group_chat": "群聊行为",
    "enable_reply_style": "回复风格",
    "enable_context": "上下文理解",
    "enable_tool_usage": "工具使用",
}

INJECTION_MARKER_START = "===== Maibot Prompt Optimization ====="
INJECTION_MARKER_END = "===== End Maibot Prompt Optimization ====="


class MaibotPromptPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig = None) -> None:
        super().__init__(context)
        self.config = config or {}
        self._prompt_cache: Dict[str, str] = {}
        self._load_prompt_blocks()
        self._register_web_apis()
        logger.info("Maibot prompt optimization plugin loaded.")

    def _load_prompt_blocks(self) -> None:
        for config_key, filename in BLOCK_REGISTRY.items():
            prompt_path = PROMPTS_DIR / filename
            try:
                self._prompt_cache[config_key] = prompt_path.read_text(
                    encoding="utf-8"
                ).strip()
            except FileNotFoundError:
                logger.error(f"Prompt block file not found: {prompt_path}")
                self._prompt_cache[config_key] = ""

    def _build_optimization_text(self) -> str:
        sections: List[str] = []
        for config_key in BLOCK_REGISTRY:
            if self.config.get(config_key, True):
                content = self._prompt_cache.get(config_key, "")
                if content:
                    sections.append(content)
        custom = str(self.config.get("custom_suffix", "")).strip()
        if custom:
            sections.append("【自定义规则】\n" + custom)
        if not sections:
            return ""
        body = "\n\n".join(sections)
        return f"{INJECTION_MARKER_START}\n{body}\n{INJECTION_MARKER_END}"

    def _register_web_apis(self) -> None:
        plugin_name = "pulid_astrbot_prompt_to_maibot"
        self.context.register_web_api(
            f"/{plugin_name}/status",
            self._web_status,
            ["GET"],
            "Get prompt block status",
        )
        self.context.register_web_api(
            f"/{plugin_name}/preview",
            self._web_preview,
            ["GET"],
            "Preview assembled optimization prompt",
        )

    async def _web_status(self):
        from astrbot.api.web import json_response

        status = []
        for key, label in BLOCK_LABELS.items():
            status.append(
                {
                    "key": key,
                    "label": label,
                    "enabled": bool(self.config.get(key, True)),
                }
            )
        return json_response(
            {
                "blocks": status,
                "injection_mode": self.config.get(
                    "injection_mode", "system_prompt"
                ),
                "has_custom": bool(
                    str(self.config.get("custom_suffix", "")).strip()
                ),
            }
        )

    async def _web_preview(self):
        from astrbot.api.web import json_response

        return json_response({"content": self._build_optimization_text()})

    @filter.on_llm_request()
    async def inject_maibot_prompt(
        self, event: AstrMessageEvent, req: ProviderRequest
    ) -> None:
        optimization = self._build_optimization_text()
        if not optimization:
            return

        mode = self.config.get("injection_mode", "system_prompt")

        if mode == "extra_user_content":
            try:
                from astrbot.core.agent.message import TextPart

                req.extra_user_content_parts.append(TextPart(text=optimization))
            except ImportError:
                logger.warning(
                    "TextPart not available, falling back to system_prompt."
                )
                self._append_to_system_prompt(req, optimization)
        else:
            self._append_to_system_prompt(req, optimization)

    @staticmethod
    def _append_to_system_prompt(
        req: ProviderRequest, optimization: str
    ) -> None:
        existing = req.system_prompt or ""
        if INJECTION_MARKER_START in existing:
            return
        if existing and not existing.endswith("\n"):
            existing += "\n\n"
        elif existing:
            existing += "\n"
        req.system_prompt = existing + optimization

    @filter.command("maibot_prompt", alias={"mbprompt", "麦麦提示"})
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def cmd_status(self, event: AstrMessageEvent):
        """查看当前提示词模块状态和注入位置。"""
        lines = ["Maibot 提示词优化状态："]
        for key, label in BLOCK_LABELS.items():
            state = "开启" if self.config.get(key, True) else "关闭"
            lines.append(f"  {label}: {state}")
        mode = self.config.get("injection_mode", "system_prompt")
        mode_text = "系统提示词追加" if mode == "system_prompt" else "用户消息追加"
        lines.append(f"注入位置: {mode_text}")
        preview = self._build_optimization_text()
        lines.append(f"当前拼装长度: {len(preview)} 字符")
        yield event.plain_result("\n".join(lines))

    @filter.command("maibot_preview", alias={"mbpreview"})
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def cmd_preview(self, event: AstrMessageEvent):
        """预览当前拼装的完整优化提示词。"""
        content = self._build_optimization_text()
        if not content:
            yield event.plain_result("所有模块均已关闭，无内容可预览。")
            return
        yield event.plain_result(content)

    async def terminate(self) -> None:
        logger.info("Maibot prompt optimization plugin unloaded.")
