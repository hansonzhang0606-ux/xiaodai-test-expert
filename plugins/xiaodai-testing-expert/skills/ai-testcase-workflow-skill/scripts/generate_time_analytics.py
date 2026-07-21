#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
时间节省分析报告生成脚本
读取 records.jsonl，生成 HTML 可视化分析报告。

用法:
  python generate_time_analytics.py                          # 生成效贷业务线报告
  python generate_time_analytics.py --biz-line "效贷"        # 指定业务线
  python generate_time_analytics.py --output report.html     # 指定输出路径
  python generate_time_analytics.py --format csv             # 输出 CSV 格式

输出:
  - HTML 报告（默认）：包含总览、按员工/故事/步骤三个维度的统计图表
  - CSV 报告：原始数据 + 汇总表
"""

import argparse
import json
import os
import sys
from datetime import datetime
from collections import defaultdict


HOURS_PER_PD = 8.0
STEP_ORDER = ["01", "02", "04", "06", "07"]
STEP_NAMES = {
    "01": "文档整理",
    "02": "需求评审",
    "04": "生成测试点",
    "06": "生成用例",
    "07": "入库知识库",
}


def get_data_dir(biz_line: str) -> str:
    home = os.path.expanduser("~")
    return os.path.join(home, ".workbuddy", "data", "time-tracking", biz_line)


def get_records_path(biz_line: str) -> str:
    return os.path.join(get_data_dir(biz_line), "records.jsonl")


def load_records(biz_line: str, input_path: str = None) -> list:
    """加载所有记录

    Args:
        biz_line: 业务线名称（用于本地 records.jsonl）
        input_path: 外部数据文件路径（JSON 或 Excel），优先使用
    """
    # 优先从外部文件读取
    if input_path and os.path.exists(input_path):
        # Excel 文件
        if input_path.lower().endswith((".xlsx", ".xls")):
            try:
                # 尝试导入同目录的 sync_to_excel
                script_dir = os.path.dirname(os.path.abspath(__file__))
                if script_dir not in sys.path:
                    sys.path.insert(0, script_dir)
                from sync_to_excel import read_excel_to_json
                records = read_excel_to_json(input_path)
                print(f"从 Excel 读取 {len(records)} 条记录: {input_path}", file=sys.stderr)
                return records
            except ImportError:
                print(f"错误: 无法导入 sync_to_excel 模块，请确保在同一目录", file=sys.stderr)
                return []

        # JSON 文件
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "records" in data:
            return data["records"]
        else:
            return [data]

    # 从本地 records.jsonl 读取
    path = get_records_path(biz_line)
    if not os.path.exists(path):
        return []
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return records


def generate_csv(records: list, biz_line: str, output_path: str):
    """生成 CSV 报告"""
    import csv
    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "时间", "日期", "业务线", "员工", "用户故事",
            "步骤", "步骤代码", "节省小时", "节省人天", "备注"
        ])
        for r in records:
            writer.writerow([
                r.get("timestamp", ""),
                r.get("date", ""),
                r.get("biz_line", ""),
                r.get("employee", ""),
                r.get("user_story", ""),
                r.get("step", ""),
                r.get("step_code", ""),
                r.get("time_saved_hours", 0),
                r.get("time_saved_pd", 0),
                r.get("remark", ""),
            ])
    print(f"CSV 报告已生成: {output_path}")


def generate_html(records: list, biz_line: str, output_path: str):
    """生成 HTML 可视化报告"""

    # ---- 统计计算 ----
    total_records = len(records)
    # 使用 total_hours 字段（v2记录），否则回退到 time_saved_hours
    total_hours = sum(r.get("total_hours", r.get("time_saved_hours", 0)) for r in records)
    total_pd = sum(r.get("time_saved_pd", 0) for r in records)

    # 按员工统计
    by_employee = defaultdict(lambda: {"hours": 0, "pd": 0, "count": 0, "stories": set()})
    for r in records:
        emp = r.get("employee", "未知")
        by_employee[emp]["hours"] += r.get("time_saved_hours", 0)
        by_employee[emp]["pd"] += r.get("time_saved_pd", 0)
        by_employee[emp]["count"] += 1
        by_employee[emp]["stories"].add(r.get("user_story", ""))

    # 按用户故事统计
    by_story = defaultdict(lambda: {"hours": 0, "pd": 0, "count": 0, "employees": set(), "steps": set()})
    for r in records:
        story = r.get("user_story", "未知")
        by_story[story]["hours"] += r.get("time_saved_hours", 0)
        by_story[story]["pd"] += r.get("time_saved_pd", 0)
        by_story[story]["count"] += 1
        by_story[story]["employees"].add(r.get("employee", ""))
        by_story[story]["steps"].add(r.get("step", ""))

    # 按步骤统计
    by_step = defaultdict(lambda: {"hours": 0, "pd": 0, "count": 0, "employees": set()})
    for r in records:
        step = r.get("step", "未知")
        by_step[step]["hours"] += r.get("time_saved_hours", 0)
        by_step[step]["pd"] += r.get("time_saved_pd", 0)
        by_step[step]["count"] += 1
        by_step[step]["employees"].add(r.get("employee", ""))

    # 按日期统计趋势
    by_date = defaultdict(lambda: {"hours": 0, "pd": 0, "count": 0})
    for r in records:
        date = r.get("date", "未知")
        by_date[date]["hours"] += r.get("time_saved_hours", 0)
        by_date[date]["pd"] += r.get("time_saved_pd", 0)
        by_date[date]["count"] += 1

    # 员工 x 步骤 交叉表（v3: 以人天为单位）
    cross_data = defaultdict(lambda: defaultdict(float))
    employees_sorted = sorted(by_employee.keys())
    steps_sorted = sorted(by_step.keys(), key=lambda s: STEP_ORDER.index(next((c for c, n in STEP_NAMES.items() if n == s), "99")) if any(c for c, n in STEP_NAMES.items() if n == s) else 99)
    for r in records:
        cross_data[r.get("employee", "未知")][r.get("step", "未知")] += r.get("total_hours", r.get("time_saved_hours", 0)) / HOURS_PER_PD

    # ---- 最大值用于柱状图比例 ----
    max_emp_hours = max((v["hours"] for v in by_employee.values()), default=1)
    max_step_hours = max((v["hours"] for v in by_step.values()), default=1)
    max_story_hours = max((v["hours"] for v in by_story.values()), default=1)
    max_date_hours = max((v["hours"] for v in by_date.values()), default=1)

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # ---- HTML 生成 ----
    html_parts = []
    html_parts.append(f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{biz_line}业务线 - 时间节省分析报告</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif; background: #f5f7fa; color: #333; padding: 24px; }}
  .header {{ text-align: center; margin-bottom: 32px; }}
  .header h1 {{ font-size: 28px; color: #1a1a2e; margin-bottom: 8px; }}
  .header .subtitle {{ font-size: 14px; color: #888; }}
  .summary-cards {{ display: flex; gap: 16px; margin-bottom: 32px; flex-wrap: wrap; }}
  .card {{ background: #fff; border-radius: 12px; padding: 24px; flex: 1; min-width: 200px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
  .card .label {{ font-size: 13px; color: #888; margin-bottom: 8px; }}
  .card .value {{ font-size: 32px; font-weight: 700; }}
  .card .unit {{ font-size: 14px; color: #aaa; margin-left: 4px; }}
  .card.green .value {{ color: #00a870; }}
  .card.blue .value {{ color: #1890ff; }}
  .card.orange .value {{ color: #fa8c16; }}
  .card.purple .value {{ color: #722ed1; }}
  .section {{ background: #fff; border-radius: 12px; padding: 24px; margin-bottom: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
  .section h2 {{ font-size: 18px; color: #1a1a2e; margin-bottom: 16px; border-left: 4px solid #00a870; padding-left: 12px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
  th {{ background: #fafafa; text-align: left; padding: 10px 12px; border-bottom: 2px solid #f0f0f0; font-weight: 600; color: #555; }}
  td {{ padding: 10px 12px; border-bottom: 1px solid #f0f0f0; }}
  tr:hover td {{ background: #fafafa; }}
  .bar-container {{ display: inline-block; width: 200px; height: 20px; background: #f0f0f0; border-radius: 10px; overflow: hidden; vertical-align: middle; margin-right: 8px; }}
  .bar {{ height: 100%; border-radius: 10px; transition: width 0.5s ease; }}
  .bar.green {{ background: linear-gradient(90deg, #00a870, #36cfc9); }}
  .bar.blue {{ background: linear-gradient(90deg, #1890ff, #69b1ff); }}
  .bar.orange {{ background: linear-gradient(90deg, #fa8c16, #ffc069); }}
  .bar.purple {{ background: linear-gradient(90deg, #722ed1, #9254de); }}
  .number {{ font-weight: 600; color: #1a1a2e; }}
  .tag {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; margin: 1px; }}
  .tag.g {{ background: #f6ffed; color: #52c41a; border: 1px solid #b7eb8f; }}
  .tag.b {{ background: #e6f7ff; color: #1890ff; border: 1px solid #91d5ff; }}
  .tag.o {{ background: #fff7e6; color: #fa8c16; border: 1px solid #ffd591; }}
  .empty {{ text-align: center; padding: 48px; color: #999; font-size: 16px; }}
  .footer {{ text-align: center; margin-top: 32px; color: #aaa; font-size: 12px; }}
  .cross-table th, .cross-table td {{ text-align: center; font-size: 13px; }}
  .cross-table th:first-child, .cross-table td:first-child {{ text-align: left; }}
</style>
</head>
<body>

<div class="header">
  <h1>{biz_line}业务线 · 测试智能助手时间节省分析</h1>
  <div class="subtitle">报告生成时间：{now} | 数据来源：records.jsonl</div>
</div>
""")

    # ---- 概览卡片（v3: 人天为主展示）----
    unique_employees = len(by_employee)
    unique_stories = len(by_story)
    total_pd_from_hours = total_hours / HOURS_PER_PD
    html_parts.append(f"""
<div class="summary-cards">
  <div class="card green">
    <div class="label">累计节省时间</div>
    <div class="value">{total_pd_from_hours:.1f}<span class="unit">人天</span></div>
  </div>
  <div class="card blue">
    <div class="label">折合小时</div>
    <div class="value">{total_hours:.1f}<span class="unit">小时</span></div>
  </div>
  <div class="card orange">
    <div class="label">记录总数</div>
    <div class="value">{total_records}<span class="unit">条</span></div>
  </div>
  <div class="card purple">
    <div class="label">参与员工 / 覆盖故事</div>
    <div class="value">{unique_employees}<span class="unit">人</span> / {unique_stories}<span class="unit">个故事</span></div>
  </div>
</div>
""")

    if total_records == 0:
        html_parts.append('<div class="empty">暂无时间节省记录数据<br><br>请在完成工作流步骤后记录时间节省数据。</div>')
    else:

        # ---- 按员工统计 ----
        html_parts.append("""
<div class="section">
  <h2>按员工统计</h2>
  <table>
    <thead>
      <tr>
        <th>员工</th>
        <th>节省时间</th>
        <th>分布</th>
        <th>记录数</th>
        <th>参与故事数</th>
      </tr>
    </thead>
    <tbody>
""")
        for emp in sorted(by_employee.keys(), key=lambda e: by_employee[e]["hours"], reverse=True):
            v = by_employee[emp]
            bar_width = int(v["hours"] / max_emp_hours * 100) if max_emp_hours > 0 else 0
            html_parts.append(f"""
      <tr>
        <td class="number">{emp}</td>
        <td>{v['pd']:.1f} 人天 ({v['hours']:.1f} 小时)</td>
        <td><span class="bar-container"><span class="bar green" style="width: {bar_width}%"></span></span></td>
        <td>{v['count']}</td>
        <td>{len(v['stories'])}</td>
      </tr>
""")
        html_parts.append("""
    </tbody>
  </table>
</div>
""")

        # ---- 按步骤统计 ----
        html_parts.append("""
<div class="section">
  <h2>按工作流步骤统计</h2>
  <table>
    <thead>
      <tr>
        <th>步骤</th>
        <th>节省时间</th>
        <th>分布</th>
        <th>记录数</th>
        <th>参与员工数</th>
      </tr>
    </thead>
    <tbody>
""")
        step_order_sorted = sorted(by_step.keys(), key=lambda s: STEP_ORDER.index(next((c for c, n in STEP_NAMES.items() if n == s), "99")) if any(c for c, n in STEP_NAMES.items() if n == s) else 99)
        for step in step_order_sorted:
            v = by_step[step]
            bar_width = int(v["hours"] / max_step_hours * 100) if max_step_hours > 0 else 0
            html_parts.append(f"""
      <tr>
        <td class="number">{step}</td>
        <td>{v['pd']:.1f} 人天 ({v['hours']:.1f} 小时)</td>
        <td><span class="bar-container"><span class="bar blue" style="width: {bar_width}%"></span></span></td>
        <td>{v['count']}</td>
        <td>{len(v['employees'])}</td>
      </tr>
""")
        html_parts.append("""
    </tbody>
  </table>
</div>
""")

        # ---- 按用户故事统计 ----
        html_parts.append("""
<div class="section">
  <h2>按用户故事统计</h2>
  <table>
    <thead>
      <tr>
        <th>用户故事</th>
        <th>节省时间</th>
        <th>分布</th>
        <th>记录数</th>
        <th>参与员工</th>
        <th>覆盖步骤</th>
      </tr>
    </thead>
    <tbody>
""")
        for story in sorted(by_story.keys(), key=lambda s: by_story[s]["hours"], reverse=True):
            v = by_story[story]
            bar_width = int(v["hours"] / max_story_hours * 100) if max_story_hours > 0 else 0
            emp_tags = " ".join(f'<span class="tag b">{e}</span>' for e in sorted(v["employees"]))
            step_tags = " ".join(f'<span class="tag o">{s}</span>' for s in sorted(v["steps"]))
            html_parts.append(f"""
      <tr>
        <td class="number">{story}</td>
        <td>{v['pd']:.1f} 人天 ({v['hours']:.1f} 小时)</td>
        <td><span class="bar-container"><span class="bar orange" style="width: {bar_width}%"></span></span></td>
        <td>{v['count']}</td>
        <td>{emp_tags}</td>
        <td>{step_tags}</td>
      </tr>
""")
        html_parts.append("""
    </tbody>
  </table>
</div>
""")

        # ---- 按日期趋势 ----
        html_parts.append("""
<div class="section">
  <h2>按日期趋势</h2>
  <table>
    <thead>
      <tr>
        <th>日期</th>
        <th>节省时间</th>
        <th>分布</th>
        <th>记录数</th>
      </tr>
    </thead>
    <tbody>
""")
        for date in sorted(by_date.keys()):
            v = by_date[date]
            bar_width = int(v["hours"] / max_date_hours * 100) if max_date_hours > 0 else 0
            html_parts.append(f"""
      <tr>
        <td class="number">{date}</td>
        <td>{v['pd']:.1f} 人天 ({v['hours']:.1f} 小时)</td>
        <td><span class="bar-container"><span class="bar purple" style="width: {bar_width}%"></span></span></td>
        <td>{v['count']}</td>
      </tr>
""")
        html_parts.append("""
    </tbody>
  </table>
</div>
""")

        # ---- 员工 x 步骤 交叉表 ----
        html_parts.append("""
<div class="section">
  <h2>员工 x 步骤 交叉分析（单位：人天）</h2>
  <table class="cross-table">
    <thead>
      <tr>
        <th>员工</th>
""")
        for step in steps_sorted:
            html_parts.append(f"        <th>{step}</th>\n")
        html_parts.append("        <th>合计</th>\n      </tr>\n    </thead>\n    <tbody>\n")

        for emp in employees_sorted:
            row_total = sum(cross_data[emp].values())
            html_parts.append(f"      <tr>\n        <td class='number'>{emp}</td>\n")
            for step in steps_sorted:
                val = cross_data[emp].get(step, 0)
                html_parts.append(f"        <td>{val:.1f}</td>\n" if val > 0 else "        <td>-</td>\n")
            html_parts.append(f"        <td class='number'>{row_total:.1f}</td>\n      </tr>\n")
        html_parts.append("""    </tbody>
  </table>
</div>
""")

    # ---- Footer ----
    html_parts.append(f"""
<div class="footer">
  效贷测试专家 · 时间节省分析报告 | 由 generate_time_analytics.py 自动生成 | {now}
</div>
</body>
</html>
""")

    html_content = "\n".join(html_parts)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"HTML 分析报告已生成: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="生成时间节省分析报告 v2")
    parser.add_argument("--biz-line", default="效贷", help="业务线（默认：效贷）")
    parser.add_argument("--input", default="", help="外部 JSON 数据文件路径（云端同步数据），优先使用")
    parser.add_argument("--output", default="", help="输出文件路径（默认自动生成）")
    parser.add_argument("--format", choices=["html", "csv"], default="html", help="输出格式（默认：html）")

    args = parser.parse_args()

    records = load_records(args.biz_line, args.input if args.input else None)

    data_source = args.input if args.input else get_records_path(args.biz_line)

    if not records:
        print(f"暂无 {args.biz_line} 业务线的时间节省记录数据。")
        print(f"数据来源: {data_source}")
        # 仍然生成一个空报告
        if not args.output:
            data_dir = get_data_dir(args.biz_line)
            if args.format == "csv":
                args.output = os.path.join(data_dir, f"time_analytics_{args.biz_line}.csv")
            else:
                args.output = os.path.join(data_dir, f"time_analytics_{args.biz_line}.html")
        if args.format == "csv":
            generate_csv(records, args.biz_line, args.output)
        else:
            generate_html(records, args.biz_line, args.output)
        return

    if not args.output:
        data_dir = get_data_dir(args.biz_line)
        if args.format == "csv":
            args.output = os.path.join(data_dir, f"time_analytics_{args.biz_line}.csv")
        else:
            args.output = os.path.join(data_dir, f"time_analytics_{args.biz_line}.html")

    if args.format == "csv":
        generate_csv(records, args.biz_line, args.output)
    else:
        generate_html(records, args.biz_line, args.output)

    # 打印详细摘要
    total_hours = sum(r.get("total_hours", r.get("time_saved_hours", 0)) for r in records)
    total_pd = sum(r.get("time_saved_pd", 0) for r in records)
    unique_emps = set(r.get("employee", "") for r in records)
    unique_stories = set(r.get("user_story", "") for r in records)

    print(f"\n{'='*50}")
    print(f"📊 {args.biz_line}业务线时间节省统计")
    print(f"{'='*50}")
    print(f"   数据来源: {data_source}")
    print(f"   记录数: {len(records)} 条")
    print(f"   累计节省: {total_pd:.1f} 人天（{total_hours:.1f} 小时）")
    print(f"   参与员工: {len(unique_emps)} 人 ({', '.join(sorted(unique_emps))})")
    print(f"   覆盖故事: {len(unique_stories)} 个")

    # 按员工摘要
    by_emp = defaultdict(float)
    for r in records:
        by_emp[r.get("employee", "")] += r.get("total_hours", r.get("time_saved_hours", 0))
    print(f"\n   按员工分布:")
    for emp in sorted(by_emp.keys(), key=lambda e: by_emp[e], reverse=True):
        print(f"     {emp}: {by_emp[emp]/HOURS_PER_PD:.1f} 人天（{by_emp[emp]:.1f} 小时）")

    # 按步骤摘要
    by_step_summary = defaultdict(float)
    for r in records:
        by_step_summary[r.get("step", "")] += r.get("total_hours", r.get("time_saved_hours", 0))
    print(f"\n   按步骤分布:")
    for step in STEP_NAMES.values():
        if step in by_step_summary:
            print(f"     {step}: {by_step_summary[step]/HOURS_PER_PD:.1f} 人天（{by_step_summary[step]:.1f} 小时）")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
