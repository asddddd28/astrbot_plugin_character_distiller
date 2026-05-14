---
name: export-packager
description: 将外部或内部蒸馏结果整理为插件标准产物，并编排 Persona、Knowledge Base、Memorix、Angel Memory 的完整导出与 AstrBot 端写入流程。
---

# Export Packager

用于把已经完成的角色蒸馏结果落入插件标准目录，并生成可供 AstrBot 端使用的导出文件。

## 适用场景

1. AI/Agent 已生成 `yonagi_distilled.json` 这类完整蒸馏结果。
2. 需要把外部 JSON 转成插件标准的 `distilled/` 文件。
3. 需要一次性导出所有阶段的 Persona Prompt、Knowledge Base Markdown、Memorix JSON、Angel Memory JSON。
4. 需要让 AstrBot AI 把导出结果写入 Persona、Knowledge Base 或已安装的 Memorix。
5. 需要回忆原文细节，但不希望把整部原文写入 Memorix。

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

将导出结果写入 AstrBot Persona：

```text
/distill apply persona 世凪 work_003 世凪
```

将导出结果写入 AstrBot Knowledge Base：

```text
/distill apply kb 世凪 work_003 世凪原著知识库 <embedding_provider_id>
```

将导出结果写入 Memorix 当前作用域：

```text
/distill apply memorix 世凪 work_003 structured
```

同时写入 Persona、Knowledge Base 和 Memorix：

```text
/distill apply all 世凪 work_003 世凪原著知识库 <embedding_provider_id>
```

Memorix 直接写入要求 AstrBot 中已加载 `astrbot_plugin_memorix`。如果直接写入失败，插件会生成 `rag_export/memorix_import/<角色>/mrx_<work_id>_<hash>.json`，可在 Memorix 导入中心启用后手动导入。不要把导入文件改成中文文件名或包含 `memorix`、`distill` 的长前缀，部分 Windows 环境下 Memorix 上传接口会返回 500。

默认 `application.memorix_payload_mode=rich`，会写入人格/知识/证据/语言指纹，并额外写入时间线人格、Persona Prompt 和 KB 检索块。需要更少长期记忆时改为 `compact`。

回查原文细节：

```text
/distill recall 世凪 work_003 思维空间 5
```

`recall` 会先查蒸馏产物，再按 `index/paragraphs.jsonl` 回读原文上下文。外部 JSON 导入但没有原文索引时，只能回查 `distilled/` 和 `rag_export/`。

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
10. `rag_export/memorix_import/<角色>/mrx_<work_id>_<hash>.json`
11. rich 模式下 Memorix payload 应包含 `timeline`、`persona_prompt` 和 `kb_chunk` 来源。

## 原则

- 不要直接覆盖用户正在使用的正式 Persona，先生成测试 Persona。
- 长期记忆导入前必须保留 `evidence_id` 或 `source_evidence_ids`。
- 如果外部 JSON 中存在推测性结论，应保留 `candidate` 或 `review_required` 标记。
- 分阶段 Persona 应分别导出，不要只保留 `auto` 阶段。
- 不要批准含义不明的 HAPI 命令请求；写入 AstrBot 应使用 `/distill apply ...`。
- 写入 Memorix 时优先使用 `structured`，除非用户明确要求叙事型或混合型导入。
- 原文全文保留在 Character Distiller `raw/` 和 `index/`，不要整体写入 Memorix；需要细节时使用 `/distill recall ...`。
