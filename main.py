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
    "0.1.0",
)
class CharacterDistillerPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.context = context
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
            result = self.pipeline.import_text(title=title, source_path=Path(file_path))
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
    @distill.command("evidence")
    async def evidence(self, event: AstrMessageEvent, action: str = "", character: str = "", work_id: str = ""):
        """生成证据卡：/distill evidence build 角色A work_001"""
        if action != "build" or not character or not work_id:
            event.set_result(
                MessageEventResult().message("用法：/distill evidence build <角色名> <work_id>")
            )
            return
        try:
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
    @distill.command("run")
    async def run_all(self, event: AstrMessageEvent, character: str = "", work_id: str = "", phase: str = "auto"):
        """跑通 MVP 流程：/distill run 角色A work_001 [phase]"""
        if not character or not work_id:
            event.set_result(MessageEventResult().message("用法：/distill run <角色名> <work_id> [phase|auto]"))
            return
        try:
            result = self.pipeline.run_mvp(work_id=work_id, character=character, phase=phase)
        except Exception as exc:
            logger.error("distill run failed: %s", exc, exc_info=True)
            event.set_result(MessageEventResult().message(f"流程执行失败：{exc}"))
            return
        event.set_result(MessageEventResult().message(result))

    async def terminate(self):
        logger.info("Character Distiller terminated")

    def _help_text(self) -> str:
        return (
            "角色人格蒸馏器 MVP 命令：\n"
            "/distill import <作品名> <txt或md文件路径>\n"
            "/distill split <work_id>\n"
            "/distill evidence build <角色名> <work_id>\n"
            "/distill persona build <角色名> <work_id> [phase|auto]\n"
            "/distill style build <角色名> <work_id>\n"
            "/distill export <persona|memorix|angel|kb|all> <角色名> <work_id> [phase|auto]\n"
            "/distill run <角色名> <work_id> [phase|auto]\n"
            "/distill status [work_id]\n\n"
            f"数据目录：{self.workspace.root}"
        )
