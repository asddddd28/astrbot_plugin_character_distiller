# AstrBot 角色动态人格蒸馏器

`astrbot_plugin_character_distiller` 是一个面向 AstrBot 的角色语料蒸馏插件。它可以把 txt/md 小说、剧本、设定集或角色语料导入为可追溯的本地语料库，再生成证据卡、阶段人格卡、语言指纹，以及可供 AstrBot Persona、Knowledge Base、Memorix、Angel Memory 使用的导出文件。

当前版本支持两种模式：

- **AI 蒸馏模式**：优先使用 AstrBot 当前会话的 LLM Provider，或配置中指定的 `distill_provider_id`，从候选证据中提取和归纳角色人格。
- **规则回退模式**：当没有可用 LLM Provider，或关闭 `enable_ai_distillation` 时，使用本地规则完成候选证据与模板化人格卡生成。

插件不会把整本书一次性丢给模型。默认流程是：程序先导入、解码、切分和召回角色相关片段，再把有限数量的候选证据交给 AI 蒸馏，降低成本并保留 `evidence_id` 追溯。

## 功能概览

- 导入 `.txt` / `.md` 文本，自动识别 `utf-8-sig`、`utf-8`、`gb18030`、`gbk` 等常见中文文本编码。
- 保存原始文件、规范化文本、源文件 hash、导入元数据。
- 切分章节、段落、粗略场景和台词候选。
- 为指定角色生成 `evidence_cards_角色.jsonl` 证据卡。
- 基于证据卡生成 `persona_card_角色_阶段.json` 阶段人格卡。
- 生成 `speech_fingerprint_角色.json` 语言指纹。
- 导出：
  - AstrBot Persona Prompt
  - Knowledge Base Markdown chunks
  - Memorix JSON
  - Angel Memory JSON
- 支持导入外部 AI/Agent 生成的完整蒸馏 JSON，并自动转换成插件标准产物。
- 内置 5 个辅助 Skills，用于证据审阅、人格蒸馏、语言指纹、知识卡抽取和导出编排。

## 安装

### 方式一：AstrBot 插件市场/插件管理器

如果你已经通过 AstrBot 插件管理器安装本插件，后续可直接使用“强制更新”。插件元数据已声明 GitHub 仓库：

```text
https://github.com/asddddd28/astrbot_plugin_character_distiller
```

### 方式二：手动安装

把本仓库放到 AstrBot 实例的插件目录下，例如：

```text
data/plugins/astrbot_plugin_character_distiller
```

然后重启 AstrBot 或在插件管理器中重载插件。

### 依赖

当前核心流程只依赖 Python 标准库和 AstrBot API。`requirements.txt` 目前不需要额外 Python 包。

## 配置说明

AstrBot 会读取插件根目录的 `_conf_schema.json` 并生成插件配置。

### provider

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `enable_ai_distillation` | `true` | 启用 AstrBot LLM Provider 进行 AI 提取和蒸馏。关闭后使用纯规则模式。 |
| `distill_provider_id` | `""` | 用于蒸馏的 LLM Provider ID。留空时使用当前会话正在使用的聊天模型。 |
| `eval_provider_id` | `""` | 预留的评估模型 Provider ID。 |

### storage

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `enable_local_corpus` | `true` | 是否启用本地语料库。 |
| `max_context_radius` | `3` | 证据回查时前后文段落数。 |
| `recall_context_radius` | `3` | `/distill recall` 回读原文时命中段落前后的上下文段落数。 |
| `recall_max_chars_per_hit` | `700` | `/distill recall` 每条蒸馏命中或原文段落最多展示的字符数。 |

### distillation

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `min_evidence_count` | `3` | 人格规则建议的最少证据数。 |
| `min_confidence` | `0.75` | 写入人格时建议的最低置信度。 |
| `enable_counter_evidence_check` | `true` | 保留反证检查策略开关。 |
| `detail_level` | `"3_balanced"` | AI 蒸馏精细程度，见下方 6 档说明。 |
| `ai_max_evidence` | `0` | 高级覆盖项。填 `0` 时按 `detail_level` 自动选择候选证据段落数。 |

### 蒸馏精细度

