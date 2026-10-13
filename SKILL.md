---
name: learning-canvas
description: >-
  把主题、文章、PDF、章节或笔记做成单文件交互式 HTML 学习报告，通过 FLOW
  知识帧、有损探测、留白复述和来源走查支持掌握与复盘。适用于“帮我学会、讲清楚、
  知识点拆解、交互式学习报告、study guide”；不用于单个事实查询或逐字原文摘要。
metadata:
  version: "1.1.4"
  display_name: "学习画布"
  display_name_en: "Learning Canvas"
  agent_created: true
  display_order: 50
---

# 学习画布 · Learning Canvas

学习效果优先于视觉装饰。把材料变成 3–5 个必要知识帧，用有损探测检查骨架，用学习者自己的话暴露漏帧与新增，用可定位的来源支持走查。

运行要求：Python 3.10+；核心流程只用标准库。读取 PDF 另装 `requirements-optional.txt` 中的 pypdf。支持 UTF-8 TXT/Markdown 与可抽取文字的 PDF，不含 OCR 或联网抓取。用户只给主题时，先找到并真实读取可靠材料，再保存为源文件；不得用模型编写的材料伪装成用户原文。

## 0. 意图闸门

- 只查一个事实，或只想要简短解释：直接回答，不启动报告流程。
- 要逐字引用的摘要：直接读文件或使用文档/PDF 工作流。
- 想掌握、讲给别人、复盘：使用本技能。材料长短不是唯一依据。

## 1. FLOW 与工作流

F = Frames 知识帧 → L = Lossy Probe 有损探测 → O = Own-Words 自己的话 → W = Walk-through 走查。顺序不可跳过。

| 阶段 | 操作 | 交互 |
|---|---|---|
| P1 摄取 | 跑 `flow_plan.py` 建源索引，真实读取全文与相关上下文 | 自动 |
| P2 切帧 | 读 [flow_framework.md](references/flow_framework.md)，写 3–5 帧、删除损失理由和每条断言的锚点 | 给帧清单请用户确认粒度；已有自主授权则按授权执行 |
| P3 探测 | 跑 `lossy_perturb.py`，润色后并入 `probes`，至少一题 | 自动 |
| P4 留白 | 邀请在场用户口述；HTML 练习区保持空白 | 条件邀请，不阻塞 |
| P5 内容规格 | 按 Schema 完成 JSON，跑渲染器 `--dry-run` | 自动 |
| P6 核验 | 独立锚点核验并回填，人工核对含义，再正式渲染 | 未通过退出 10，回退修复，不交付 |
| P7 交付 | 给 HTML 路径、实际覆盖率与复习提案 | 问是否建立提醒；已有授权则不重复询问 |

只有真实报告制作时执行 P2/P7；开发或测试技能包不需要把样例当成用户学习任务。详情见 [interaction_checkpoints.md](references/interaction_checkpoints.md)。

## 2. 内容规格与生成

**禁止直接手写最终报告 HTML**。必须按 [report_spec.schema.json](assets/report_spec.schema.json) 写 spec，再调用渲染器。可参照 [完整 HTTPS spec](assets/worked_example_https.json) 及 [对应源材料](assets/worked_example_https_source.md)。

每帧字段：`id / title / subtitle / body / why / claims`。每个来源断言：`text / anchor / source_id`；`anchor` 为精确原文引句，`source_id` 指向 `sources[].id`。无来源补充使用 `{"text":"…","ai_only":true}`，不能挂锚点或假来源。来源条目包含 `id / text`，推荐同时填源索引给出的 `paragraph_id / line_start / line_end`。

文本仅支持三种行内标记：`**加粗**`、单反引号代码、`{S1}` 来源徽标。所有其他 HTML/链接语法按文本转义。`rationale` 必须说明 FLOW、切帧方法、理论映射与已有方法关系；理论依据按需读 [theory_map.md](references/theory_map.md) 和 [prior_art.md](references/prior_art.md)。不把设计推断声称为普遍学习定律。

```bash
python scripts/render_report.py spec.json --dry-run
python scripts/render_report.py spec.json --out report.html
python scripts/render_report.py spec.json --out report-static.html --static
```

