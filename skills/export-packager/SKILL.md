---
name: export-packager
description: 将外部或内部蒸馏结果整理为插件标准产物，并编排 Persona、Knowledge Base、Memorix、Angel Memory 的完整导出流程。
---

# Export Packager

用于把已经完成的角色蒸馏结果落入插件标准目录，并生成可供 AstrBot 端使用的导出文件。

## 适用场景

1. AI/Agent 已生成 `yonagi_distilled.json` 这类完整蒸馏结果。
2. 需要把外部 JSON 转成插件标准的 `distilled/` 文件。
3. 需要一次性导出所有阶段的 Persona Prompt、Knowledge Base Markdown、Memorix JSON、Angel Memory JSON。

## 推荐命令

导入外部蒸馏结果，并自动导出完整包：

```text
/distill import-result new C:/path/yonagi_distilled.json yes
```

导入到已有 work，但暂不导出：

```text
/distill import-result work_003 C:/path/yonagi_distilled.json no
```

对已有标准产物重新导出完整包：

```text
/distill export-package 世凪 work_003
```

## 输出检查

导出完成后应检查：

1. `distilled/evidence_cards_<角色>.jsonl`
2. `distilled/persona_card_<角色>_<phase>.json`
3. `distilled/speech_fingerprint_<角色>.json`
4. `distilled/knowledge_cards_<角色>.jsonl`
5. `exports/astrbot_persona_prompt_<角色>_<phase>.txt`
6. `exports/memorix_export_<角色>_<phase>.json`
7. `exports/angel_memory_export_<角色>_<phase>.json`
8. `rag_export/kb_chunks/<角色>/`
9. `rag_export/knowledge_cards/<角色>/`

## 原则

- 不要直接覆盖用户正在使用的正式 Persona，先生成测试 Persona。
- 长期记忆导入前必须保留 `evidence_id` 或 `source_evidence_ids`。
- 如果外部 JSON 中存在推测性结论，应保留 `candidate` 或 `review_required` 标记。
- 分阶段 Persona 应分别导出，不要只保留 `auto` 阶段。
