from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .utils import safe_filename, utc_now
from ..storage.workspace import DistillerWorkspace


PHASE_MAP = {
    "序幕": "early",
    "少年时期": "early",
    "青年时期": "middle",
    "壮年时期": "late",
    "终章": "post_end",
    "尾声": "post_end",
}


def normalize_phase(value: str) -> str:
    return PHASE_MAP.get(value, value or "auto")


class DistilledResultImporter:
    def __init__(self, workspace: DistillerWorkspace):
        self.workspace = workspace

    def import_result(self, work_id: str, json_path: Path) -> dict[str, Any]:
        json_path = json_path.expanduser()
        if not json_path.exists():
            raise FileNotFoundError(f"蒸馏结果文件不存在：{json_path}")

        data = json.loads(json_path.read_text(encoding="utf-8"))
        metadata = data.get("metadata", {})
        character = metadata.get("character") or self._infer_character(data)
        if not character:
            raise ValueError("蒸馏结果缺少 metadata.character，无法确定角色名")

        if work_id.lower() in {"", "new", "auto"}:
            work_id = self.workspace.next_work_id()
        base = self.workspace.ensure_work_layout(work_id)

        raw_dir = base / "raw"
        imported_copy = raw_dir / "imported_distilled_result.json"
        imported_copy.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

        meta_path = raw_dir / "source_meta.json"
        current_meta = self.workspace.read_json(meta_path, {})
        current_meta.update(
            {
                "work_id": work_id,
                "title": metadata.get("source", current_meta.get("title", work_id)),
                "source_type": "external_distilled_result",
                "character": character,
                "original_path": str(imported_copy.relative_to(base)),
                "imported_result_path": str(imported_copy.relative_to(base)),
                "source_encoding": metadata.get("encoding", ""),
                "total_mentions": metadata.get("total_mentions"),
                "created_at": current_meta.get("created_at") or utc_now(),
                "updated_at": utc_now(),
            }
        )
        self.workspace.write_json(meta_path, current_meta)

        char_file = safe_filename(character)
        evidence_cards = self._convert_evidence(work_id, character, data.get("evidence_cards", []))
        self.workspace.write_jsonl(base / "distilled" / f"evidence_cards_{char_file}.jsonl", evidence_cards)

        persona_count = 0
        for persona in data.get("persona_cards", []):
            converted = self._convert_persona(work_id, character, persona)
            phase_file = safe_filename(converted["phase"])
            self.workspace.write_json(
                base / "distilled" / f"persona_card_{char_file}_{phase_file}.json",
                converted,
            )
            persona_count += 1

        style = self._convert_style(work_id, character, data.get("style_fingerprint", {}))
        self.workspace.write_json(base / "distilled" / f"speech_fingerprint_{char_file}.json", style)

        knowledge_cards = self._convert_knowledge(work_id, character, data.get("knowledge_cards", []))
        self.workspace.write_jsonl(base / "distilled" / f"knowledge_cards_{char_file}.jsonl", knowledge_cards)

        review = data.get("evidence_review", {})
        if review:
            self.workspace.write_json(base / "eval" / f"evidence_review_{char_file}.json", review)

        return {
            "work_id": work_id,
            "character": character,
            "evidence_count": len(evidence_cards),
            "persona_count": persona_count,
            "knowledge_count": len(knowledge_cards),
            "has_style": bool(style),
            "has_review": bool(review),
        }

    @staticmethod
    def _infer_character(data: dict[str, Any]) -> str:
        for persona in data.get("persona_cards", []):
            if persona.get("character"):
                return persona["character"]
        for card in data.get("evidence_cards", []):
            if card.get("character"):
                return card["character"]
        return ""

    @staticmethod
    def _convert_evidence(work_id: str, character: str, cards: list[dict]) -> list[dict]:
        converted = []
        for idx, card in enumerate(cards, start=1):
            converted.append(
                {
                    "evidence_id": card.get("evidence_id") or f"ev_{work_id}_import_{idx:04d}",
                    "work_id": work_id,
                    "character": character,
                    "phase": normalize_phase(card.get("phase", "")),
                    "phase_name": card.get("phase", ""),
                    "claim_type": card.get("claim_type") or card.get("category", "character_context"),
                    "claim": card.get("claim") or card.get("content", ""),
                    "evidence_text_summary": card.get("evidence_text_summary") or card.get("raw_text") or card.get("content", ""),
                    "source_refs": [
                        {
                            "source_lines": card.get("source_lines", ""),
                            "paragraph_ids": card.get("paragraph_ids", []),
                        }
                    ],
                    "confidence": float(card.get("confidence", 0.8)),
                    "counter_evidence": card.get("counter_evidence", []),
                    "status": card.get("status", "imported_review_required"),
                }
            )
        return converted

    @staticmethod
    def _convert_persona(work_id: str, character: str, persona: dict) -> dict:
        converted = dict(persona)
        converted["work_id"] = work_id
        converted["character"] = character
        converted["phase"] = normalize_phase(persona.get("phase") or persona.get("phase_name", "auto"))
        converted.setdefault("phase_name", persona.get("phase_name", converted["phase"]))
        converted.setdefault("trigger_conditions", [])
        converted.setdefault("expression_patterns", [])
        converted.setdefault("behavior_rules", [])
        converted.setdefault("anti_drift_rules", [])
        converted.setdefault("evidence_ids", [])
        converted.setdefault("counter_evidence_ids", [])
        converted.setdefault("confidence", 0.75)
        converted.setdefault("status", "imported_review_required")
        return converted

    @staticmethod
    def _convert_style(work_id: str, character: str, style: dict) -> dict:
        converted = dict(style or {})
        converted["work_id"] = work_id
        converted["character"] = character
        converted.setdefault("phase", "auto")
        if "sample_quotes" in converted and "sample_quotes_preview" not in converted:
            converted["sample_quotes_preview"] = converted["sample_quotes"]
        converted.setdefault("sample_count", len(converted.get("sample_quotes_preview", [])))
        converted.setdefault("common_moves", [])
        converted.setdefault("forbidden_style", [])
        return converted

    @staticmethod
    def _convert_knowledge(work_id: str, character: str, cards: list[dict]) -> list[dict]:
        converted = []
        for idx, card in enumerate(cards, start=1):
            row = dict(card)
            row.setdefault("knowledge_id", f"kn_{work_id}_{idx:04d}")
            row["work_id"] = work_id
            row["character"] = character
            row.setdefault("status", "imported_review_required")
            converted.append(row)
        return converted
