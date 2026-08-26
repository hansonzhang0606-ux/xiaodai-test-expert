# 时间追踪独立 Skill 抽取 — 任务概览

## 完成事项

把「效贷测试专家」v1.5.0 中的**测试人员时间节省追踪能力**抽取为独立、通用（多业务线）的 Skill，并打包为 zip，供嵌入智慧记测试团队的 Skill 套件。

## 交付物

| 文件 | 位置 |
|------|------|
| zip 包（主交付） | `D:\##AI转型\效贷测试专家-WorkBuddy\time-tracking-skill.zip` |
| 源码目录 | `D:\##AI转型\效贷测试专家-WorkBuddy\time-tracking-skill\` |

zip 解压后根目录为 `time-tracking-skill/`，含 33 个文件（SKILL.md、README.md、prompts/、config/、scripts/ 含打包的 pymysql）。

## 关键决策

1. **biz_line 完全可配置**：新增 `biz_line_helper.py` 统一解析（CLI 参数 → config `default_biz_line` → 空则报错），不静默猜测默认业务线。
2. **多业务线花名册**：`employee_id` → `biz_line_code`（数组），一名员工可属多条业务线；身份确认时由员工选择本次业务线。
3. **7 条业务线编码对照**：XD 效贷 / JWY 泾渭云 / XR 效融 / XXD 小贷 / ZHJ 智慧记+运营系统 / AIJXC AI进销存 / ZHJLS 智慧记零售。
4. **保留 v1.5.0 全部能力**：本地 JSONL / Excel / 腾讯文档 cloud 三种存储 + MySQL 幂等同步 + HTML 报告。
5. **默认值安全**：`default_biz_line` 留空、`storage_mode` 默认 `local`，`tencent_docs` 凭据清空——开箱即用且不会写错业务线。

## 变更文件清单

- 新增：`scripts/biz_line_helper.py`、`SKILL.md`、`README.md`
- 泛化：`record_time_saved.py`、`generate_time_analytics.py`、`sync_to_excel.py`、`sync_to_mysql.py`、`init_mysql_config.py`、`sync_task.bat`、`config_loader.py`
- 重写：`config/time_tracking_config.yaml`、`config/smartsheet_template.yaml`、`prompts/time_tracking.md`
- 花名册：MySQL `agent_team_roster` 表（人员由管理员直接维护，不再经 `team_roster.yaml`）
- 原样打包：`scripts/pymysql/`（纯 Python MySQL 驱动）

## 验证结果

- 7 个 Python 脚本语法检查通过
- 未配置 `default_biz_line` → 清晰报错退出
- `--biz-line 智慧记` → 记录成功、花名册校验通过、报告标题正确
- 测试数据已清理，配置已恢复默认值

## 后续事项

- 智慧记团队部署时需：① 设置 `default_biz_line: "智慧记"`；② 填写花名册（已预填）；③ 如需 MySQL 汇总则各机器跑 `init_mysql_config.py`
- 若智慧记团队也要「MySQL-only」（去掉腾讯文档依赖），需按原专家包 v5 口径再改一遍 `time_tracking.md`（本包仍保留 cloud 逻辑）