渲染退出码：0 成功；2 spec/输入不合规；3 模板缺失或多出占位符。固定模板与 JS 在构建时内联，最终 HTML 无 CDN、可离线、可打印。未核验或已变更的规格仅渲染为显著草稿，不能交付为最终报告。质量要求见 [html_quality_bar.md](references/html_quality_bar.md)。

## 3. 四道核验门

写锚点前读 [verification_protocol.md](references/verification_protocol.md)。

```bash
python scripts/anchor_verify.py spec.json source.md --log --write-back
```

1. 源材料实际可读且非空。
2. 至少一个条目真的定位到原文。
3. 覆盖率 ≥ 90%：分母是所有 claims 与所有 sources，**包含 AI 补充**。
4. 非 AI 补充的失败条数 = 0；任何失败都阻止交付，即使平均覆盖率很高。

核验器分别验证 `frames[].claims[].anchor` 和 `sources[].text`，检查指定位置与左邻否定词。AI 补充没有来源，不计入覆盖率分子，用灰底明确标注；过多补充同样不能通过闸门。

**退出 10 必须修复后重跑**。使用 `--write-back` 回填后再渲染，未核验项会标红。源文件或规格改变后，重新核验；旧 SHA-256 印记不能沿用。核验器和渲染器不共享定位实现。

机器匹配只说明引句存在，不证明含义支持。必须人工检查主体、因果、范围、否定与条件。`body` 中的每条事实都登记进 `claims`，不得在正文、探测答案或设计依据中藏入未经核验的新事实。

## 4. 不代做与交互

- 不替学习者回答 O 阶段，不模拟复述、不代为润色。
- 报告的复述、自测输入与漏帧/新增记录初始留空。
- 离线 HTML 提供自评标记、本地保存与 JSON 导出，不调用模型、不自动判读语义。
- 若学习者把复述发回对话，只指出“漏帧 / 新增”，引用来源；不输出改写后的代答。
- 可以先让用户预测术语或机制，不要在预测题前提前把答案泄露。

## 5. 可复现命令链

从技能根目录执行。所有输出路径都可显式指定；使用用户允许的工作目录。

```bash
# P1：输出 spec 骨架及 spec.flow-index.json；骨架不是完成品
python scripts/flow_plan.py source.md --topic "X" -o spec.json
# 读索引和原材料，确认切帧，人工完成 frames/sources/rationale。
# spec.flow-index.json 是源索引，不能拿来渲染。

# P3：按目标帧生成探测草稿，润色后把对象放进 spec.probes 数组
python scripts/lossy_perturb.py spec.json --target F2 --seed 7 -o probe.json

# P5 / P6：先校验，再核验回填，再正式渲染
python scripts/render_report.py spec.json --dry-run
python scripts/anchor_verify.py spec.json source.md --log --write-back
python scripts/render_report.py spec.json --out report.html

# P7：仅打印复习提案；默认 1/3/7/14/30 天，可用 --intervals 调整
python scripts/schedule.py plan --start 2026-10-13 --spec spec.json
python scripts/schedule.py stats --log spec.verification.jsonl
```

日期应换成用户当地的实际起始日。`schedule.py` 不建立系统提醒；只有用户明确要求时才使用环境中的提醒工具。台账统计反映核验结果，不是学习掌握度。

## 6. 自迭代与资源

改进必须来自实测问题，记录到 [CHANGELOG.md](CHANGELOG.md)。改 spec 结构时同步改 Schema 和渲染校验；改版式只动模板；修问题先补失败用例。

```bash
python tests/regression_suite.py  # 文档要求的 31 项：反幻觉门 9 / 注入防御 8 / 结构 9 / 一致性 5
python tests/extended_suite.py    # 额外边界回归
```

改过任何脚本后必须重跑，全部通过才收工。按文档实际敲完整命令链，不能只在脑中推演；检查可执行 HTML 用解析器或浏览器，不用文本搜索计数。完整交付与验证说明见 [README.md](README.md)，原始委托文档保存在 `docs/委托原文.md`。
