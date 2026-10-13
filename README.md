# 学习画布 · Learning Canvas

单文件交互式 HTML 学习报告生成工具包 —— 把一份材料锻造成**能证明你学会了**的报告，而不是又一份解释。

**版本 1.1.4** ｜ Python 3.10+ ｜ 核心流程零第三方依赖、零联网、零 API Key ｜ [MIT License](LICENSE)

---

## 一、这个项目解决什么问题

AI 让「解释一件事」变得极其廉价，于是出现了新的失败模式：

> 你读完一份漂亮的解释 → 每句话都懂 → 合上页面却讲不出来 → **你以为自己学会了**。

这叫**胜任错觉**。它的根源是「看懂」和「能讲出来」之间有鸿沟，而多数 AI 学习工具只优化
「讲得更好懂」，反而**加深**了错觉。

本项目的着力点不是「讲得好不好懂」，而是改**你怎么证明自己懂了**：

| 常见做法 | 本项目的做法 |
|---|---|
| 给一份完整解释让你读 | 先给**有损版本**，让你自己找出丢了什么 |
| 讲得越顺越好 | 逼你说出「少了它为什么就不成立」 |
| 帮你总结、代你复述 | **只标你漏了哪帧、新增了什么**，绝不代写 |
| 结论看起来合理就发布 | 每条断言必须能在源材料里**逐字定位**，否则不予交付 |

一句话：用「不可再压缩」定义理解，用「有损探测」测量理解，用「自己的话」暴露误解，
用「可验证锚点」防止幻觉。

---

## 二、主要功能

### 1. FLOW 学习循环（核心方法论）

**F**rames 知识帧 → **L**ossy Probe 有损探测 → **O**wn-Words 自己的话 → **W**alk-through 走查。
顺序不可跳过。

- **F 切帧**：把材料压成 3–5 个「删掉任一帧理解就会塌」的必要知识单元
- **L 探测**：确定性生成遗漏某一帧的压缩版，考察能否定位损失
- **O 留白**：报告里的复述区**保持空白**，脚本不代写、不预填、不自动判读语义
- **W 走查**：每条断言可点击跳转到源材料中的定位

### 2. 四道证据门（反幻觉）

`anchor_verify.py` 反复核验，四门全过才允许交付：

1. 源材料实际可读且非空
2. 至少一个条目真的定位到原文
3. 覆盖率 ≥ 90%（分母包含 AI 补充）
4. **非 AI 补充的失败条数 = 0**（即使平均覆盖率很高，任何失败都阻止交付）

未通过返回退出码 `10`，必须回退修复。

### 3. 单文件交互式报告

- **完全自包含**：CSS/JS 内联，无 CDN、无外部请求，断网可打开
- 可折叠知识帧、点击揭示自测、阅读进度条、来源徽标跳转
- 复述区支持本地保存与 JSON 导出；**不调用模型、不自动打分**
- `@media print` 友好：打印时自动展开折叠内容

### 4. 可复现的命令行工具链

五个纯标准库脚本，输入输出契约明确，全部支持 `--help`：

| 脚本 | 职责 |
|---|---|
| `flow_plan.py` | 建源索引 + 生成**待填写**的 spec 骨架 |
| `lossy_perturb.py` | 确定性生成遗漏指定帧的探测草稿 |
| `anchor_verify.py` | 独立实现的证据门（不复用渲染/规划代码） |
| `render_report.py` | spec → 单文件 HTML |
| `schedule.py` | 复习提案（`plan`）与核验台账统计（`stats`） |

### 5. 自带回归测试

31 项核心回归 + 16 项扩展边界回归，均可离线运行。另有一套 README 声明核验脚本，把本文件
当作待验证的声明集合逐条核对——路径是否存在、命令是否真能跑、数字是否对得上、退出码是否如实——
所以「README 写的」与「代码做的」不一致时会被测出来。

---

## 三、安装方法

### 需要什么

- **Python 3.10 或更高**（本交付包在 Python 3.13 上实测通过）
- 仅此而已：核心流程不联网、不需要 API Key、不需要 Node.js、不装任何第三方包

### 获取与运行

本包是**便携目录**，无需安装即可使用：

```bash
# 解压后进入包目录
cd learning-canvas

# 验证环境（无需任何依赖）
python scripts/render_report.py --help
```

如需读取 PDF 材料，再装可选的 PDF 依赖：

```bash
python -m pip install -r requirements-optional.txt   # 仅 pypdf>=5,<7
```

TXT / Markdown 与全部核心命令**只用标准库**。本包不会自行安装依赖、不修改系统 Python、
不写入用户配置。

