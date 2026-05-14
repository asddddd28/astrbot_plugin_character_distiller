from __future__ import annotations

from pathlib import Path

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, MessageEventResult, filter
from astrbot.api.star import Context, Star, register

from .distiller.pipeline import CharacterDistillerPipeline
from .storage.workspace import DistillerWorkspace


PLUGIN_NAME = "astrbot_plugin_character_distiller"


@register(
    PLUGIN_NAME,
    "asddd",
    "角色动态人格蒸馏器：导入文本、生成证据卡、人格 Prompt、语言指纹和记忆导出。",
    "0.3.0",
)
class CharacterDistillerPlugin(Star):
    def __init__(self, context: Context, config=None):
        super().__init__(context)
        self.context = context
        self.config = config or {}
        self.workspace = DistillerWorkspace(PLUGIN_NAME)
        self.pipeline = CharacterDistillerPipeline(self.workspace)

    async def initialize(self):
        self.workspace.ensure_layout()
        logger.info("Character Distiller initialized at %s", self.workspace.root)

    @filter.command_group("distill")
    def distill(self):
        """角色人格蒸馏器"""

    @distill.command("help")
    async def help(self, event: AstrMessageEvent):
        event.set_result(MessageEventResult().message(self._help_text()))

    @distill.command("status")
    async def status(self, event: AstrMessageEvent, work_id: str = ""):
        if work_id:
            text = self.pipeline.status(work_id)
        else:
            text = self.pipeline.list_works()
        event.set_result(MessageEventResult().message(text))

    @filter.permission_type(filter.PermissionType.ADMIN)
    @distill.command("import")
    async def import_work(
        self,
        event: AstrMessageEvent,
        title: str = "",
        file_path: str = "",
    ):
        """导入 txt/md：/distill import 作品名 C:\\path\\novel.txt"""
        if not title or not file_path:
            event.set_result(
                MessageEventResult().message(
                    "用法：/distill import <作品名> <txt或md文件路径>\n"
                    "路径包含空格时，请先放到无空格路径，或在 WebUI/文件上传版本中导入。"
                )
            )
            return
        try:
            clean_path = file_path.strip().strip("\"'“”‘’")
            result = self.pipeline.import_text(title=title, source_path=Path(clean_path))
        except Exception as exc:
            logger.error("distill import failed: %s", exc, exc_info=True)
            event.set_result(MessageEventResult().message(f"导入失败：{exc}"))
            return
        event.set_result(MessageEventResult().message(result))

    @filter.permission_type(filter.PermissionType.ADMIN)
    @distill.command("split")
    async def split_work(self, event: AstrMessageEvent, work_id: str = ""):
        """切分章节、段落和粗略场景：/distill split work_001"""
        if not work_id:
            event.set_result(MessageEventResult().message("用法：/distill split <work_id>"))
            return
        try:
            result = self.pipeline.split_work(work_id)
        except Exception as exc:
            logger.error("distill split failed: %s", exc, exc_info=True)
            event.set_result(MessageEventResult().message(f"切分失败：{exc}"))
            return
        event.set_result(MessageEventResult().message(result))

    @filter.permission_type(filter.PermissionType.ADMIN)
    @distill.command("import-result")
    async def import_result(
        self,
        event: AstrMessageEvent,
        work_id: str = "",
        json_path: str = "",
        auto_export: str = "yes",
    ):
        """导入外部蒸馏 JSON：/distill import-result new C:\\path\\yonagi_distilled.json [yes|no]"""
        if not work_id or not json_path:
            event.set_result(
                MessageEventResult().message(
                    "用法：/distill import-result <work_id|new> <json路径> [yes|no]\n"
                    "yes 表示导入后自动生成 Persona/KB/Memorix/Angel 导出包。"
                )
            )
            return
        try:
            clean_path = json_path.strip().strip("\"'“”‘’")
            result = self.pipeline.import_result(
                work_id=work_id,
                json_path=Path(clean_path),
                auto_export=auto_export.lower() not in {"no", "false", "0"},
            )
        except Exception as exc:
            logger.error("distill import-result failed: %s", exc, exc_info=True)
            event.set_result(MessageEventResult().message(f"外部蒸馏结果导入失败：{exc}"))
            return
        event.set_result(MessageEventResult().message(result))

    @filter.permission_type(filter.PermissionType.ADMIN)
    @distill.command("evidence")
    async def evidence(self, event: AstrMessageEvent, action: str = "", character: str = "", work_id: str = ""):
        """生成证据卡：/distill evidence build 角色A work_001"""
        if action != "build" or not character or not work_id:
            event.set_result(
                MessageEventResult().message("用法：/distill evidence build <角色名> <work_id>")
            )
            return
        try:
            llm_generate = await self._llm_generate(event)
            if llm_generate:
                result = await self.pipeline.build_evidence_ai(
                    work_id=work_id,
                    character=character,
                    llm_generate=llm_generate,
                    max_evidence=self._max_evidence(),
                    detail_level=self._detail_level(),
                )
            else:
                result = self.pipeline.build_evidence(work_id=work_id, character=character)
        except Exception as exc:
            logger.error("distill evidence failed: %s", exc, exc_info=True)
            event.set_result(MessageEventResult().message(f"证据卡生成失败：{exc}"))
            return
        event.set_result(MessageEventResult().message(result))

    @filter.permission_type(filter.PermissionType.ADMIN)
    @distill.command("persona")
    async def persona(self, event: AstrMessageEvent, action: str = "", character: str = "", work_id: str = "", phase: str = "auto"):
        """生成人格卡：/distill persona build 角色A work_001 [phase]"""
        if action != "build" or not character or not work_id:
            event.set_result(
                MessageEventResult().message("用法：/distill persona build <角色名> <work_id> [phase|auto]")
            )
            return
        try:
            llm_generate = await self._llm_generate(event)
            if llm_generate:
                result = await self.pipeline.build_persona_ai(
                    work_id=work_id,
                    character=character,
                    phase=phase,
                    llm_generate=llm_generate,
                    max_evidence=self._max_evidence(),
                    detail_level=self._detail_level(),
                )
            else:
                result = self.pipeline.build_persona(work_id=work_id, character=character, phase=phase)
        except Exception as exc:
            logger.error("distill persona failed: %s", exc, exc_info=True)
            event.set_result(MessageEventResult().message(f"人格卡生成失败：{exc}"))
            return
        event.set_result(MessageEventResult().message(result))

    @filter.permission_type(filter.PermissionType.ADMIN)
    @distill.command("style")
    async def style(self, event: AstrMessageEvent, action: str = "", character: str = "", work_id: str = ""):
        """生成语言指纹：/distill style build 角色A work_001"""
        if action != "build" or not character or not work_id:
            event.set_result(
                MessageEventResult().message("用法：/distill style build <角色名> <work_id>")
            )
            return
        try:
            llm_generate = await self._llm_generate(event)
            if llm_generate:
                result = await self.pipeline.build_style_ai(
                    work_id=work_id,
                    character=character,
                    llm_generate=llm_generate,
                    max_evidence=self._max_evidence(),
                    detail_level=self._detail_level(),
                )
            else:
                result = self.pipeline.build_style(work_id=work_id, character=character)
        except Exception as exc:
            logger.error("distill style failed: %s", exc, exc_info=True)
            event.set_result(MessageEventResult().message(f"语言指纹生成失败：{exc}"))
            return
        event.set_result(MessageEventResult().message(result))

    @filter.permission_type(filter.PermissionType.ADMIN)
    @distill.command("export")
    async def export(self, event: AstrMessageEvent, target: str = "", character: str = "", work_id: str = "", phase: str = "auto"):
        """导出：/distill export persona|memorix|angel|kb|all 角色A work_001 [phase]"""
        if target not in {"persona", "memorix", "angel", "kb", "all"} or not character or not work_id:
            event.set_result(
                MessageEventResult().message(
                    "用法：/distill export <persona|memorix|angel|kb|all> <角色名> <work_id> [phase|auto]"
                )
            )
            return
        try:
            result = self.pipeline.export(work_id=work_id, character=character, target=target, phase=phase)
        except Exception as exc:
            logger.error("distill export failed: %s", exc, exc_info=True)
            event.set_result(MessageEventResult().message(f"导出失败：{exc}"))
            return
        event.set_result(MessageEventResult().message(result))

    @filter.permission_type(filter.PermissionType.ADMIN)
    @distill.command("export-package")
    async def export_package(self, event: AstrMessageEvent, character: str = "", work_id: str = ""):
        """导出完整包：/distill export-package 角色A work_001"""
        if not character or not work_id:
            event.set_result(MessageEventResult().message("用法：/distill export-package <角色名> <work_id>"))
            return
        try:
            result = self.pipeline.export_package(work_id=work_id, character=character)
        except Exception as exc:
            logger.error("distill export-package failed: %s", exc, exc_info=True)
            event.set_result(MessageEventResult().message(f"完整导出包生成失败：{exc}"))
            return
        event.set_result(MessageEventResult().message(result))

    @filter.permission_type(filter.PermissionType.ADMIN)
    @distill.command("run")
    async def run_all(self, event: AstrMessageEvent, character: str = "", work_id: str = "", phase: str = "auto"):
        """跑通 MVP 流程：/distill run 角色A work_001 [phase]"""
        if not character or not work_id:
            event.set_result(MessageEventResult().message("用法：/distill run <角色名> <work_id> [phase|auto]"))
            return
        try:
            llm_generate = await self._llm_generate(event)
            if llm_generate:
                result = await self.pipeline.run_ai(
                    work_id=work_id,
                    character=character,
                    phase=phase,
                    llm_generate=llm_generate,
                    max_evidence=self._max_evidence(),
                    detail_level=self._detail_level(),
                )
            else:
                result = "未找到可用 LLM Provider，已使用规则模式。\n\n" + self.pipeline.run_mvp(
                    work_id=work_id,
                    character=character,
                    phase=phase,
                )
        except Exception as exc:
            logger.error("distill run failed: %s", exc, exc_info=True)
            event.set_result(MessageEventResult().message(f"流程执行失败：{exc}"))
            return
        event.set_result(MessageEventResult().message(result))

    async def terminate(self):
        logger.info("Character Distiller terminated")

    def _max_evidence(self) -> int:
        distillation = self.config.get("distillation", {})
        override = int(distillation.get("ai_max_evidence", 0) or 0)
        if override > 0:
            return override
        return {
            "1_quick": 12,
            "2_light": 24,
            "3_balanced": 48,
            "4_deep": 80,
            "5_canonical": 120,
            "6_exhaustive": 180,
        }.get(self._detail_level(), 48)

    def _detail_level(self) -> str:
        distillation = self.config.get("distillation", {})
        return str(distillation.get("detail_level", "3_balanced"))

    async def _llm_generate(self, event: AstrMessageEvent):
        if not self.config.get("provider", {}).get("enable_ai_distillation", True):
            return None
        provider_id = self.config.get("provider", {}).get("distill_provider_id", "")
        if not provider_id:
            try:
                provider_id = await self.context.get_current_chat_provider_id(event.unified_msg_origin)
            except Exception:
                provider_id = ""
        if not provider_id:
            return None

        async def generate(system_prompt: str, prompt: str) -> str:
            response = await self.context.llm_generate(
                chat_provider_id=provider_id,
                system_prompt=system_prompt,
                prompt=prompt,
                temperature=0.2,
            )
            return response.completion_text

        return generate

    def _help_text(self) -> str:
        return (
            "角色人格蒸馏器命令：\n"
            "/distill import <作品名> <txt或md文件路径>\n"
            "/distill split <work_id>\n"
            "/distill import-result <work_id|new> <json路径> [yes|no]  # 导入外部蒸馏 JSON 并可自动导出\n"
            "/distill evidence build <角色名> <work_id>  # 有 Provider 时使用 AI 提取\n"
            "/distill persona build <角色名> <work_id> [phase|auto]  # 有 Provider 时使用 AI 蒸馏\n"
            "/distill style build <角色名> <work_id>  # 有 Provider 时使用 AI 分析语言指纹\n"
            "/distill export <persona|memorix|angel|kb|all> <角色名> <work_id> [phase|auto]\n"
            "/distill export-package <角色名> <work_id>  # 导出所有阶段 Persona/KB/Memorix/Angel\n"
            "/distill run <角色名> <work_id> [phase|auto]  # AI 证据+人格+语言指纹+导出\n"
            "/distill status [work_id]\n\n"
            f"数据目录：{self.workspace.root}"
        )
