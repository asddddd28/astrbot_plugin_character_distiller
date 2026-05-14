from __future__ import annotations

from pathlib import Path

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, MessageEventResult, filter
from astrbot.api.star import Context, Star, register

from .distiller.pipeline import CharacterDistillerPipeline
from .distiller.utils import safe_filename
from .storage.workspace import DistillerWorkspace


PLUGIN_NAME = "astrbot_plugin_character_distiller"


@register(
    PLUGIN_NAME,
    "asddd",
    "角色动态人格蒸馏器：导入文本、生成证据卡、人格 Prompt、语言指纹和记忆导出。",
    "0.4.0",
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
    @distill.command("apply")
    async def apply_to_astrbot(
        self,
        event: AstrMessageEvent,
        target: str = "",
        character: str = "",
        work_id: str = "",
        name: str = "",
        embedding_provider_id: str = "",
    ):
        """写入 AstrBot：/distill apply persona|kb|all 角色A work_001 [名称] [embedding_provider_id]"""
        if target not in {"persona", "kb", "all"} or not character or not work_id:
            event.set_result(
                MessageEventResult().message(
                    "用法：/distill apply <persona|kb|all> <角色名> <work_id> [persona前缀或知识库名] [embedding_provider_id]\n"
                    "示例：/distill apply persona 世凪 work_004 世凪\n"
                    "示例：/distill apply kb 世凪 work_004 世凪原著知识库 openai_embedding\n"
                    "示例：/distill apply all 世凪 work_004 世凪原著知识库 openai_embedding"
                )
            )
            return
        try:
            outputs = []
            if target in {"persona", "all"}:
                prefix = name if target == "persona" and name else character
                outputs.append(await self._apply_personas(character, work_id, prefix))
            if target in {"kb", "all"}:
                kb_name = name or f"{character}原著知识库"
                outputs.append(await self._apply_knowledge_base(character, work_id, kb_name, embedding_provider_id))
        except Exception as exc:
            logger.error("distill apply failed: %s", exc, exc_info=True)
            event.set_result(MessageEventResult().message(f"写入 AstrBot 失败：{exc}"))
            return
        event.set_result(MessageEventResult().message("\n\n".join(outputs)))

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

    async def _apply_personas(self, character: str, work_id: str, persona_prefix: str) -> str:
        base = self.workspace.require_work_dir(work_id)
        char_file = safe_filename(character)
        prompt_paths = sorted((base / "exports").glob(f"astrbot_persona_prompt_{char_file}_*.txt"))
        if not prompt_paths:
            self.pipeline.export_package(work_id, character)
            prompt_paths = sorted((base / "exports").glob(f"astrbot_persona_prompt_{char_file}_*.txt"))
        if not prompt_paths:
            raise RuntimeError("没有找到 Persona Prompt 导出文件，请先执行 /distill export-package")

        skills = self._persona_skills()
        created = []
        skipped = []
        for prompt_path in prompt_paths:
            phase = prompt_path.stem.replace(f"astrbot_persona_prompt_{char_file}_", "", 1)
            persona_id = safe_filename(f"{persona_prefix}_{phase}")
            prompt = prompt_path.read_text(encoding="utf-8")
            try:
                await self.context.persona_manager.create_persona(
                    persona_id=persona_id,
                    system_prompt=prompt,
                    begin_dialogs=None,
                    tools=None,
                    skills=skills,
                    custom_error_message="当前人格设定无法回答时，请保持原著证据边界，不要编造。",
                )
                created.append(persona_id)
            except ValueError:
                skipped.append(persona_id)

        lines = ["AstrBot Persona 写入完成："]
        if created:
            lines.append("新增：" + ", ".join(created))
        if skipped:
            lines.append("已存在，跳过：" + ", ".join(skipped))
        return "\n".join(lines)

    async def _apply_knowledge_base(
        self,
        character: str,
        work_id: str,
        kb_name: str,
        embedding_provider_id: str,
    ) -> str:
        base = self.workspace.require_work_dir(work_id)
        char_file = safe_filename(character)
        kb_chunks_dir = base / "rag_export" / "kb_chunks" / char_file
        knowledge_dir = base / "rag_export" / "knowledge_cards" / char_file
        if not kb_chunks_dir.exists() and not knowledge_dir.exists():
            self.pipeline.export_package(work_id, character)

        chunks = []
        for path in sorted(kb_chunks_dir.glob("*.md")) if kb_chunks_dir.exists() else []:
            chunks.append(path.read_text(encoding="utf-8"))
        for path in sorted(knowledge_dir.glob("*.md")) if knowledge_dir.exists() else []:
            chunks.append(path.read_text(encoding="utf-8"))
        if not chunks:
            raise RuntimeError("没有找到 KB Markdown 导出文件，请先执行 /distill export-package")

        kb_mgr = self.context.kb_manager
        kb_helper = await kb_mgr.get_kb_by_name(kb_name)
        created_kb = False
        if not kb_helper:
            provider_id = embedding_provider_id or self._default_embedding_provider_id()
            if not provider_id:
                raise RuntimeError("创建知识库需要 embedding_provider_id。请在配置 default_embedding_provider_id，或命令末尾传入。")
            kb_helper = await kb_mgr.create_kb(
                kb_name=kb_name,
                description=f"{character} 原著证据和知识卡，由 Character Distiller 导入。",
                emoji="📚",
                embedding_provider_id=provider_id,
                chunk_size=768,
                chunk_overlap=80,
                top_k_dense=50,
                top_k_sparse=50,
                top_m_final=8,
            )
            created_kb = True

        document = await kb_helper.upload_document(
            file_name=f"{character}_{work_id}_distilled.md",
            file_content=None,
            file_type="md",
            pre_chunked_text=chunks,
        )
        return (
            "AstrBot Knowledge Base 写入完成：\n"
            f"知识库：{kb_name}{'（新建）' if created_kb else '（已有）'}\n"
            f"文档：{document.doc_name}\n"
            f"chunks：{len(chunks)}"
        )

    def _persona_skills(self) -> list[str] | None:
        value = self.config.get("application", {}).get(
            "persona_skills",
            "evidence-reviewer,persona-distiller,style-fingerprint,knowledge-distiller",
        )
        if not value:
            return None
        return [item.strip() for item in str(value).split(",") if item.strip()]

    def _default_embedding_provider_id(self) -> str:
        return str(self.config.get("application", {}).get("default_embedding_provider_id", ""))

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
            "/distill apply <persona|kb|all> <角色名> <work_id> [名称] [embedding_provider_id]  # 写入 AstrBot Persona/KB\n"
            "/distill run <角色名> <work_id> [phase|auto]  # AI 证据+人格+语言指纹+导出\n"
            "/distill status [work_id]\n\n"
            f"数据目录：{self.workspace.root}"
        )