### 让代理自动发现（可选）

要让支持技能机制的代理自动加载本技能，把整个 `learning-canvas` 目录交给它的技能加载
机制，或在对话中直接引用本目录的 `SKILL.md`。

本包**不替用户安装到任何位置**；具体安装路径取决于所用产品。仅使用命令行工具时，
完全不需要技能安装。

### 系统若只提供 python3

把下文所有 `python` 替换为 `python3`。

---

## 四、使用方法

### 快速体验（30 秒）

```bash
python scripts/anchor_verify.py assets/worked_example_https.json assets/worked_example_https_source.md --log --write-back
python scripts/render_report.py assets/worked_example_https.json --out demo.html
```

然后双击打开 `demo.html`。

> 这两条命令**不需要任何第三方包**。示例是教学用输入；真实使用时，由代理或你本人阅读
> 原文、切帧、填写 spec —— **脚本不会自动编造报告内容**。

### 完整流程（P1 → P7）

从包根目录执行：

```bash
# P1 建源索引，生成待填写骨架
python scripts/flow_plan.py source.md --topic "你的主题" -o spec.json

#   → 读 spec.flow-index.json 与原材料，人工完成 frames / sources / rationale
#   → spec.flow-index.json 是源索引，不能拿来渲染

# P3 生成有损探测草稿，润色后并入 spec 的 probes 数组
python scripts/lossy_perturb.py spec.json --target F2 --seed 7 -o probe.json

# P5 先校验内容规格
python scripts/render_report.py spec.json --dry-run

# P6 证据门核验并回填（未通过返回 10，必须修复后重跑）
python scripts/anchor_verify.py spec.json source.md --log --write-back

# P5 正式渲染；需要静态版加 --static
python scripts/render_report.py spec.json --out report.html

# P7 复习提案与台账统计
python scripts/schedule.py plan --start 2026-10-13 --spec spec.json
python scripts/schedule.py stats --log spec.verification.jsonl
```

### 参数与退出码

| 脚本 | 主要参数 | 产出 |
|---|---|---|
| `flow_plan.py` | `source --topic X -o spec.json`；`-o -` 走标准输出 | spec 骨架 + `.flow-index.json`；stdout 模式为 `{spec, index}` |
| `lossy_perturb.py` | `spec --target F2 --seed 7 -o probe.json` | 单个 probe 对象；**不修改原 spec** |
| `anchor_verify.py` | `spec source --log [路径] --write-back` | stdout JSON 结果；可回填 spec 并追加 JSONL 台账 |
| `render_report.py` | `spec --out report.html [--dry-run] [--static] [--template T]` | 单文件 HTML，或只校验 |
| `schedule.py` | `plan --start YYYY-MM-DD --spec spec [--out r.json] [--intervals ...]` | 可调整的复习提案，**不建立提醒** |
| `schedule.py` | `stats --log verify.jsonl` | 按主题汇总核验记录 |

**退出码**

| 码 | 含义 |
|---|---|
| `0` | 成功 |
| `2` | 输入或结构错误（如 spec 缺字段、文件不存在） |
| `3` | 模板占位符错误（缺少**或**多出）—— **只在真实渲染时检查** |
| `10` | 证据门未通过，必须修复后重跑 |

> `render_report.py --dry-run` 只校验 spec，**不加载模板**，因此不会返回 3。
> 要检查自定义模板，需要跑一次真实渲染。

### 自定义模板（进阶）

模板占位符使用 `@@NAME@@` 语法（共 12 个）。自定义模板必须与渲染器提供的键**完全一致**，
缺一个或多一个都会以退出码 `3` 拒绝渲染。

---

## 五、输入输出示例

以下输出均为**实际运行结果**，可直接复现。

### 示例 1：建源索引

```bash
$ python scripts/flow_plan.py assets/worked_example_https_source.md --topic "HTTPS" -o spec.json
{"spec": "spec.json", "index": "spec.flow-index.json", "status": "需人工完成切帧和断言；骨架不可直接渲染"}
```

**输出文件**：`spec.json`（待填写骨架）+ `spec.flow-index.json`（源索引，只用来查位置）。

> `status` 明确提示骨架**不可直接渲染** —— 直接喂渲染器会以退出码 2 拒绝。这是刻意的：
> 防止半成品被当成成品交付。

### 示例 2：有损探测草稿

```bash
$ python scripts/lossy_perturb.py spec.json --target F2 --seed 7 -o probe.json
```

`probe.json` 实际内容（节选）：

