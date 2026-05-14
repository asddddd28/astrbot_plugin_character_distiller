---
name: knowledge-distiller
description: 从剧情、设定和证据卡中抽取短知识卡，区分事实、推测、传闻和角色视角，并保留 evidence_id 来源。
---

# Knowledge Distiller

用于把原文证据整理为可进入 Knowledge Base、Memorix 或 Angel Memory 的短知识卡。该技能强调短、准、可追溯。

## 抽取规则

1. 每条知识尽量短，避免把剧情摘要当作知识库条目。
2. 必须保留来源 `evidence_id` 或原文片段引用。
3. 区分事实、推测、传闻、角色视角和叙述者视角。
4. 不把一次性情绪或误会写成世界观规则。
5. 角色关系、地点设定、事件因果和长期状态应分开成不同条目。

## 输出建议

```json
{
  "knowledge": "角色 A 在中期阶段与角色 B 的关系明显转为互相信任。",
  "type": "relationship",
  "certainty": "candidate",
  "source_evidence_ids": ["ev_work_001_ai_0003"],
  "tags": ["character:A", "phase:middle", "relationship", "review_required"]
}
```
