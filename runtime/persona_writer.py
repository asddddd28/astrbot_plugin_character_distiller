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
                "【外部记忆与原文依据使用规则】",
                "- 如果系统上下文中提供了 Memorix、Knowledge Base、证据卡或原文检索片段，必须优先依据这些内容回答。",
                "- 当用户询问具体情节、台词、场景、时间线或“回忆细节”时，优先使用原文回查结果（例如 /distill recall），而不是凭印象补全。",
                "- 如果上下文没有提供对应原文依据，只能基于已知人格设定概括回答，并说明需要原文回查才能确认细节。",
                "- 不要把 Persona 设定当作原文事实来源；Persona 只约束角色人格、语气和行为边界。",
                "",
                "【证据追溯】",
                "- " + ", ".join(persona.get("evidence_ids", [])[:20]),
            ]
        )
        return "\n".join(lines).strip() + "\n"
