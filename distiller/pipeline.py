from __future__ import annotations

from pathlib import Path

from .extractors import EvidenceExtractor, PersonaExtractor, SpeechExtractor
from .ai_distiller import AIDistiller, LLMGenerate
from .importer import TextImporter
from .splitter import TextSplitter
from .utils import safe_filename
from ..rag.exporters import RagExporter
from ..runtime.persona_writer import PersonaWriter
from ..storage.workspace import DistillerWorkspace


class CharacterDistillerPipeline:
    def __init__(self, workspace: DistillerWorkspace):
        self.workspace = workspace
        self.importer = TextImporter(workspace)
        self.splitter = TextSplitter()
        self.evidence_extractor = EvidenceExtractor()
        self.persona_extractor = PersonaExtractor()
        self.speech_extractor = SpeechExtractor()
        self.persona_writer = PersonaWriter()
        self.rag_exporter = RagExporter()

    def import_text(self, title: str, source_path: Path) -> str:
        meta = self.importer.import_text(title, source_path)
        return (
            f"导入完成：{meta['title']}\n"
            f"work_id：{meta['work_id']}\n"
            f"hash：{meta['source_hash']}\n"
            "下一步：/distill split {work_id}".format(work_id=meta["work_id"])
        )

    def split_work(self, work_id: str) -> str:
        base = self.workspace.require_work_dir(work_id)
        meta = self.workspace.read_json(base / "raw" / "source_meta.json", {})
        text = (base / "raw" / "normalized.txt").read_text(encoding="utf-8")
        result = self.splitter.split(work_id, meta.get("title", work_id), text)
        self.workspace.write_jsonl(base / "index" / "chapters.jsonl", result["chapters"])
        self.workspace.write_jsonl(base / "index" / "paragraphs.jsonl", result["paragraphs"])
        self.workspace.write_jsonl(base / "index" / "scenes.jsonl", result["scenes"])
        self.workspace.write_jsonl(base / "index" / "utterances.jsonl", result["utterances"])
        return (
            f"切分完成：{work_id}\n"
            f"章节：{len(result['chapters'])}\n"
            f"段落：{len(result['paragraphs'])}\n"
            f"粗略场景：{len(result['scenes'])}\n"
            f"台词候选：{len(result['utterances'])}"
        )

    def build_evidence(self, work_id: str, character: str) -> str:
        base = self.workspace.require_work_dir(work_id)
        paragraphs = self.workspace.read_jsonl(base / "index" / "paragraphs.jsonl")
        if not paragraphs:
            raise RuntimeError("尚未切分文本，请先执行 /distill split")
        cards = self.evidence_extractor.build(work_id, character, paragraphs)
        if not cards:
            raise RuntimeError(
                f"未在 {work_id} 中找到角色名「{character}」的证据段落；"
                "请确认角色名写法，或重新导入原文后再 split。"
            )
        char_file = safe_filename(character)
        out = base / "distilled" / f"evidence_cards_{char_file}.jsonl"
        self.workspace.write_jsonl(out, cards)
        return f"证据卡生成完成：{len(cards)} 张\n输出：{out}"

    def build_persona(self, work_id: str, character: str, phase: str = "auto") -> str:
        persona = self._build_persona_obj(work_id, character, phase)
        base = self.workspace.require_work_dir(work_id)
        char_file = safe_filename(character)
        phase_file = safe_filename(persona["phase"])
        out = base / "distilled" / f"persona_card_{char_file}_{phase_file}.json"
        self.workspace.write_json(out, persona)
        return (
            f"人格卡生成完成：{character} / {persona['phase']}\n"
            f"证据数：{len(persona.get('evidence_ids', []))}\n"
            f"置信度：{persona.get('confidence')}\n"
            f"输出：{out}"
        )

    def build_style(self, work_id: str, character: str) -> str:
        speech = self._build_style_obj(work_id, character)
        base = self.workspace.require_work_dir(work_id)
        char_file = safe_filename(character)
        out = base / "distilled" / f"speech_fingerprint_{char_file}.json"
        self.workspace.write_json(out, speech)
        return (
            f"语言指纹生成完成：{character}\n"
            f"台词样本：{speech.get('sample_count', 0)}\n"
            f"输出：{out}"
        )

    def export(self, work_id: str, character: str, target: str, phase: str = "auto") -> str:
        base = self.workspace.require_work_dir(work_id)
        persona = self._load_or_build_persona(work_id, character, phase)
        speech = self._load_or_build_style(work_id, character)
        outputs = []

        if target in {"persona", "all"}:
            prompt = self.persona_writer.build_prompt(persona, speech)
            char_file = safe_filename(character)
            phase_file = safe_filename(persona["phase"])
            out = base / "exports" / f"astrbot_persona_prompt_{char_file}_{phase_file}.txt"
            out.write_text(prompt, encoding="utf-8")
            outputs.append(out)

        if target in {"memorix", "all"}:
            rows = self.rag_exporter.memorix_rows(persona)
            char_file = safe_filename(character)
            phase_file = safe_filename(persona["phase"])
            out = base / "exports" / f"memorix_export_{char_file}_{phase_file}.json"
            self.workspace.write_json(out, rows)
            outputs.append(out)

        if target in {"angel", "all"}:
            rows = self.rag_exporter.angel_rows(persona)
            char_file = safe_filename(character)
            phase_file = safe_filename(persona["phase"])
            out = base / "exports" / f"angel_memory_export_{char_file}_{phase_file}.json"
            self.workspace.write_json(out, rows)
            outputs.append(out)

        if target in {"kb", "all"}:
            cards = self._load_evidence(work_id, character)
            char_file = safe_filename(character)
            kb_dir = base / "rag_export" / "kb_chunks" / char_file
            kb_dir.mkdir(parents=True, exist_ok=True)
            for card in cards:
                (kb_dir / f"{card['evidence_id']}.md").write_text(
                    self.rag_exporter.kb_markdown(card),
                    encoding="utf-8",
                )
            outputs.append(kb_dir)

        return "导出完成：\n" + "\n".join(str(path) for path in outputs)

    def run_mvp(self, work_id: str, character: str, phase: str = "auto") -> str:
        parts = [
            self.build_evidence(work_id, character),
            self.build_persona(work_id, character, phase),
            self.build_style(work_id, character),
            self.export(work_id, character, "all", phase),
        ]
        return "\n\n".join(parts)

    async def build_evidence_ai(
        self,
        work_id: str,
        character: str,
        llm_generate: LLMGenerate,
        max_evidence: int = 48,
    ) -> str:
        base = self.workspace.require_work_dir(work_id)
        paragraphs = self.workspace.read_jsonl(base / "index" / "paragraphs.jsonl")
        if not paragraphs:
            raise RuntimeError("尚未切分文本，请先执行 /distill split")
        cards = await AIDistiller(llm_generate, max_evidence).build_evidence(
            work_id,
            character,
            paragraphs,
        )
        if not cards:
            return self.build_evidence(work_id, character)
        char_file = safe_filename(character)
        out = base / "distilled" / f"evidence_cards_{char_file}.jsonl"
        self.workspace.write_jsonl(out, cards)
        return f"AI 证据卡生成完成：{len(cards)} 张\n输出：{out}"

    async def build_persona_ai(
        self,
        work_id: str,
        character: str,
        phase: str,
        llm_generate: LLMGenerate,
        max_evidence: int = 48,
    ) -> str:
        cards = self._load_evidence(work_id, character)
        if not cards:
            await self.build_evidence_ai(work_id, character, llm_generate, max_evidence)
            cards = self._load_evidence(work_id, character)
        if not cards:
            raise RuntimeError("尚未生成证据卡，请先执行 /distill evidence build")
        persona = await AIDistiller(llm_generate, max_evidence).build_persona(
            work_id,
            character,
            cards,
            phase,
        )
        base = self.workspace.require_work_dir(work_id)
        char_file = safe_filename(character)
        phase_file = safe_filename(persona["phase"])
        out = base / "distilled" / f"persona_card_{char_file}_{phase_file}.json"
        self.workspace.write_json(out, persona)
        return (
            f"AI 人格卡生成完成：{character} / {persona['phase']}\n"
            f"证据数：{len(persona.get('evidence_ids', []))}\n"
            f"置信度：{persona.get('confidence')}\n"
            f"输出：{out}"
        )

    async def build_style_ai(
        self,
        work_id: str,
        character: str,
        llm_generate: LLMGenerate,
        max_evidence: int = 48,
    ) -> str:
        base = self.workspace.require_work_dir(work_id)
        paragraphs = self.workspace.read_jsonl(base / "index" / "paragraphs.jsonl")
        utterances = self.workspace.read_jsonl(base / "index" / "utterances.jsonl")
        if not paragraphs:
            raise RuntimeError("尚未切分文本，请先执行 /distill split")
        speech = await AIDistiller(llm_generate, max_evidence).build_style(
            work_id,
            character,
            paragraphs,
            utterances,
        )
        char_file = safe_filename(character)
        out = base / "distilled" / f"speech_fingerprint_{char_file}.json"
        self.workspace.write_json(out, speech)
        return (
            f"AI 语言指纹生成完成：{character}\n"
            f"台词样本：{speech.get('sample_count', 0)}\n"
            f"输出：{out}"
        )

    async def run_ai(
        self,
        work_id: str,
        character: str,
        phase: str,
        llm_generate: LLMGenerate,
        max_evidence: int = 48,
    ) -> str:
        parts = [
            await self.build_evidence_ai(work_id, character, llm_generate, max_evidence),
            await self.build_persona_ai(work_id, character, phase, llm_generate, max_evidence),
            await self.build_style_ai(work_id, character, llm_generate, max_evidence),
            self.export(work_id, character, "all", phase),
        ]
        return "\n\n".join(parts)

    def list_works(self) -> str:
        works = []
        for work_dir in sorted(self.workspace.works_dir().glob("work_*")):
            meta = self.workspace.read_json(work_dir / "raw" / "source_meta.json", {})
            works.append(f"- {work_dir.name}: {meta.get('title', '(未命名)')}")
        if not works:
            return "尚未导入作品。使用 /distill import <作品名> <文件路径>"
        return "已导入作品：\n" + "\n".join(works)

    def status(self, work_id: str) -> str:
        base = self.workspace.require_work_dir(work_id)
        meta = self.workspace.read_json(base / "raw" / "source_meta.json", {})
        counts = {
            "chapters": len(self.workspace.read_jsonl(base / "index" / "chapters.jsonl")),
            "paragraphs": len(self.workspace.read_jsonl(base / "index" / "paragraphs.jsonl")),
            "scenes": len(self.workspace.read_jsonl(base / "index" / "scenes.jsonl")),
            "utterances": len(self.workspace.read_jsonl(base / "index" / "utterances.jsonl")),
        }
        distilled = sorted(path.name for path in (base / "distilled").glob("*"))
        exports = sorted(path.name for path in (base / "exports").glob("*"))
        return (
            f"作品：{meta.get('title', work_id)} ({work_id})\n"
            f"hash：{meta.get('source_hash', '')}\n"
            f"章节/段落/场景/台词：{counts['chapters']}/{counts['paragraphs']}/{counts['scenes']}/{counts['utterances']}\n"
            f"distilled：{', '.join(distilled) if distilled else '无'}\n"
            f"exports：{', '.join(exports) if exports else '无'}"
        )

    def _load_evidence(self, work_id: str, character: str) -> list[dict]:
        base = self.workspace.require_work_dir(work_id)
        char_file = safe_filename(character)
        return self.workspace.read_jsonl(base / "distilled" / f"evidence_cards_{char_file}.jsonl")

    def _build_persona_obj(self, work_id: str, character: str, phase: str) -> dict:
        cards = self._load_evidence(work_id, character)
        if not cards:
            raise RuntimeError("尚未生成证据卡，请先执行 /distill evidence build")
        return self.persona_extractor.build(work_id, character, cards, phase)

    def _build_style_obj(self, work_id: str, character: str) -> dict:
        base = self.workspace.require_work_dir(work_id)
        paragraphs = self.workspace.read_jsonl(base / "index" / "paragraphs.jsonl")
        utterances = self.workspace.read_jsonl(base / "index" / "utterances.jsonl")
        if not paragraphs:
            raise RuntimeError("尚未切分文本，请先执行 /distill split")
        return self.speech_extractor.build(work_id, character, paragraphs, utterances)

    def _load_or_build_persona(self, work_id: str, character: str, phase: str) -> dict:
        base = self.workspace.require_work_dir(work_id)
        pattern_phase = "*" if phase == "auto" else phase
        char_file = safe_filename(character)
        phase_file = "*" if pattern_phase == "*" else safe_filename(pattern_phase)
        matches = sorted((base / "distilled").glob(f"persona_card_{char_file}_{phase_file}.json"))
        if matches:
            return self.workspace.read_json(matches[0], {})
        return self._build_persona_obj(work_id, character, phase)

    def _load_or_build_style(self, work_id: str, character: str) -> dict:
        base = self.workspace.require_work_dir(work_id)
        char_file = safe_filename(character)
        path = base / "distilled" / f"speech_fingerprint_{char_file}.json"
        if path.exists():
            return self.workspace.read_json(path, {})
        return self._build_style_obj(work_id, character)
