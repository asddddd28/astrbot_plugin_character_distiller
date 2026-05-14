# AstrBot 角色动态人格蒸馏器

这是一个 AstrBot 插件 MVP，用于把 txt/md 角色语料整理成可追溯的人格蒸馏产物：

- 高保真原文保存与 hash 追溯
- 章节、段落、粗略场景、台词候选切分
- `evidence_cards.jsonl` 证据卡
- `persona_card.json` 阶段人格候选
- `speech_fingerprint.json` 语言指纹候选
- AstrBot Persona Prompt、Knowledge Base Markdown、Memorix JSON、Angel Memory JSON 导出

## 命令

```text
/distill import <作品名> <txt或md文件路径>
/distill split <work_id>
/distill evidence build <角色名> <work_id>
/distill persona build <角色名> <work_id> [phase|auto]
/distill style build <角色名> <work_id>
/distill export <persona|memorix|angel|kb|all> <角色名> <work_id> [phase|auto]
/distill run <角色名> <work_id> [phase|auto]
/distill status [work_id]
/distill help
```

## 推荐流程

```text
/distill import 作品名 C:\novels\sample.txt
/distill split work_001
/distill run 角色A work_001 auto
```

生成的数据位于 AstrBot 数据目录：

```text
data/plugin_data/astrbot_plugin_character_distiller/works/work_001/
```

## 当前 MVP 边界

第一版先跑通完整构建流程，蒸馏采用本地启发式候选生成，不会把候选人格直接当成最终结论。正式写入 Persona、Memorix 或 Angel Memory 前，应人工审核 `evidence_id`、阶段和反证。

后续版本可继续接入 LLM Provider、SQLite FTS5、自动说话人识别、WebUI 证据审核和 Self-Evolution Arc 导出。
