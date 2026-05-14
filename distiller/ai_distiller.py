from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Awaitable, Callable

from .utils import short


LLMGenerate = Callable[[str, str], Awaitable[str]]


def _extract_json(text: str):
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.S | re.I)
    if fenced:
        text = fenced.group(1).strip()
    start = min([idx for idx in (text.find("{"), text.find("[")) if idx >= 0], default=-1)
    if start > 0:
        text = text[start:]
    return json.loads(text)


def _sample_evenly(rows: list[dict], limit: int) -> list[dict]:
    if len(rows) <= limit:
        return rows
    by_phase: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_phase[row.get("phase", "middle")].append(row)
    sampled = []
    phase_limit = max(1, limit // max(len(by_phase), 1))
    for phase in ("early", "middle", "late"):
        items = by_phase.get(phase, [])
        if not items:
            continue
        step = max(1, len(items) // phase_limit)
        sampled.extend(items[::step][:phase_limit])
    if len(sampled) < limit:
        seen = {row["paragraph_id"] for row in sampled}
        sampled.extend(row for row in rows if row["paragraph_id"] not in seen)
    return sampled[:limit]


DETAIL_GUIDES = {
    "1_quick": "快速概览：只提取最核心证据和最短人格摘要，适合试跑。",
    "2_light": "轻量蒸馏：覆盖主要阶段和关键证据，输出保持简洁。",
    "3_balanced": "均衡蒸馏：覆盖阶段弧线、行为、关系和语言风格，适合常规使用。",
    "4_deep": "深度蒸馏：加强反证、触发条件、关系变化和阶段差异。",
    "5_canonical": "高保真蒸馏：严格保留 evidence_id，细分人格机制、语言指纹和防跑偏规则。",
    "6_exhaustive": "穷尽式蒸馏：尽量完整覆盖重要证据和阶段差异，成本较高，适合最终归档。",
}


class AIDistiller:
    def __init__(
        self,
        llm_generate: LLMGenerate,
        max_evidence: int = 48,
        detail_level: str = "3_balanced",
    ):
        self.llm_generate = llm_generate
        self.max_evidence = max_evidence
        self.detail_level = detail_level

    def _detail_guide(self) -> str:
        return DETAIL_GUIDES.get(self.detail_level, DETAIL_GUIDES["3_balanced"])

    async def build_evidence(self, work_id: str, character: str, paragraphs: list[dict]) -> list[dict]:
        matched = [p for p in paragraphs if character in p.get("text", "")]
        if not matched:
            return []
        samples = _sample_evenly(matched, self.max_evidence)
        prompt = {
            "task": "从原文片段中为角色提取可追溯证据卡。只依据给定片段，不要编造。",
            "detail_level": self.detail_level,
            "detail_guide": self._detail_guide(),
            "work_id": work_id,
            "character": character,
            "requirements": [
                "输出 JSON 数组，不要输出解释文字。",
                "最多保留 24 条最有价值证据。",
                "每条必须引用输入里的 paragraph_id。",
                "claim_type 从 behavior_pattern, speech_style, relationship, inner_conflict, character_context 中选择。",
                "confidence 使用 0.0 到 1.0。",
            ],
            "schema": {
                "paragraph_id": "输入片段 ID",
                "claim_type": "证据类型",
                "claim": "从证据归纳出的候选判断",
                "evidence_text_summary": "不超过 120 字的原文证据摘要",
                "confidence": 0.0,
                "counter_evidence": ["可选反证或限制"],
            },
            "paragraphs": [
                {
                    "paragraph_id": p["paragraph_id"],
                    "chapter_id": p["chapter_id"],
                    "phase": p["phase"],
                    "text": short(p["text"], 500),
                }
                for p in samples
            ],
        }
        text = await self.llm_generate(
            "你是严谨的角色文本证据审阅器，必须保留证据来源，禁止脱离原文推断。",
            json.dumps(prompt, ensure_ascii=False),
        )
        rows = _extract_json(text)
        para_by_id = {p["paragraph_id"]: p for p in samples}
        cards = []
        for idx, row in enumerate(rows if isinstance(rows, list) else [], start=1):
            para = para_by_id.get(str(row.get("paragraph_id", "")))
            if not para:
                continue
            cards.append(
                {
                    "evidence_id": f"ev_{work_id}_ai_{idx:04d}",
                    "work_id": work_id,
                    "character": character,
                    "phase": para["phase"],
                    "claim_type": row.get("claim_type", "character_context"),
                    "claim": row.get("claim", ""),
                    "evidence_text_summary": row.get("evidence_text_summary") or short(para["text"], 220),
                    "source_refs": [
                        {
                            "chapter_id": para["chapter_id"],
                            "scene_id": "",
                            "paragraph_ids": [para["paragraph_id"]],
                        }
                    ],
                    "confidence": float(row.get("confidence", 0.7)),
                    "counter_evidence": row.get("counter_evidence", []),
                    "status": "ai_candidate",
                }
            )
        return cards

    async def build_persona(self, work_id: str, character: str, cards: list[dict], phase: str) -> dict:
        selected = [c for c in cards if phase == "auto" or c.get("phase") == phase]
        selected = sorted(selected, key=lambda c: c.get("confidence", 0), reverse=True)[:32]
        prompt = {
            "task": "基于证据卡蒸馏角色人格卡。只使用 evidence_id 支持的判断。",
            "detail_level": self.detail_level,
            "detail_guide": self._detail_guide(),
            "work_id": work_id,
            "character": character,
            "phase": phase,
            "schema": {
                "phase": "early/middle/late/auto 中最合适阶段",
                "surface_trait": "表层表现",
                "deep_mechanism": "深层动机和心理机制",
                "trigger_conditions": ["触发条件"],
                "expression_patterns": ["表达策略"],
                "behavior_rules": ["扮演时行为规则"],
                "anti_drift_rules": ["防跑偏规则"],
                "evidence_ids": ["引用的 evidence_id"],
                "counter_evidence_ids": ["有冲突或限制的 evidence_id"],
                "confidence": 0.0,
                "status": "review_required",
            },
            "evidence_cards": selected,
        }
        text = await self.llm_generate(
            "你是角色人格蒸馏器。输出严格 JSON 对象，结论必须可追溯到 evidence_id。",
            json.dumps(prompt, ensure_ascii=False),
        )
        obj = _extract_json(text)
        obj["work_id"] = work_id
        obj["character"] = character
        obj.setdefault("phase", phase if phase != "auto" else "middle")
        obj.setdefault("evidence_ids", [c["evidence_id"] for c in selected[:12]])
        obj.setdefault("counter_evidence_ids", [])
        obj.setdefault("confidence", 0.75)
        obj.setdefault("status", "ai_review_required")
        return obj

    async def build_style(
        self,
        work_id: str,
        character: str,
        paragraphs: list[dict],
        utterances: list[dict],
    ) -> dict:
        related = [p for p in paragraphs if character in p.get("text", "")]
        samples = _sample_evenly(related, 32)
        prompt = {
            "task": "从原文片段和台词候选中蒸馏角色语言指纹。不要复述长原文。",
            "detail_level": self.detail_level,
            "detail_guide": self._detail_guide(),
            "work_id": work_id,
            "character": character,
            "schema": {
                "phase": "auto",
                "default_tone": "默认语气",
                "sentence_length": "句长和节奏特征",
                "punctuation_profile": {"question_rate": 0.0, "exclamation_rate": 0.0},
                "common_moves": ["常见话术动作"],
                "emotion_variants": {"worried": "", "hurt": "", "trusting": ""},
                "forbidden_style": ["禁止风格"],
                "sample_quotes_preview": ["短台词样本"],
            },
            "paragraphs": [
                {"paragraph_id": p["paragraph_id"], "phase": p["phase"], "text": short(p["text"], 420)}
                for p in samples
            ],
            "utterances": [u.get("text", "") for u in utterances[:60]],
        }
        text = await self.llm_generate(
            "你是角色语言风格分析器。输出严格 JSON 对象，避免编造原文没有的口癖。",
            json.dumps(prompt, ensure_ascii=False),
        )
        obj = _extract_json(text)
        obj["work_id"] = work_id
        obj["character"] = character
        obj.setdefault("phase", "auto")
        obj.setdefault("sample_count", len(obj.get("sample_quotes_preview", [])))
        return obj
