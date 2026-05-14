from __future__ import annotations


class PersonaWriter:
    def build_prompt(self, persona: dict, speech: dict | None = None) -> str:
        speech = speech or {}
        lines = [
            f"你正在扮演【{persona['character']}】。",
            "",
            "【当前阶段】",
            f"- 阶段：{persona.get('phase', 'auto')}",
            "- 该阶段信息必须优先来自 evidence_id 支持的候选人格卡；证据不足时保持保守。",
            "",
            "【核心人格机制】",
            f"- 表层模式：{persona.get('surface_trait', '')}",
            f"- 深层机制：{persona.get('deep_mechanism', '')}",
            "",
            "【触发条件】",
        ]
        lines.extend(f"- {item}" for item in persona.get("trigger_conditions", []))
        lines.extend(["", "【表达策略】"])
        lines.extend(f"- {item}" for item in persona.get("expression_patterns", []))
        if speech:
            lines.extend(
                [
                    "",
                    "【语言风格】",
                    f"- 默认语气：{speech.get('default_tone', '')}",
                    f"- 句长：{speech.get('sentence_length', '')}",
                ]
            )
            lines.extend(f"- {item}" for item in speech.get("common_moves", []))
        lines.extend(["", "【行为边界】"])
        lines.extend(f"- {item}" for item in persona.get("behavior_rules", []))
        lines.extend(["", "【反跑偏规则】"])
        lines.extend(f"- {item}" for item in persona.get("anti_drift_rules", []))
        lines.extend(
            [
                "",
                "【动态记忆使用规则】",
                "- 用户关系和近期互动可由记忆系统提供，但不得覆盖原著核心人格。",
                "- 若运行时记忆与证据卡冲突，以 evidence_id 支持的原著人格为准。",
                "",
                "【证据追溯】",
                "- " + ", ".join(persona.get("evidence_ids", [])[:20]),
            ]
        )
        return "\n".join(lines).strip() + "\n"
