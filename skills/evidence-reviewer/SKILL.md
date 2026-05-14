---
name: evidence-reviewer
description: 审核角色人格判断是否有足够原文证据，检查反证、阶段混淆、过度推断和 evidence_id 追溯完整性。
---

# Evidence Reviewer

用于审阅角色人格蒸馏结果是否可靠。该技能不负责创作新人格设定，而是检查每个判断是否被证据卡支持。

## 审核规则

1. 检查证据数量是否足够，不接受只有单一片段支持的长期人格结论。
2. 检查是否存在反证、例外情境或阶段变化。
3. 检查是否把短期情绪、单次事件或叙事视角误判为长期人格。
4. 检查是否跨 `early`、`middle`、`late` 阶段混用互相冲突的行为模式。
5. 检查每条人格判断是否能追溯到明确的 `evidence_id`。
6. 输出结论使用 `approve`、`reject` 或 `needs_more_evidence`。

## 输出建议

```json
{
  "verdict": "needs_more_evidence",
  "reason": "证据主要来自单一阶段，缺少反证检查。",
  "missing": ["late 阶段证据", "关系变化证据"],
  "accepted_evidence_ids": ["ev_work_001_ai_0001"],
  "rejected_evidence_ids": []
}
```
