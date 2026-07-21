# 数据归集说明

## 目录结构

每位测试人员的数据存储在独立子目录中：

```
data/
├── data_README.md          ← 本文件
├── 吴香康/
│   └── records.jsonl       ← 吴香康的时间节省记录
├── 周峰/
│   └── records.jsonl       ← 周峰的时间节省记录
└── 何甜/
    └── records.jsonl       ← 何甜的时间节省记录
```

## 数据格式

每行一个 JSON 记录，字段如下：

```json
{
  "date": "2026-07-21",
  "employee": "吴香康",
  "user_story": "用户故事描述",
  "step": "文档整理",
  "step_code": "doc_consolidate",
  "time_saved_hours": 3.0,
  "biz_line": "效贷",
  "remark": "备注信息",
  "recorded_at": "2026-07-21T16:30:00"
}
```

## 使用方式

### 测试人员推送数据

完成工作流步骤后，专家会自动将数据写入本地 JSONL。测试人员可通过以下命令推送：

```bash
cd <本地专家数据目录>
git add data/<姓名>/records.jsonl
git commit -m "update time records"
git push
```

### 管理员合并数据

管理员拉取所有人员数据后，可使用分析脚本生成汇总报告：

```bash
python scripts/generate_time_analytics.py --biz-line "效贷" --input data/all_records.json
```

## 注意事项

- `time_saved_hours` 统一以**小时**为单位存储
- 报告展示时自动换算为**人天**（1人天 = 8小时）
- 每条记录需经过**二次确认**后才会写入
- 数据仅限效贷业务线内部使用
