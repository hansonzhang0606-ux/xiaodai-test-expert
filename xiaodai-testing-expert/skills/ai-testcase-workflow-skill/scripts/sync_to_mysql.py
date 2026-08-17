#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
效贷测试专家 — 时间节省数据同步到 MySQL（WorkBuddy 版）

读取本地 JSONL 记录，幂等 upsert 到 MySQL 的 agent_time_tracking 表。
pymysql 已打包进本脚本同目录（scripts/pymysql/），无需 pip install，离线可用。

用法:
  python sync_to_mysql.py                 # 同步效贷业务线
  python sync_to_mysql.py --biz-line 效贷  # 指定业务线
  python sync_to_mysql.py --since 2026-08-17  # 只同步该日期及之后的记录
  python sync_to_mysql.py --dry-run       # 试运行，只看不写

数据源: ~/.workbuddy/data/time-tracking/{biz_line}/records.jsonl
配置:   ~/.workbuddy/data/time-tracking/{biz_line}/mysql_config.json
幂等:   唯一键 record_key = MD5(biz_line_code|employee|user_story|step_code|timestamp秒)
        INSERT ... ON DUPLICATE KEY UPDATE，重复同步不会产生重复数据。
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime

# 让脚本可独立运行：优先加载同目录打包的 pymysql（离线可用）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if os.path.isdir(os.path.join(SCRIPT_DIR, "pymysql")):
    sys.path.insert(0, SCRIPT_DIR)

try:
    import pymysql
    import pymysql.cursors
except ImportError:
    print("ERROR: pymysql 未打包进脚本目录。请确认 scripts/pymysql/ 存在。", file=sys.stderr)
    sys.exit(1)

# 业务线中文名 -> 编码（与 init_mysql.sql 注释一致）
BIZ_LINE_CODE_MAP = {
    "效贷": "XD",
    "泾渭云": "JWY",
    "效融": "XR",
    "小贷": "XXD",
    "智慧记+运营系统": "ZHJ",
    "AI进销存": "AIJXC",
    "智慧记零售": "ZHJLS",
}

HOME = os.path.expanduser("~")


def get_data_dir(biz_line):
    return os.path.join(HOME, ".workbuddy", "data", "time-tracking", biz_line)


