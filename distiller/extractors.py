from __future__ import annotations

import re
from collections import Counter

from .utils import short


EMOTION_HINTS = {
    "担心": ["担心", "不安", "焦急", "慌", "皱眉", "沉默"],
    "愤怒": ["怒", "吼", "冷笑", "咬牙", "质问"],
    "回避": ["别问", "无所谓", "转身", "避开", "沉默"],
    "保护": ["挡", "护", "扶", "照顾", "包扎", "救"],
    "信任": ["交给你", "相信", "拜托", "点头"],
}


class EvidenceExtractor:
    def build(self, work_id: str, character: str, paragraphs: list[dict]) -> list[dict]:
        matched = [p for p in paragraphs if character in p["text"]]
        cards = []
        for idx, para in enumerate(matched, start=1):
            hints = self._hints(para["text"])
            claim_type = "behavior_pattern" if hints else "character_context"
            claim = self._claim(character, hints)
            cards.append(
                {
                    "evidence_id": f"ev_{work_id}_{idx:04d}",
                    "work_id": work_id,
                    "character": character,
                    "phase": para["phase"],
                    "claim_type": claim_type,
                    "claim": claim,
                    "evidence_text_summary": short(para["text"], 220),
                    "source_refs": [
                        {
                            "chapter_id": para["chapter_id"],
                            "scene_id": "",
                            "paragraph_ids": [para["paragraph_id"]],
                        }
                    ],
                    "confidence": 0.62 if hints else 0.45,
                    "counter_evidence": [],
                    "status": "candidate",
                }
            )
        return cards

    @staticmethod
    def _hints(text: str) -> list[str]:
        found = []
        for tag, words in EMOTION_HINTS.items():
            if any(word in text for word in words):
                found.append(tag)
        return found

    @staticmethod
    def _claim(character: str, hints: list[str]) -> str:
        if not hints:
            return f"{character}在该片段中出现，但需要更多上下文才能形成人格判断。"
        return f"{character}在包含{ '、'.join(hints) }线索的场景中有可观察行为，适合作为候选人格证据。"


class PersonaExtractor:
    def build(self, work_id: str, character: str, cards: list[dict], phase: str = "auto") -> dict:
        selected = [c for c in cards if c["character"] == character]
        if phase != "auto":
            selected = [c for c in selected if c["phase"] == phase]
        phase_counts = Counter(c["phase"] for c in selected)
        phase_name = phase if phase != "auto" else (phase_counts.most_common(1)[0][0] if phase_counts else "middle")
        evidence_ids = [c["evidence_id"] for c in selected[:12]]
        confidence = min(0.9, 0.35 + len(evidence_ids) * 0.08)

        return {
            "work_id": work_id,
            "character": character,
            "phase": phase_name,
            "surface_trait": "候选：需人工审核的表层表达模式",
            "deep_mechanism": "当前 MVP 使用启发式证据聚合，只将结论标记为候选；正式写入 Persona 前应人工审核 evidence_id。",
            "trigger_conditions": [
                "角色名出现在同一段落或场景",
                "段落包含情绪、行为或关系线索",
                "同类线索在多个证据卡中重复出现",
            ],
            "expression_patterns": [
                "优先依据多张证据卡归纳表达策略",
                "低证据数量时避免强人格断言",
                "阶段不明确时保持保守表达",
            ],
            "behavior_rules": [
                "不要把孤立情绪当成长期人格",
                "不要跨阶段混用明显冲突的表达",
                "回答时优先遵守有 evidence_id 的规则",
            ],
            "anti_drift_rules": [
                "禁止把运行时聊天记忆覆盖为原著核心人格",
                "禁止无证据添加口癖、关系或创伤设定",
                "遇到证据不足的问题应保持模糊或请求补充语料",
            ],
            "evidence_ids": evidence_ids,
            "counter_evidence_ids": [],
            "confidence": round(confidence, 2),
            "status": "candidate" if len(evidence_ids) < 3 else "review_required",
        }


class SpeechExtractor:
    def build(self, work_id: str, character: str, paragraphs: list[dict], utterances: list[dict]) -> dict:
        related_paras = [p["text"] for p in paragraphs if character in p["text"]]
        quotes = []
        for text in related_paras:
            quotes.extend(re.findall(r"[“\"']([^“”\"']{1,120})[”\"']", text))
        if not quotes:
            quotes = [u["text"] for u in utterances[:30]]

        lengths = [len(q) for q in quotes]
        avg_len = round(sum(lengths) / len(lengths), 1) if lengths else 0
        question_rate = round(sum("?" in q or "？" in q for q in quotes) / max(len(quotes), 1), 2)
        exclaim_rate = round(sum("!" in q or "！" in q for q in quotes) / max(len(quotes), 1), 2)

        return {
            "work_id": work_id,
            "character": character,
            "phase": "auto",
            "sample_count": len(quotes),
            "default_tone": "候选：需结合人工审核样本确认",
            "sentence_length": f"平均台词长度约 {avg_len} 字；样本不足时不要过度推断。",
            "punctuation_profile": {
                "question_rate": question_rate,
                "exclamation_rate": exclaim_rate,
            },
            "common_moves": [
                "从多段证据中抽象句式，不直接复制长原文",
                "按对象、情绪和阶段拆分表达差异",
                "将口癖与人格机制分开保存",
            ],
            "emotion_variants": {
                "worried": "如证据显示担心，应观察是否转化为责备、沉默或行动。",
                "hurt": "如证据显示受伤，应观察句长、回避和解释倾向变化。",
                "trusting": "如证据显示信任，应观察称呼、请求和坦率程度变化。",
            },
            "forbidden_style": [
                "不要无证据添加卖萌或网络流行口癖",
                "不要把旁白文风当成角色说话方式",
                "不要用少量经典台词覆盖全部阶段",
            ],
            "sample_quotes_preview": [short(q, 60) for q in quotes[:6]],
        }
