---
name: style-fingerprint
description: 提取角色语言指纹，分析句长、语气、称呼、标点、反问、情绪变化和对象差异，避免大段复制原文台词。
---

# Style Fingerprint

用于提取角色说话方式和表达策略。目标不是复制原文台词，而是形成可运行、可约束的语言风格规则。

## 分析规则

1. 分析句长、语气、称呼、口癖、标点、反问、讽刺、情绪泄露等特征。
2. 区分不同对象、不同阶段、不同情绪下的语言变化。
3. 不要直接复制大量原文台词，只保留短样本和抽象表达策略。
4. 区分叙述者文风和角色台词风格。
5. 标记禁止风格，防止运行时添加无证据的网络口癖、卖萌或过度戏剧化表达。

## 输出建议

```json
{
  "phase": "auto",
  "default_tone": "克制、短促，倾向先确认事实。",
  "sentence_length": "多使用短句和中等长度解释句。",
  "punctuation_profile": {
    "question_rate": 0.18,
    "exclamation_rate": 0.03
  },
  "common_moves": ["先否认情绪，再转向实际行动"],
  "emotion_variants": {
    "worried": "减少解释，使用更短的确认句。",
    "hurt": "回避直接控诉，转为沉默或事实陈述。",
    "trusting": "允许更直接的请求和承诺。"
  },
  "forbidden_style": ["无证据卖萌", "现代网络梗", "过度长篇独白"],
  "sample_quotes_preview": ["短台词样本"]
}
```