| 等级 | 配置值 | 默认候选证据数 | 适用场景 |
| --- | --- | ---: | --- |
| 1 | `1_quick` | 12 | 快速试跑，只看流程是否通。 |
| 2 | `2_light` | 24 | 轻量蒸馏，提取主线人格和少量核心证据。 |
| 3 | `3_balanced` | 48 | 均衡蒸馏，当前默认等级，适合常规角色卡生成。 |
| 4 | `4_deep` | 80 | 深度蒸馏，加强阶段差异、触发条件、关系变化和反证。 |
| 5 | `5_canonical` | 120 | 高保真蒸馏，适合准备写入长期 Persona/Memory 前的正式版本。 |
| 6 | `6_exhaustive` | 180 | 穷尽式蒸馏，成本最高，适合最终归档或核心角色。 |

你现在看到的 `yonagi_distilled.json` 这类结果，大致接近 **3_balanced 到 4_deep** 之间：阶段弧线完整，但证据卡数量仍保持克制，没有对全部 1187 次出场做穷尽式逐条建模。

### rag

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `use_knowledge_base` | `true` | 是否导出 Knowledge Base Markdown chunk。 |
| `use_memorix` | `false` | 是否导出 Memorix JSON。 |
| `use_angel_memory` | `false` | 是否导出 Angel Memory JSON。 |

### application

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `default_embedding_provider_id` | `""` | 创建 AstrBot Knowledge Base 时使用的 Embedding Provider ID。留空时需要在 `/distill apply kb/all` 命令末尾传入。 |
| `persona_skills` | `"evidence-reviewer,persona-distiller,style-fingerprint,knowledge-distiller"` | 写入 AstrBot Persona 时绑定的 Skills，多个用英文逗号分隔。 |
| `enable_memorix_direct_write` | `true` | `/distill apply memorix/all` 时直接调用已加载的 Memorix 插件写入当前作用域。关闭后只生成导入 JSON。 |
| `memorix_knowledge_type` | `"structured"` | 写入 Memorix 时使用的 `knowledge_type`。可选 `auto`、`factual`、`narrative`、`structured`、`mixed`，角色蒸馏结果建议 `structured`。 |
| `memorix_payload_mode` | `"rich"` | 写入 Memorix 的内容规模。`compact` 只写人格/知识/证据/语言指纹；`rich` 额外写时间线、Persona Prompt 和 KB 检索块。 |

## 命令

```text
/distill help
/distill status [work_id]
/distill import <作品名> <txt或md文件路径>
/distill split <work_id>
/distill import-result <work_id|new> <json路径> [yes|no]
/distill evidence build <角色名> <work_id>
/distill persona build <角色名> <work_id> [phase|auto]
/distill style build <角色名> <work_id>
/distill export <persona|memorix|angel|kb|all> <角色名> <work_id> [phase|auto]
/distill export-package <角色名> <work_id>
/distill apply <persona|kb|memorix|all> <角色名> <work_id> [名称或knowledge_type] [embedding_provider_id]
/distill recall <角色名> <work_id> <关键词> [top_k]
/distill run <角色名> <work_id> [phase|auto]
```

说明：

- `phase` 可填 `early`、`middle`、`late` 或 `auto`。
- `run` 会依次执行 evidence、persona、style、export all。
- `import-result` 会导入外部蒸馏 JSON，例如 Agent 生成的 `yonagi_distilled.json`。
- `export-package` 会对所有阶段人格卡生成完整 Persona/KB/Memorix/Angel 导出包。
- `apply persona` 会把导出的 Persona Prompt 写入 AstrBot Persona。
- `apply kb` 会把 KB Markdown 写入 AstrBot Knowledge Base，并触发向量化。
- `apply memorix` 会把人格、知识卡、证据卡和语言指纹写入已加载的 Memorix 当前作用域。
- `apply all` 会同时写入 Persona、Knowledge Base 和 Memorix。
- `recall` 用于“回忆原文细节”：先查证据/知识/KB/Persona，再按段落索引回读原文上下文。
- 在 AI 蒸馏模式下，`evidence`、`persona`、`style`、`run` 会调用 AstrBot LLM Provider。
- 在没有可用 Provider 时，插件会回退到规则模式。

## 推荐流程

以 `3158.txt` 和角色 `世凪` 为例：

```text
/distill import Shiro "C:/Users/asddd/Downloads/3158.txt"
/distill split work_001
/distill run 世凪 work_001 auto
/distill status work_001
```

如果导入返回的 `work_id` 不是 `work_001`，后续命令请使用实际返回的编号。

### 导入外部蒸馏结果

如果 AI/Agent 已经生成类似 `yonagi_distilled.json` 的完整结果，可以直接导入插件标准目录并自动导出：

```text
/distill import-result new "C:/path/to/yonagi_distilled.json" yes
```

导入到已有 work 但暂不导出：

