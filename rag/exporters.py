from __future__ import annotations

import json


class RagExporter:
    def memorix_rows(self, persona: dict) -> list[dict]:
        return [
            {
                "text": f"{persona['character']}（{persona.get('phase', 'auto')}）人格候选：{persona.get('deep_mechanism', '')}",
                "knowledge_type": "structured",
                "tags": [
                    "canon",
                    "persona",
                    f"character:{persona['character']}",
                    f"phase:{persona.get('phase', 'auto')}",
                    "protected",
                    "review_required",
                ],
                "source": {
                    "work_id": persona.get("work_id"),
                    "evidence_ids": persona.get("evidence_ids", []),
                },
            }
        ]

    def angel_rows(self, persona: dict) -> list[dict]:
        return [
            {
                "judgment": f"{persona['character']}在{persona.get('phase', 'auto')}阶段的候选人格需要按证据卡审核后使用。",
                "reasoning": persona.get("deep_mechanism", ""),
                "tags": [
                    f"persona:{persona['character']}",
                    f"phase:{persona.get('phase', 'auto')}",
                    "canon",
                    "review_required",
                ],
                "strength": int(float(persona.get("confidence", 0.5)) * 100),
                "memory_type": "persona",
                "source_evidence_ids": persona.get("evidence_ids", []),
            }
        ]

    def kb_markdown(self, card: dict) -> str:
        refs = card.get("source_refs", [])
        ref_text = json.dumps(refs, ensure_ascii=False)
        return (
            f"# evidence_id: {card['evidence_id']}\n\n"
            "metadata:\n"
            f"- work_id: {card.get('work_id', '')}\n"
            f"- character: {card.get('character', '')}\n"
            f"- phase: {card.get('phase', '')}\n"
            f"- type: {card.get('claim_type', '')}\n"
            f"- confidence: {card.get('confidence', '')}\n"
            f"- source_refs: {ref_text}\n\n"
            "## 证据摘要\n"
            f"{card.get('evidence_text_summary', '')}\n\n"
            "## 候选结论\n"
            f"{card.get('claim', '')}\n"
        )