```json
{
  "id": "L1",
  "target": "F2",
  "kind": "drop",
  "prompt": "HTTPS 使用 TLS 保护浏览器与服务器之间传输的 HTTP 数据。 加密让传输中的数据难以被第三方直接读取。 ……这个压缩版遗漏了哪一个必要知识单元？遗漏会造成什么误解？",
  "answer": "遗漏 F2：完整性：发现路上的改动。",
  "explanation": "删去这一帧，只剩保密，会遗漏检测传输篡改这一保护目标。",
  "seed": 7
}
```

同一个 `--seed` 每次生成相同结果，保证「测的是理解而不是运气」。

### 示例 3：证据门核验

```bash
$ python scripts/anchor_verify.py assets/worked_example_https.json assets/worked_example_https_source.md
```

实际输出（节选）：

```json
{
  "passed": true,
  "coverage": 1.0,
  "total": 10,
  "verified": 10,
  "ai_only": 0,
  "failed": 0,
  "gates": {
    "source_readable": true,
    "at_least_one": true,
    "coverage_90": true,
    "zero_failed": true
  }
}
```

带 `--log --write-back` 时：结果追加到 `spec.verification.jsonl` 台账，并把未核验项回填进 spec
（渲染时标红），同时记录源材料与 spec 的 SHA-256。

### 示例 4：渲染报告

```bash
$ python scripts/render_report.py assets/worked_example_https.json --out demo.html
{"html": "...\\demo.html", "static": false}
```

> 该行 JSON 原样打印输出文件的**绝对路径**；上面的 `...` 是本文省略掉的目录前缀，不是程序输出内容。

**产物**：`demo.html`，25,334 字节单文件，实测外部 http(s) 引用为 **0**。

示例报告（HTTPS 主题）包含：

| 内容 | 实际数量 |
|---|---|
| 知识帧 | 4（传输保密 / 完整性 / 服务器认证 / 能力边界） |
| 来源锚点 | 5 条 |
| 有损探测 | 1 题 |
| 复述练习区 | 1 处（初始留空） |
| 应溯源条目 | 10（5 条来源 + 5 条断言），核验 10/10 |

### 示例 5：复习提案

```bash
$ python scripts/schedule.py plan --start 2026-10-13 --spec assets/worked_example_https.json
```

```json
{
  "topic": "HTTPS 保护了什么？",
  "start": "2026-10-13",
  "status": "proposal_only",
  "note": "这是可调整的复习提案，尚未建立提醒；这些间隔不是个体最优值。",
  "reviews": [
    { "date": "2026-10-14", "day_offset": 1,  "task": "先不看报告做有损探测与自己的话，再核对漏帧、新增和证据。" },
    { "date": "2026-10-16", "day_offset": 3,  "task": "…" },
    { "date": "2026-10-20", "day_offset": 7,  "task": "…" },
    { "date": "2026-10-27", "day_offset": 14, "task": "…" },
    { "date": "2026-11-12", "day_offset": 30, "task": "…" }
  ]
}
```

默认间隔为 1/3/7/14/30 天，可用 `--intervals` 调整。**只生成提案，不创建系统提醒。**

### 示例 6：完整流水线产物

`examples/full-pipeline/` 保存了从源材料到成品的全部真实产物：

```
spec.json                    填写完成的输入规格
spec.flow-index.json         源材料段落索引
probe.json                   有损探测
spec.verification.jsonl      核验台账
reviews.json                 复习提案
report.html                  最终报告（25,371 B）
report-static.html           静态降级版（21,765 B）
```

---

## 六、验证状态

本包自带可复跑的验证证据。**以下为实测结果：**

```bash
python tests/regression_suite.py    # 31 项核心回归
python tests/extended_suite.py      # 16 项扩展边界回归
python tests/readme_claims.py       # README 声明逐条核验（本身会跑上面两套，耗时较长）
```

| 项目 | 结果 |
|---|---|
| 核心回归 | **31 项全部通过**（反幻觉门 9 / 注入防御 8 / 结构完整性 9 / 声称一致性 5） |
| 扩展回归 | **16 项全部通过**（源材料变化、位置失真、覆盖率阈值、显式 AI 补充、编码、日志、练习留白等） |
| README 声明核验 | **全部通过**（路径存在性、`--help` 可执行、示例产物字节数、四类退出码、占位符与清单条目数） |
| 示例核验 | 10/10 条定位成功，覆盖率 100%，失败 0 |
| PDF 输入 | 3 项；未装 `reportlab` 时自动跳过（`skipped=3`，退出码仍为 0） |
| 浏览器检查 | 20 项通过，`errors: []`（见 `validation/18-browser-results.json`） |
| 打印检查 | 通过（`validation/19-print-check.txt`、`validation/previews/`） |
| 完整性清单 | `SHA256SUMS.json` 记录 62 个文件的 SHA-256 |