```text
/distill import-result work_003 "C:/path/to/yonagi_distilled.json" no
```

重新生成完整导出包：

```text
/distill export-package 世凪 work_003
```

### 写入 AstrBot Persona / Knowledge Base / Memorix

导出完成后，文件还只是插件产物。要让 AstrBot 运行时使用，需要显式写入 AstrBot 的 Persona、Knowledge Base 或 Memorix。

写入 Persona：

```text
/distill apply persona 世凪 work_004 世凪
```

这会创建多个 AstrBot Persona，例如：

```text
世凪_early
世凪_middle
世凪_late
世凪_post_end
```

写入 Knowledge Base：

```text
/distill apply kb 世凪 work_004 世凪原著知识库 <embedding_provider_id>
```

如果已在插件配置里填写 `application.default_embedding_provider_id`，命令末尾的 `<embedding_provider_id>` 可以省略。

同时写入 Persona 和 Knowledge Base：

```text
/distill apply all 世凪 work_004 世凪原著知识库 <embedding_provider_id>
```

写入 Memorix：

```text
/distill apply memorix 世凪 work_004 structured
```

Memorix 写入会优先调用已加载的 `astrbot_plugin_memorix` 内部导入服务，写入当前会话所在的 Memorix scope。写入内容包括：

- 阶段人格卡：每个阶段一条结构化记忆。
- 知识卡：用于长期事实与设定检索。
- 证据卡：保留可追溯原文依据。
- 语言指纹：用于保持角色说话方式。
- `rich` 模式还会写入时间线人格、Persona Prompt 和 KB 检索块，便于 `/mem query` 查到更完整的角色资料。

如果 Memorix 未安装、未启用或内部接口不可用，插件不会丢弃结果，而是生成：

```text
works/<work_id>/rag_export/memorix_import/<角色>/mrx_<work_id>_<hash>.json
```

此时可以在 Memorix 配置中启用 `web.import.enabled=true`，通过 `/mem ui` 打开导入中心后导入该 JSON；也可以使用 Memorix 的 raw/plugin_data 扫描导入这个目录。文件名故意使用短 ASCII 前缀，避免部分 Windows 环境下 Memorix 上传接口返回 `Internal Server Error`。

注意：

- Knowledge Base 写入会调用 Embedding Provider 生成向量，可能产生模型调用成本。
- Memorix 直接写入依赖 Memorix 插件已在 AstrBot 中加载；没有加载时会退回到导入 JSON。
- Angel Memory 目前仍以 JSON 导出文件形式提供，建议在对应插件中导入 `exports/` 下的 JSON。
- HAPI 出现不明命令，例如 `command=a`，不要批准。应使用上面的 `/distill apply ...` 显式命令。

### 原文长记忆与回忆细节

原文全文不建议直接写入 Memorix。插件采用分层存储：

- `raw/normalized.txt`：完整原文档案，作为权威来源。
- `index/paragraphs.jsonl`、`index/scenes.jsonl`：原文段落和粗略场景索引。
- `distilled/`：证据卡、知识卡、人格卡和语言指纹。
- Memorix：长期蒸馏记忆，用于角色事实、人格、风格和关键证据检索。
- Knowledge Base/RAG：适合放原文检索块，辅助查找具体情节。

需要“回忆细节”时，用：

```text
/distill recall 世凪 work_004 思维空间 5
```

它会先返回证据卡、知识卡、KB chunk 或 Persona 命中，再返回原文段落上下文。如果该 work 是外部蒸馏 JSON 导入、没有原始 txt 和段落索引，`recall` 会只回查蒸馏产物，并提示缺少原文索引。这样可以避免把整部小说塞进 Memorix，同时保留需要时回读原文的能力。

成功使用 AI 蒸馏时，响应中会出现类似：

```text
AI 证据卡生成完成：24 张
AI 人格卡生成完成：世凪 / middle
AI 语言指纹生成完成：世凪
导出完成：
...
```

## 输出目录

数据默认位于 AstrBot 插件数据目录：

```text
data/plugin_data/astrbot_plugin_character_distiller/works/<work_id>/
```

典型结构：

```text
works/work_001/
├── raw/
│   ├── original.txt
│   ├── normalized.txt
│   └── source_meta.json
├── index/
│   ├── chapters.jsonl
│   ├── paragraphs.jsonl
│   ├── scenes.jsonl
│   └── utterances.jsonl
├── distilled/
│   ├── evidence_cards_<角色>.jsonl
│   ├── persona_card_<角色>_<phase>.json
│   └── speech_fingerprint_<角色>.json
├── exports/
│   ├── astrbot_persona_prompt_<角色>_<phase>.txt
│   ├── memorix_export_<角色>_<phase>.json
│   └── angel_memory_export_<角色>_<phase>.json
└── rag_export/
    └── kb_chunks/<角色>/*.md
```

