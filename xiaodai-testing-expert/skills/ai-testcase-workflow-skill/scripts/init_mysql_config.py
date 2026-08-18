#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
初始化 MySQL 本地配置文件（单业务线）

此脚本不打包任何真实凭据，安装专家包后由测试人员在自己电脑上运行一次，
生成本机专用的 mysql_config.json，供后续 sync_to_mysql.py 定时同步使用。

用法:
  python init_mysql_config.py --biz-line 效贷
  python init_mysql_config.py --biz-line 效贷 --password "xxx" --no-interactive
"""

import argparse
import json
import os
import sys

HOME = os.path.expanduser("~")

# 效贷业务线默认数据库配置（仅默认连接信息，密码绝不写入任何文件）
DEFAULT_DB_CONFIG = {
    "效贷": {
        "host": "172.20.148.36",
        "port": 3306,
        "user": "root",
        "database": "auto_efficiency_platform_dev",
        "table": "agent_time_tracking",
    }
}


def get_data_dir(biz_line):
    return os.path.join(HOME, ".workbuddy", "data", "time-tracking", biz_line)


def prompt_with_default(label, default, hide=False):
    """交互式提示，带默认值；hide=True 时不回显输入"""
    if hide:
        try:
            import getpass
            value = getpass.getpass(f"{label} [{default}]: ").strip()
        except Exception:
            value = input(f"{label} [{default}]: ").strip()
    else:
        value = input(f"{label} [{default}]: ").strip()
    return value if value else default


def main():
    parser = argparse.ArgumentParser(description="初始化 MySQL 本地配置文件")
    parser.add_argument("--biz-line", default="效贷", help="业务线（默认：效贷）")
    parser.add_argument("--host", help="MySQL 主机")
    parser.add_argument("--port", type=int, help="MySQL 端口")
    parser.add_argument("--user", help="MySQL 用户名")
    parser.add_argument("--password", default=None, help="MySQL 密码（命令行直接传不安全，仅 CI/自动化场景使用）")
    parser.add_argument("--database", help="数据库名")
    parser.add_argument("--table", help="表名")
    parser.add_argument("--no-interactive", action="store_true", help="非交互模式，必须命令行传齐所有参数")
    parser.add_argument("--force", action="store_true", help="覆盖已存在的配置文件")
    args = parser.parse_args()

    biz_line = args.biz_line
    defaults = DEFAULT_DB_CONFIG.get(biz_line, {
        "host": "127.0.0.1",
        "port": 3306,
        "user": "root",
        "database": "your_database",
        "table": "agent_time_tracking",
    })

    data_dir = get_data_dir(biz_line)
    os.makedirs(data_dir, exist_ok=True)
    cfg_path = os.path.join(data_dir, "mysql_config.json")

    if os.path.exists(cfg_path) and not args.force:
        print(f"⚠️  配置文件已存在: {cfg_path}", file=sys.stderr)
        print("   如需重新生成，请删除该文件或加 --force 参数覆盖。", file=sys.stderr)
        sys.exit(1)

    if args.no_interactive:
        if not args.password:
            print("ERROR: --no-interactive 模式下必须提供 --password", file=sys.stderr)
            sys.exit(1)
        config = {
            "host": args.host or defaults["host"],
            "port": args.port or defaults["port"],
            "user": args.user or defaults["user"],
            "password": args.password,
            "database": args.database or defaults["database"],
            "table": args.table or defaults["table"],
            "charset": "utf8mb4",
        }
    else:
        print("=" * 60)
        print(f"初始化 {biz_line} 业务线 MySQL 本地配置")
        print("=" * 60)
        print(f"配置文件将保存到: {cfg_path}")
        print("提示：密码仅保存在本机，不会随专家包上传或分发。\n")

        config = {
            "host": prompt_with_default("主机", args.host or defaults["host"]),
            "port": int(prompt_with_default("端口", str(args.port or defaults["port"]))),
            "user": prompt_with_default("用户名", args.user or defaults["user"]),
            "password": prompt_with_default("密码", args.password or "", hide=True),
            "database": prompt_with_default("数据库", args.database or defaults["database"]),
            "table": prompt_with_default("表名", args.table or defaults["table"]),
            "charset": "utf8mb4",
        }

    if not config["password"]:
        print("ERROR: 密码不能为空", file=sys.stderr)
        sys.exit(1)

    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 配置文件已生成: {cfg_path}")
    print("   后续可直接运行: python sync_to_mysql.py --biz-line 效贷")


if __name__ == "__main__":
    main()
