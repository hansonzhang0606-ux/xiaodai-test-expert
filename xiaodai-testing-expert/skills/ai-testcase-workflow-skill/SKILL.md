---
name: ai-testcase-workflow-skill
description: |
  测试用例生成通用 Skill，支持从需求文档到测试用例入库的灵活流程。多项目复用、知识库驱动、AI核心推导、脚本辅助输出。

  支持 2 种执行模式：
  - 模式A（完整流程）：文档整理 → 评审 → 测试点 → 用例 → [可选落库]
  - 模式B（单步模式）：按需执行任意一步（整理/评审/测试点/用例/落库）

  ⚠️ 强制约束（最高优先级）：
  1. 每个阶段开始前，必须完整阅读对应 prompts/*.md 文档，禁止凭记忆执行
  2. ⛔ 禁止假设已读取 / 禁止简化 Todo / 禁止跳过步骤 / 禁止自行判断 / 禁止假设状态
  3. ⛔ 步骤①完成后不自动触发评审，必须等待用户指令
  4. ⛔ 步骤⑦在所有模式下都是可选的，用户说"入库"时才执行
  5. ⚠️ 进入任何主步骤时，第一步必须追加子流程 Todo（规划动作），禁止先执行操作再追加

  📖 详细执行规则在各 prompts/*.md 文件中，本文档只保留流程概览和核心约束。
---

# AI Testcase Workflow Skill

> **测试用例生成通用 Skill，从需求文档到测试用例入库的端到端流水线**

## ✨ 特性

- **多项目复用**：一套 Skill，每个项目独立 `.skill/` 配置和知识库
- **知识库驱动**：历史用例沉淀，精华库持续进化
- **AI 核心推导**：AI 分析需求、推导场景、细化用例，脚本辅助输出
- **灵活执行**：2 种模式适应不同场景

---

## 🎯 2 种执行模式

| 模式 | 适用场景 | 流程 |
|------|---------|------|
| **A 完整流程** | 新项目/新需求从零开始 | ①→②→③→④→⑤→⑥→[⑦可选] |
| **B 单步模式** | 按需执行任意一步（如已有评审后 XMind 直接生成用例） | 用户指定步骤→执行 |

> 💡 步骤①完成后**不自动触发评审** | 步骤⑦**可选**，用户说"入库"才执行

---

## 🔄 核心流程概览（7步）

```
① 文档整理 → ② 需求评审 → ③ 确认评审 → ④ 生成测试点 → ⑤ 评审XMind → ⑥ 生成用例 → [⑦入库知识库]
```

| 步骤 | 名称 | AI 参与 | 输入 | 输出 | 必读文档 | ⛔ 不读的风险 |
|------|------|---------|------|------|----------|-------------|
| ① | 文档整理 | 中 | 需求目录(源文件) | 整理版 MD + source/归档 | `prompts/document_consolidate.md` | 锚点格式错误、图片未分确定/不确定、增量识别失效、自动触发评审、流程图使用 Mermaid 而非步骤+缩进 |
| ② | 需求评审 | 高 | 整理版 MD + 精华库 | 评审报告 MD+JSON | `prompts/requirement_review.md` | 遗漏评审维度、JSON 格式错误、精华库未读取、评审了运维细节 |
| ③ | 确认评审 | - | - | - | - | 等待用户确认 |
| ④ | 生成测试点 | 高 | 整理版 MD+评审报告+精华库 | 测试点 JSON+XMind+报告 | `prompts/testpoint_generate.md` | 测试点格式错误、未去重、缺少处理决策解析、未生成测试点报告 |
| ⑤ | 评审XMind | - | - | {需求名}_测试点.xmind（用户直接在此文件上评审） | - | 用户人工评审 |
| ⑥ | 生成用例 | 高 | {需求名}_测试点.xmind + 整理版 MD | 测试用例 JSON+Excel + reviewed.json（仅模式A） | `prompts/testcase_refine.md` | 步骤编号错误、数据未实例化、步骤与预期不对应、Excel 格式错误 |
| ⑦ | 入库知识库 | 中 | 全部产出物 | 知识库更新 | `prompts/knowledge_base_archive.md` | 命名不规范、重复入库、未提炼精华、进化日志未更新 |

---

## 📁 目录结构

```
ai-testcase-workflow-skill/
├── config/defaults.yaml              # 公共默认配置
├── scripts/                          # Python 脚本
│   ├── convert_to_md.py              # 文档转换 (依赖: markitdown[all], pywin32)
│   ├── parse_xmind.py                # XMind 评审标记解析
│   ├── generate_xmind.py             # 测试点 JSON → XMind
│   ├── refine_testcases.py           # 用例细化
│   ├── generate_excel.py             # Excel 生成
│   ├── generate_review_report.py     # 评审报告生成
│   ├── config_loader.py              # 配置加载器
│   ├── record_time_saved.py          # 时间节省记录 (每步完成后调用)
│   ├── generate_time_analytics.py    # 时间节省分析报告生成
│   └── sync_to_excel.py              # Excel 集中存储同步
├── prompts/                          # AI 执行规则 (每步必读)
│   ├── document_consolidate.md       # ① 文档整理
│   ├── requirement_review.md         # ② 需求评审
│   ├── testpoint_generate.md         # ④ 测试点生成
│   ├── testcase_refine.md            # ⑥ 用例细化
│   ├── knowledge_base_archive.md     # ⑦ 入库知识库
│   └── time_tracking.md             # 时间节省追踪 (每步完成后)
├── templates/                        # 项目配置+知识库模板
├── SKILL.md                          # 本文档
└── README.md                         # 简介
```

---

## 🗂️ 多项目架构

```
ai-testcase-workflow-skill/     ← 通用 Skill
{项目A}/.skill/                 ← 项目A配置+知识库
{项目B}/.skill/                 ← 项目B配置+知识库
```

AI 自动识别项目：用户提供任意路径 → 向上查找 `.skill/` (最多3层) → 定位项目根目录

---

## 🆕 新项目初始化

**触发**：首次定位到项目，检查 `{项目根}/.skill/project.yaml` 是否存在

**流程**：
1. 创建 `.skill/` + `knowledge-base/` 目录结构
2. 复制模板文件 (project.yaml + 知识库模板)
3. 询问用户填写配置 (项目组/产品/模块路径)
4. 更新 project.yaml

**安全规则**：目录/文件已存在 → 跳过，不覆盖

---

## ⚠️ 强制约束（最高优先级）

### 1. 前置检查流程

用户触发任何操作时，必须先执行：

```
1. 项目根目录 → 已缓存直接使用 / 未缓存则定位(向上查找 .skill/ 最多3层)
2. 初始化检查 → 仅首次定位时执行
3. 模式识别 → 判断用户意图(A/B)
4. 执行操作 → 先阅读对应 prompts/*.md 文档
```

> ❌ 禁止每个步骤重复定位 | 禁止重复检查初始化 | 禁止整理后自动评审 | 禁止生成 Excel 后自动入库

### 2. 每阶段必读对应文档

| 步骤 | 必读文档 | ⛔ 不读的风险 |
|------|----------|-------------|
| ① 文档整理 | `prompts/document_consolidate.md` | 锚点格式错误、图片未分确定/不确定、增量识别失效、自动触发评审 |
| ② 需求评审 | `prompts/requirement_review.md` | 遗漏评审维度、JSON 格式错误、精华库未读取、评审了运维细节 |
| ④ 生成测试点 | `prompts/testpoint_generate.md` | 测试点格式错误、未去重、缺少处理决策解析、未生成测试点报告 |
| ⑥ 生成用例 | `prompts/testcase_refine.md` | 步骤编号错误、数据未实例化、步骤与预期不对应、Excel 格式错误 |
| ⑦ 入库知识库 | `prompts/knowledge_base_archive.md` | 命名不规范、重复入库、未提炼精华、进化日志未更新 |

> ❌ 禁止凭记忆执行 | 禁止跳过阅读 | 禁止假设规则内容

### 3. 层级 Todo 管理

| 层级 | 内容 | 编号 | 状态管理 |
|------|------|------|---------|
| 一级(主流程) | 7步流程(①~⑦) | 0,1,2... | 始终保留，不替换 |
| 二级(子流程) | 当前步骤详细子步骤 | N-1,N-2... | 进入时追加，完成时移除 |

**执行规则**：进入主步骤 N → 第一步追加完整二级 Todo → 逐项执行 → 完成后移除二级，标记一级 completed

> ❌ 禁止先执行操作再追加 Todo | 禁止替换一级 Todo | 禁止省略二级 Todo

### 4. ⛔ 禁止 AI 擅自决策

| 禁止项 | 说明 |
|--------|------|
| 禁止假设已读取 | 不假设前置步骤已完成，必须实际执行每步读取 |
| 禁止简化 Todo | Todo 清单必须完整，不可省略强制检查项 |
| 禁止跳过步骤 | 强制项不可跳过，必须逐项执行并标记状态 |
| 禁止自行判断 | AI 不可自行判断「不重要」「已完成」「无需执行」 |
| 禁止假设状态 | 标记「已完成」前必须实际执行该操作 |
| 禁止修改路径 | 路径字符串原样复制，禁止添加/删除空格符号 |

---

## 📊 产出物清单

| 步骤 | 产出物 |
|------|--------|
| ① | `{目录名}_整理版_v{version}.md` + `source/.整理索引.yaml` + `source/` 归档 |
| ② | `*_评审报告.md` + `*_评审数据.json` |
| ④ | `*_测试点.xmind` + `*_测试点.json` + `*_测试点生成报告.md` |
| ⑤ | `*_测试点.xmind`（用户直接在此文件上评审，覆盖原文件） |
| ⑥ | `*_测试用例.json` → `*_测试用例.xlsx` + `*_测试点_reviewed.json`（仅模式A） |
| ⑦ | 知识库 4 个目录更新 + INDEX.md + EVOLUTION_LOG.md |

---

## 🔗 步骤依赖关系

```
① 文档整理 ──→ ② 需求评审 ──→ ③ 确认 ──→ ④ 生成测试点 ──→ ⑤ 评审XMind
                                                                │
⑦ 入库 ←── ⑥ 生成用例 ←────────────────────────────────────────┘
```

---

## 🎮 用户指令识别

| 用户指令 | AI 判断 | 必读文档 | ⛔ 不读的风险 |
|---------|--------|----------|-------------|
| "整理" / "处理这些文档" | 执行① | `prompts/document_consolidate.md` | 锚点格式错误、图片未分确定/不确定、自动触发评审、流程图使用 Mermaid 而非步骤+缩进 |
| "评审" / "评审这个需求" | 执行② | `prompts/requirement_review.md` | 遗漏评审维度、JSON 格式错误、评审了运维细节 |
| "生成测试点" / "转 XMind" | 执行④ | `prompts/testpoint_generate.md` | 测试点格式错误、未去重、缺少处理决策解析 |
| "生成用例" / "生成 Excel" | 执行⑥ | `prompts/testcase_refine.md` | 步骤编号错误、数据未实例化、Excel 格式错误 |
| "入库" / "归档" | 执行⑦ | `prompts/knowledge_base_archive.md` | 命名不规范、重复入库、未提炼精华 |

---

## 🔧 脚本使用

> 💡 **AI 在对话中按步骤直接调用各脚本**，依赖缺失时 Python 会提示安装命令。

### 单独脚本

```bash
python scripts/convert_to_md.py <文件> [--archive]  # 文档转换
python scripts/parse_xmind.py <xmind> -o <json>     # XMind 解析
python scripts/generate_xmind.py --input <json> --output <xmind>  # 测试点 JSON → XMind
python scripts/refine_testcases.py <json> [参数]    # 用例细化
python scripts/generate_excel.py <json> [参数]      # Excel 生成
python scripts/generate_review_report.py --input <json> --output <md>  # 评审报告
```

> ⚠️ 步骤⑦入库知识库**由 AI 按 `prompts/knowledge_base_archive.md` 规则手动操作**（复制文件、更新进化日志、提炼精华库），不调用脚本。

### 时间节省追踪脚本

```bash
# 每步完成后记录时间节省（v3: 统一存储为小时，支持二次确认）
python scripts/record_time_saved.py \
  --employee "{员工}" --user-story "{故事}" \
  --step "{步骤}" --step-code "{代码}" \
  --hours {小时数} --biz-line "{业务线}" [--remark "{备注}"]

# 也可用人天输入，脚本自动换算为小时存储
python scripts/record_time_saved.py \
  --employee "{员工}" --user-story "{故事}" \
  --step "{步骤}" --step-code "{代码}" \
  --person-days {人天数} --biz-line "{业务线}"

# 生成HTML分析报告（以人天为主展示）
python scripts/generate_time_analytics.py --biz-line "{业务线}"

# 指定 Excel 数据源生成报告
python scripts/generate_time_analytics.py --biz-line "{业务线}" --input <Excel路径>

# 导出CSV
python scripts/generate_time_analytics.py --biz-line "{业务线}" --format csv

# Excel 集中存储操作
python scripts/sync_to_excel.py --init --excel <路径>                        # 初始化模板
python scripts/sync_to_excel.py --sync-all --jsonl <JSONL> --excel <路径>    # 全量同步
python scripts/sync_to_excel.py --read --excel <路径>                        # 读取为JSON
```

> 详见 `prompts/time_tracking.md`

---

## ⚙️ 项目配置

**位置**: `{项目根}/.skill/project.yaml`

```yaml
project:
  name: "项目名称"
defaults:
  team: "项目组"         # ⭐ 必填
  product: "产品名称"    # ⭐ 必填
  modulePath: "模块路径" # ⭐ 必填
  caseLevel: "P1"
knowledge_base:
  relative_path: ".skill/knowledge-base"
```

---

## 📚 知识库结构

```
knowledge-base/
├── INDEX.md                    # 索引
├── EVOLUTION_LOG.md            # 进化日志(只在⑦入库时读写)
├── patterns/                   # 精华库(参与②④⑥生成)
│   ├── common_root_causes.md   # 高频根因 Top 10
│   ├── common_omissions.md     # 高频遗漏 Top 10
│   └── improvement_patterns.md # 改进措施 Top 10
├── requirements/               # 历史需求
├── review-reports/             # 历史评审
├── tech-solutions/             # 历史技术方案
└── testcases/                  # 历史测试点/用例
```

**精华库 vs 进化日志**：
- 精华库：固定 Top 10，参与生成流程，≤ 300 Token
- 进化日志：历史流水账，只在⑦入库时读写

---

## 📖 详细文档索引

各步骤的详细执行规则、JSON 格式规范、Todo 清单定义、评审维度等详细内容，请参考对应 prompts 文件：

| 文件 | 内容 | 行数 |
|------|------|------|
| [prompts/document_consolidate.md](prompts/document_consolidate.md) | ① 文档整理：12步流程、锚点溯源格式、图片解析规则（步骤+缩进流程图）、增量识别 | ~550 |
| [prompts/requirement_review.md](prompts/requirement_review.md) | ② 需求评审：13步流程、6维评审、JSON 格式规范、精华库读取 | ~650 |
| [prompts/testpoint_generate.md](prompts/testpoint_generate.md) | ④ 测试点生成：10步流程、5大来源、去重合并、报告结构 | ~1100 |
| [prompts/testcase_refine.md](prompts/testcase_refine.md) | ⑥ 用例细化：10步流程、细化规则、Excel 格式、用例分类 | ~350 |
| [prompts/knowledge_base_archive.md](prompts/knowledge_base_archive.md) | ⑦ 入库知识库：12步流程、差异对比、精华提炼、进化指标 | ~700 |
| [prompts/time_tracking.md](prompts/time_tracking.md) | 时间节省追踪v3：二次确认+统一小时存储+人天展示+Excel集中存储 | ~280 |

---

## 💡 使用示例

### 示例1：完整流程

```
用户：帮我处理 D:\项目A\2026\Q2\需求目录 下的需求文档

AI：
1. 定位项目 → 执行前置检查 → 创建 7 步 Todo（按 prompts 定义的一级主流程）
2. 阅读 prompts/document_consolidate.md → 按文档定义的 Todo 清单执行① → 输出整理版 MD → 等待用户校验
3. 用户确认 → 阅读 prompts/requirement_review.md → 按文档定义的 Todo 清单执行② → 输出评审报告
4. 用户确认 → 阅读 prompts/testpoint_generate.md → 按文档定义的 Todo 清单执行④ → 输出 XMind
5. 用户评审 XMind → 阅读 prompts/testcase_refine.md → 按文档定义的 Todo 清单执行⑥ → 输出 Excel
6. 用户确认入库 → 阅读 prompts/knowledge_base_archive.md → 按文档定义的 Todo 清单执行⑦ → 完成
```

### 示例2：单步模式

```
用户：我有评审后的 XMind，帮我生成用例

AI：
1. 定位项目 → 识别模式B（单步执行⑥） → 创建 Todo（一级：⑥生成用例、⑦可选入库）
2. 阅读 prompts/testcase_refine.md → 按文档定义的 Todo 清单执行⑥ → 输出 Excel
3. 用户确认 → 流程结束 (如需入库请说"入库")
```

---

*版本：v2.4*
*更新日期：2026-06-23*
*更新：简化执行模式 3→2（原模式B合并到模式B单步），知识库默认轻量路径（仅读精华库），用户说"结合历史"时走完整路径*