## AstrBot 端使用说明

### LLM Provider

要使用 AI 蒸馏，请先在 AstrBot 中配置可用的聊天模型 Provider。插件优先级如下：

1. 使用插件配置里的 `provider.distill_provider_id`。
2. 如果为空，使用当前会话正在使用的聊天模型 Provider。
3. 如果仍不可用，自动回退到规则模式。

### 插件更新

从 `v0.2.0` 开始，`metadata.yaml` 已包含 `repo` 字段。通过 AstrBot 插件管理器安装到这一版后，后续“强制更新”应可直接从 GitHub 拉取。

如果你的本地副本仍显示 `v0.1.0`，说明 AstrBot 当前加载的插件目录还没有更新到新版 `metadata.yaml`。可以先手动重装一次，之后再使用强制更新。

### Skills 显示

插件内置的 Skills 位于：

```text
skills/
├── evidence-reviewer/
├── export-packager/
├── knowledge-distiller/
├── persona-distiller/
└── style-fingerprint/
```

这些 Skill 用于指导 AI 在证据审阅、人格归纳、知识卡抽取和语言风格分析时保持可追溯、少编造、分阶段和可审核。新版 `SKILL.md` 已补充 frontmatter 描述，AstrBot 的技能管理界面应能显示说明。

## 内置 Skills

| Skill | 作用 |
| --- | --- |
| `evidence-reviewer` | 审核人格判断是否有足够证据，检查反证、阶段混淆和过度推断。 |
| `persona-distiller` | 从证据卡构建阶段人格卡，要求引用 `evidence_id` 并输出防跑偏规则。 |
| `style-fingerprint` | 提取角色语言指纹，包括句长、语气、称呼、标点、情绪下的表达变化。 |
| `knowledge-distiller` | 从剧情和设定中提取短知识卡，区分事实、推测、传闻和角色视角。 |
| `export-packager` | 将外部蒸馏 JSON 转成标准产物，并编排 Persona/KB/Memorix/Angel 完整导出。 |

## 当前边界

- 章节、场景和说话人识别仍是轻量规则，不等同于完整 NLP 标注。
- AI 蒸馏只处理候选证据样本，不会自动遍历整本书做无限上下文分析。
- 输出的人格卡和记忆导出仍建议人工审核，尤其是要写入长期记忆、Persona 或对外发布时。
- 反证检查、角色关系图、WebUI 证据审核、SQLite FTS5 检索仍属于后续增强方向。

## 排错

### `/distill split` 后台词候选为 0

常见原因：

- 旧版本导入器按 UTF-8 错读了 GBK/GB18030 文本。请更新到 `v0.2.0+` 后重新导入。
- 原文不是用引号标注台词，而是使用冒号、破折号或特殊排版。需要后续增加对应规则。

### `/distill run` 提示没有证据卡

常见原因：

- 角色名写法和原文不一致。
- 使用了旧的坏编码 `work_id`。更新后重新 `import` 和 `split`。
- AI Provider 不可用且规则召回不到角色段落。

### 强制更新失败，提示没有 repository URL

说明本地加载的插件还是旧版 `metadata.yaml`，其中 `repo` 为空。更新到包含以下字段的版本：

```yaml
repo: https://github.com/asddddd28/astrbot_plugin_character_distiller
```

## 版本

- `v0.6.0`：新增 `/distill recall`，支持从蒸馏产物定位并回读原文段落上下文，形成 Memorix 长期记忆与原文档案分层编排。
- `v0.5.0`：新增 `/distill apply memorix`，支持直接写入已加载的 Memorix 当前作用域，并提供导入 JSON 降级路径。
- `v0.4.0`：新增 `/distill apply`，支持把导出结果写入 AstrBot Persona 和 Knowledge Base。
- `v0.3.0`：新增外部蒸馏 JSON 导入、完整导出包、导出编排 Skill，以及 1-6 级蒸馏精细度设置。
- `v0.2.0`：接入 AstrBot LLM Provider，支持 AI 证据提取、人格蒸馏和语言指纹分析；修复中文旧编码导入；补充插件更新元数据。
- `v0.1.0`：规则型 MVP，支持导入、切分、证据卡、人格卡、语言指纹和导出。
