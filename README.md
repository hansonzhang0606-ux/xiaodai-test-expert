# 效贷测试专家 - WorkBuddy 团队市场

## 简介

本仓库是效贷业务线功能测试专家的 WorkBuddy 团队级私有市场，提供一键安装能力。

## 安装方式

在 WorkBuddy 中添加团队市场仓库：

```
仓库地址：https://github.com/hansonzhang0606-ux/xiaodai-test-expert
```

添加后即可在专家市场页面看到「效贷测试专家」，点击安装即可使用。

## 专家版本

- **版本**：v1.5.2
- **内置 Skill**：ai-testcase-workflow-skill（7 步测试用例流水线）
- **身份验证**：会话启动时**实时查询 MySQL `agent_team_roster` 表**做精确匹配（覆盖 7 条业务线：效贷 XD / 泾渭云 JWY / 小贷 XR / 小贷 XXD / 智慧记 ZHJ / AI 进销存 AIJXC / 智慧记零售 ZHJLS）
- **MySQL 初始化**：首次使用由 AI 自动完成（`init_mysql_config.py --auto`），测试人员无需手动执行 CMD
- **时间节省统计**：数据同步至共享 MySQL 库 `agent_time_tracking`，查看统计时生成 HTML 报告并本地展示（已移除腾讯文档依赖）
- **文件前缀**：各步骤产出文件统一添加步骤数字前缀（1/2/4/6），便于识别文件归属步骤

## 功能概览

| 步骤 | 功能 | 说明 |
|------|------|------|
| 1 | 文档整理 | 多格式文档转换为 Markdown（本地目录或 Confluence 页面） |
| 2 | 需求评审 | 6 维度评审报告 |
| 3 | 确认评审 | 评审结论确认 |
| 4 | 生成测试点 | 测试点 + XMind 导出 |
| 5 | 评审 XMind | XMind 解析与评审 |
| 6 | 生成用例 | Excel 用例 + JSON |
| 7 | 入库知识库 | 经验沉淀归档（可选） |

## 身份验证与权限

- 会话启动时，AI 先检查本机 MySQL 配置，再**实时查询 `agent_team_roster` 表**获取在职人员名单，对用户输入姓名做精确匹配。
- 仅花名册内**在职**人员可使用；匹配失败直接终止服务，不提供 fallback 选项。
- 花名册由管理员维护 `team_roster.yaml`（输入源），通过 `sync_roster_to_mysql.py` 幂等同步到 MySQL，多副本 / 多机器部署下始终最新。

## 时间节省追踪

每完成一个工作流步骤后，专家会自动收集时间节省数据：

- 二次确认机制确保数据准确
- 统一以小时为单位存储，报告以人天为主展示（1 人天 = 8 小时）
- 数据经每日定时任务幂等 upsert 到共享 MySQL 表 `agent_time_tracking`（内置 pymysql 驱动，离线可用）
- 查看统计时从 MySQL 读取全量数据生成 HTML 报告并本地展示

## 数据归集

各测试人员的工时数据集中存储在共享 MySQL 库（业务线按 `biz_line_code` 区分：XD / JWY / XR / XXD / ZHJ / AIJXC / ZHJLS），管理员可随时拉取合并生成汇总报告。

## 版本历史

- **v1.5.2**：身份识别从读 `team_roster.yaml` 改为实时查 MySQL `agent_team_roster`；新增 `load_roster.py` / `sync_roster_to_mysql.py`，花名册多副本始终最新。
- **v1.5.1**：会话启动自动检查并初始化 MySQL 本地配置（AI 自动调用 `init_mysql_config.py`，测试人员无需手动 CMD）。
- **v1.5.0**：时间节省数据同步 MySQL（本地 JSONL 经定时任务幂等 upsert 到共享表），查看统计改为从 MySQL 读取生成报告，移除腾讯文档依赖。
- **v1.4.4**：自动识别查看者角色（测试人员个人视角 / 管理员业务线全量），HTML 报告内置 JS 筛选面板。

## 管理员

- **仓库所有者**：hansonzhang0606-ux
- **业务线**：效贷
