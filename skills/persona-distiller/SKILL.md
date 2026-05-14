---
name: persona-distiller
description: 从证据卡构建可追溯的阶段人格卡，要求区分表层表现、深层机制、触发条件、行为规则和防跑偏规则。
---

# Persona Distiller

用于从证据卡中构建角色人格，而不是直接从原文片段随意总结。所有人格判断都必须能回到 `evidence_id`。

## 蒸馏规则

1. 不只输出“温柔”“冷静”“傲娇”等性格标签，必须解释触发条件和行为方式。
2. 每个人格判断应包含：触发条件、表层表达、深层动机、行为倾向。
3. 区分表层语言和真实心理，避免把口头强硬误判为内在冷漠。
4. 区分阶段人格：`early`、`middle`、`late` 或 `post_end`。
5. 对证据不足的结论标记为候选，不写成最终定论。
6. 必须输出防跑偏规则，防止运行时聊天记忆污染原著人格。
7. 必须引用 `evidence_id`，并记录可能的反证。

## 输出建议

```json
{
  "phase": "middle",
  "surface_trait": "面对压力时表现克制，较少直接表达需求。",
  "deep_mechanism": "倾向先确认局势和他人安全，再处理自身情绪。",
  "trigger_conditions": ["同伴受伤", "关系被质疑"],
  "expression_patterns": ["短句确认", "回避过度解释"],
  "behavior_rules": ["优先行动而不是长篇自白"],
  "anti_drift_rules": ["没有 evidence_id 支持时，不添加新创伤或口癖"],
  "evidence_ids": ["ev_work_001_ai_0001"],
  "counter_evidence_ids": [],
  "confidence": 0.82,
  "status": "review_required"
}
```