def load_mysql_config(biz_line):
    """读取本地 MySQL 配置（机器本地，不进 Git）"""
    cfg_path = os.path.join(get_data_dir(biz_line), "mysql_config.json")
    if not os.path.exists(cfg_path):
        print(f"ERROR: 配置文件不存在: {cfg_path}", file=sys.stderr)
        print("请创建该文件，字段见 scripts/mysql_config.json.template", file=sys.stderr)
        sys.exit(1)
    with open(cfg_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_connection(cfg):
    return pymysql.connect(
        host=cfg.get("host", "127.0.0.1"),
        port=int(cfg.get("port", 3306)),
        user=cfg.get("user", "root"),
        password=cfg.get("password", ""),
        database=cfg.get("database", ""),
        charset=cfg.get("charset", "utf8mb4"),
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=10,
    )


def normalize_timestamp(ts):
    """把 ISO 时间戳归一化为 '%Y-%m-%d %H:%M:%S'（秒级，MySQL DATETIME）"""
    ts = ts or ""
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ts[:19].replace("T", " ") if ts else None


def compute_record_key(record, biz_line_code):
    """幂等唯一键 MD5(biz_line_code|employee|user_story|step_code|timestamp秒)"""
    ts_sec = normalize_timestamp(record.get("timestamp")) or ""
    key_str = "|".join([
        biz_line_code,
        record.get("employee", "") or "",
        record.get("user_story", "") or "",
        record.get("step_code", "") or "",
        ts_sec,
    ])
    return hashlib.md5(key_str.encode("utf-8")).hexdigest()


def read_jsonl_records(biz_line):
    """读取本地 JSONL 记录"""
    jsonl = os.path.join(get_data_dir(biz_line), "records.jsonl")
    if not os.path.exists(jsonl):
        return []
    records = []
    with open(jsonl, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def upsert_record(conn, table, record, biz_line_code):
    """幂等 upsert 一条记录（record_key 唯一键兜底）"""
    record_key = compute_record_key(record, biz_line_code)
    ts = normalize_timestamp(record.get("timestamp"))
    date_val = record.get("date", "") or (ts[:10] if ts else "")

    sql = f"""
        INSERT INTO {table}
            (record_key, timestamp, date, biz_line, biz_line_code, employee, user_story,
             step, step_code, time_saved_hours, time_saved_pd, total_hours, remark)
        VALUES (%(record_key)s, %(timestamp)s, %(date)s, %(biz_line)s, %(biz_line_code)s,
                %(employee)s, %(user_story)s, %(step)s, %(step_code)s,
                %(time_saved_hours)s, %(time_saved_pd)s, %(total_hours)s, %(remark)s)
        ON DUPLICATE KEY UPDATE
            timestamp=VALUES(timestamp), date=VALUES(date),
            time_saved_hours=VALUES(time_saved_hours),
            time_saved_pd=VALUES(time_saved_pd),
            total_hours=VALUES(total_hours), remark=VALUES(remark)
    """
    params = {
        "record_key": record_key,
        "timestamp": ts,
        "date": date_val,
        "biz_line": record.get("biz_line", "") or "效贷",
        "biz_line_code": biz_line_code,
        "employee": record.get("employee", ""),
        "user_story": record.get("user_story", ""),
        "step": record.get("step", ""),
        "step_code": record.get("step_code", ""),
        "time_saved_hours": float(record.get("time_saved_hours", 0)),
        "time_saved_pd": float(record.get("time_saved_pd", 0)),
        "total_hours": float(record.get("total_hours", 0)),
        "remark": record.get("remark", ""),
    }
    with conn.cursor() as cur:
        cur.execute(sql, params)


def main():
    parser = argparse.ArgumentParser(description="时间节省数据同步到 MySQL（WorkBuddy 版）")
    parser.add_argument("--biz-line", default="效贷", help="业务线（默认：效贷）")
    parser.add_argument("--since", default="", help="只同步该日期及之后的记录（YYYY-MM-DD）")
    parser.add_argument("--dry-run", action="store_true", help="试运行，只看不写")
    args = parser.parse_args()

    biz_line = args.biz_line
    biz_line_code = BIZ_LINE_CODE_MAP.get(biz_line, "XD")

    records = read_jsonl_records(biz_line)
    if args.since:
        records = [r for r in records if (r.get("date") or "") >= args.since]
    print("=" * 62)
    print(f"时间记录同步到 MySQL — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 62)
    print(f"业务线: {biz_line} ({biz_line_code})")
    print(f"本地记录: {len(records)} 条")

    if not records:
        print("✅ 没有待同步的记录。")
        return

    cfg = load_mysql_config(biz_line)
    table = cfg.get("table", "agent_time_tracking")

    if args.dry_run:
        print(f"\n🔍 试运行 — 将同步到 {cfg.get('host')}:{cfg.get('port')}/"
              f"{cfg.get('database')}.{table}:")
        for r in records:
            print(f"  {r.get('date')} | {r.get('employee')} | {r.get('step_code')} "
                  f"{r.get('step')} | {r.get('total_hours')}h")
        print(f"\n共 {len(records)} 条（未实际写入）")
        return

    conn = get_connection(cfg)
    print(f"✅ 已连接 MySQL: {cfg.get('host')}:{cfg.get('port')}/"
          f"{cfg.get('database')}.{table}")

    ok = 0
    fail = 0
    for r in records:
        try:
            upsert_record(conn, table, r, biz_line_code)
            ok += 1
            print(f"  ✅ {r.get('date')} | {r.get('employee')} | {r.get('step_code')} "
                  f"{r.get('step')} | {r.get('total_hours')}h")
        except Exception as e:
            fail += 1
            print(f"  ❌ {r.get('date')} | {r.get('employee')} | {r.get('step')} → {e}")

    conn.commit()
    conn.close()

    print("\n" + "=" * 62)
    print(f"同步完成: 成功 {ok} 条 / 失败 {fail} 条 / 合计 {len(records)} 条")
    print("=" * 62)

    if fail > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