详细运行输出在 `validation/`；截图与打印样本在 `validation/previews/`。

**浏览器与打印检查属于开发验收**，需要 Node.js + Playwright 与 `pypdf`，**不是报告使用依赖**：

```bash
node tests/browser_smoke.cjs demo.html --out browser-check
python tests/print_check.py 打印PDF路径
```

`PLAYWRIGHT_CHROMIUM_EXECUTABLE` 可指向已有浏览器（不自动下载），`NODE_PATH` 可指向已有
Playwright 模块目录。

### 修改文件后

改了任何内容，文件 SHA-256 就会变化，`SHA256SUMS.json` 随之失效。请重新核验并更新清单 ——
哈希用于**发现内容变化**，不是防伪签名。

### 用 git 管理时注意换行符

清单按每个文件的**原始字节**计算。git 默认会对文本做 LF/CRLF 互转，一旦发生，克隆出来的
文件字节就变了，清单会**全部校验失败**。本包已用 `.gitattributes` 里的 `* -text` 关掉转换。

本项目的换行本身是混合的（一部分文件 CRLF、一部分 LF），所以不能用「统一成某一种」的办法解决 ——
统一任何一侧都会破坏另一侧文件的摘要。如果你把内容搬到别的仓库，记得带上这份 `.gitattributes`。

---

## 七、边界与限制

这些是**已知的真实边界**，不是免责声明：

- **锚点匹配不是语义正确性的证明**。脚本只证明「这个引句确实存在于源材料」，不证明它
  在语义上支持该断言。必须人工核对主体、因果、范围、否定与条件。
- **不会自动生成知识帧**。需要代理或作者真实阅读材料并填写内容规格；正文、探测答案与
  设计依据中不得藏入未经核验的新事实。
- **PDF 不含 OCR**。扫描件、加密件需先转换为可抽取文字的格式；PDF 的索引行号基于抽取文本。
- **离线报告不调用模型**。复述区只提供留白与自评标注，不自动判读语义、不自动打分。
- **本地保存取决于浏览器策略**。`localStorage` 在部分打开方式下不可用；重要练习请导出。
- **不代做 O 阶段**。不模拟复述、不代为润色；练习区初始留空。
- **复习间隔只是可调整提案**，不代表个体最优值；`schedule.py` 不创建系统提醒。
- **学习理论依据**见 `references/theory_map.md`；本文不把设计推断声称为普遍学习定律。

---

## 八、目录结构

```
learning-canvas/
├── README.md                    本文件
├── LICENSE                      MIT 许可证
├── SKILL.md                     技能定义与可复现命令链（代理读取的入口）
├── CHANGELOG.md                 逐版本变更与实测发现的问题
├── 验收说明.md                   交付验收结果与要求映射
├── SHA256SUMS.json              62 个文件的 SHA-256 清单
├── requirements-optional.txt    可选依赖（仅 PDF 用 pypdf）
├── .gitattributes               禁用 git 换行转换，保住清单按字节校验的前提
├── .gitignore                   Python 缓存、测试临时区与本地渲染产物
├── agents/openai.yaml           代理展示元数据
├── scripts/                     五个核心脚本 + common.py
├── assets/                      HTML 模板、Schema、HTTPS 示例与其源材料
├── references/                  六份方法论参考（FLOW/理论/核验/质量/检查点/先例）
├── examples/full-pipeline/      完整流水线真实产物
├── docs/委托原文.md              原始委托文档（按字节保留）
├── tests/                       31 核心 + 16 扩展 + README 声明核验 + PDF + 打印 + 浏览器检查
└── validation/                  18 项验收输出、截图与打印样本
```

---

## 九、出处

- HTTPS 示例依据：[MDN TLS 说明](https://developer.mozilla.org/en-US/docs/Web/Security/Defenses/Transport_Layer_Security)、
  [Chromium 连接安全说明](https://blog.chromium.org/2023/05/an-update-on-lock-icon.html)
- 学习理论来源：见 [references/theory_map.md](references/theory_map.md)
- 方法论与先例对比：见 [references/prior_art.md](references/prior_art.md)

---

## 十、许可

本项目以 [MIT License](LICENSE) 发布。

文中标注的第三方出处（MDN、Chromium Blog 等）仅作为事实来源引用，内容版权归各自作者所有；
本项目的说明文字与代码均为原创，不复制其受版权保护的表达。
