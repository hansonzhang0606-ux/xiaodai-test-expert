#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
初始化 MySQL 本地配置文件（多业务线通用）

此脚本不打包任何真实凭据，安装专家包后由测试人员在自己电脑上运行一次，
生成本机专用的 mysql_config.json，供后续 sync_to_mysql.py 定时同步使用。

支持业务线：效贷、泾渭云、小贷、智慧记零售、效融、AI进销存、智慧记+运营系统等。
所有业务线默认共用同一套 MySQL 连接（按 biz_line 字段区分），也可通过参数覆盖。

用法:
  # 交互模式（推荐首次使用）
  python init_mysql_config.py --biz-line 效贷

  # 非交互模式（AI 自动调用）
  python init_mysql_config.py --biz-line 效贷 --password "xxx" --no-interactive --employee "张三"

  # 自动检测模式（AI 会话启动时调用）：配置已存在则跳过，不存在则按默认生成
  python init_mysql_config.py --biz-line 效贷 --auto --password "xxx" --no-interactive
  # 模板模式（v1.5.3，AI 自动生成全空配置模板并生成 mysql_config.notes.md 备注说明，
  # 测试人员按备注填全部字段或找管理员获取，不在对话中索要密码）：
  python init_mysql_config.py --biz-line 效贷 --template --no-interactive --quiet
"""

import argparse
import json
import os
import sys

HOME = os.path.expanduser("~")

# 业务线中文名 -> 编码（与 sync_to_mysql.py 保持一致）
BIZ_LINE_CODE_MAP = {
    "效贷": "XD",
    "泾渭云": "JWY",
    "效融": "XR",
    "小贷": "XXD",
    "智慧记+运营系统": "ZHJ",
    "AI进销存": "AIJXC",
    "智慧记零售": "ZHJLS",
}

# 默认数据库配置：所有业务线默认共用同一套数据库连接，通过 biz_line 字段区分
# 管理员可修改此处为各业务线独立数据库
DEFAULT_DB_CONFIG = {
    "host": "172.20.148.36",
    "port": 3306,
    "user": "root",
    "database": "auto_efficiency_platform_dev",
    "table": "agent_time_tracking",
}


def get_data_dir(biz_line):
    """生成本业务线的本地数据目录"""
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


def ensure_data_dir(biz_line):
    """确保数据目录存在，返回目录路径"""
    data_dir = get_data_dir(biz_line)
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def build_config(args, defaults):
    """根据命令行参数和默认值构造配置字典"""
    return {
        "host": args.host or defaults["host"],
        "port": int(args.port or defaults["port"]),
        "user": args.user or defaults["user"],
        "password": args.password or "",
        "database": args.database or defaults["database"],
        "table": args.table or defaults["table"],
        "charset": "utf8mb4",
        "biz_line": args.biz_line,
        "biz_line_code": BIZ_LINE_CODE_MAP.get(args.biz_line, args.biz_line),
    }


def write_config(cfg_path, config):
    """写配置文件到本机"""
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def print_machine_result(status, message, cfg_path="", biz_line=""):
    """输出机器可读的结果（AI 可解析）"""
    result = {
        "status": status,  # ok / skipped / error
        "message": message,
        "config_path": cfg_path,
        "biz_line": biz_line,
        "biz_line_code": BIZ_LINE_CODE_MAP.get(biz_line, biz_line) if biz_line else "",
    }
    print(json.dumps(result, ensure_ascii=False))


def build_config_notes(biz_line):
    """生成 mysql_config.notes.md 内容：逐字段说明取值来源，测试人员按此填写或找管理员获取。"""
    return f"""# MySQL 配置填写说明（mysql_config.json）

本文件由 AI 自动生成，所有字段初始为空。请按下方说明逐条填写，
不清楚的字段**找管理员获取**（不要自己猜，也不要发到群里 / 提交 Git）。
填写完成后，回到对话回复「已填好」即可继续。

| 字段 | 含义 | 填写说明 / 获取方式 |
|------|------|--------------------|
| host | MySQL 服务器地址 | 找管理员获取（如 172.20.148.36） |
| port | 端口 | 通常 3306 |
| user | 用户名 | 找管理员获取（如 root） |
| password | 密码 | 管理员单独告知，**仅填在本机文件，不要外传** |
| database | 数据库名 | 找管理员获取（如 auto_efficiency_platform_dev） |
| table | 表名 | 时间记录表：agent_time_tracking；花名册表：agent_team_roster |
| charset | 字符集 | 填 utf8mb4 |
| biz_line | 业务线中文名 | 如 效贷 / 智慧记+运营系统 / AI进销存 / 智慧记零售 |
| biz_line_code | 业务线编码 | 如 XD / ZHJ / AIJXC / ZHJLS（与 biz_line 对应，找管理员确认） |

> 当前业务线：{biz_line}。agent_team_roster 与 agent_time_tracking 共用同一库，连接信息相同。
"""

def main():
    parser = argparse.ArgumentParser(description="初始化 MySQL 本地配置文件（多业务线通用）")
    parser.add_argument("--biz-line", default="效贷", help="业务线（默认：效贷）")
    parser.add_argument("--biz-line-code", help="业务线编码（默认自动映射）")
    parser.add_argument("--host", help="MySQL 主机")
    parser.add_argument("--port", type=int, help="MySQL 端口")
    parser.add_argument("--user", help="MySQL 用户名")
    parser.add_argument("--password", default=None, help="MySQL 密码（命令行直接传不安全，仅 CI/自动化场景使用）")
    parser.add_argument("--database", help="数据库名")
    parser.add_argument("--table", help="表名")
    parser.add_argument("--employee", help="当前使用者姓名（仅用于日志/标识，不写入配置）")
    parser.add_argument("--no-interactive", action="store_true", help="非交互模式，必须命令行传齐所有参数")
    parser.add_argument("--auto", action="store_true",
                        help="自动模式：配置已存在则直接跳过（退出码0），不存在则生成")
    parser.add_argument("--force", action="store_true", help="覆盖已存在的配置文件")
    parser.add_argument("--template", action="store_true", help="生成配置模板：全部字段留空（host/port/user/password/database/table/charset/biz_line/biz_line_code 均为空）并生成 mysql_config.notes.md 备注说明；测试人员按备注填或找管理员获取（AI 自动生成，不在对话中索要密码，代码不含任何凭据）")
    parser.add_argument("--quiet", action="store_true", help="静默模式，只输出机器可读 JSON")
    args = parser.parse_args()

    biz_line = args.biz_line
    data_dir = ensure_data_dir(biz_line)
    cfg_path = os.path.join(data_dir, "mysql_config.json")

    # 自动模式：已存在则跳过
    if args.auto and os.path.exists(cfg_path) and not args.force:
        msg = f"配置文件已存在: {cfg_path}，无需重复初始化。"
        if args.quiet:
            print_machine_result("skipped", msg, cfg_path=cfg_path, biz_line=biz_line)
        else:
            print(f"✅ {msg}")
        return 0

    # 普通模式：已存在则提示，但 --force 可覆盖
    if os.path.exists(cfg_path) and not args.force:
        msg = f"配置文件已存在: {cfg_path}。如需重新生成，请删除该文件或加 --force 参数覆盖。"
        if args.quiet:
            print_machine_result("skipped", msg, cfg_path=cfg_path, biz_line=biz_line)
        else:
            print(f"⚠️  {msg}", file=sys.stderr)
        return 0  # 退出码 0，避免 AI 调用时误判为失败

    # 模板模式（v1.5.3）：生成全空配置模板 + 备注说明文件，AI 自动调用，不在对话中索要密码
    if args.template:
        config = {
            "host": "",
            "port": "",
            "user": "",
            "password": "",
            "database": "",
            "table": "",
            "charset": "",
            "biz_line": "",
            "biz_line_code": "",
        }
        write_config(cfg_path, config)
        notes_path = os.path.join(os.path.dirname(cfg_path), "mysql_config.notes.md")
        with open(notes_path, "w", encoding="utf-8") as nf:
            nf.write(build_config_notes(biz_line))
        msg = f"配置模板已生成(请按 mysql_config.notes.md 备注填写全部字段): {cfg_path}"
        if args.quiet:
            print_machine_result("ok", msg, cfg_path=cfg_path, biz_line=biz_line)
        else:
            print(f"✅ {msg}")
        return 0

    # 构造配置
    config = build_config(args, DEFAULT_DB_CONFIG)

    # 非交互模式：必须提供密码
    if args.no_interactive:
        if not config["password"]:
            msg = "ERROR: --no-interactive 模式下必须提供 --password"
            if args.quiet:
                print_machine_result("error", msg, cfg_path=cfg_path, biz_line=biz_line)
            else:
                print(msg, file=sys.stderr)
            return 1
    else:
        # 交互模式
        print("=" * 60)
        print(f"初始化 {biz_line} 业务线 MySQL 本地配置")
        print("=" * 60)
        print(f"配置文件将保存到: {cfg_path}")
        print(f"业务线编码: {config['biz_line_code']}")
        if args.employee:
            print(f"当前使用者: {args.employee}")
        print("提示：密码仅保存在本机，不会随专家包上传或分发。\n")

        config["host"] = prompt_with_default("主机", config["host"])
        config["port"] = int(prompt_with_default("端口", str(config["port"])))
        config["user"] = prompt_with_default("用户名", config["user"])
        config["password"] = prompt_with_default("密码", config["password"], hide=True)
        config["database"] = prompt_with_default("数据库", config["database"])
        config["table"] = prompt_with_default("表名", config["table"])

    if not config["password"]:
        msg = "ERROR: 密码不能为空"
        if args.quiet:
            print_machine_result("error", msg, cfg_path=cfg_path, biz_line=biz_line)
        else:
            print(msg, file=sys.stderr)
        return 1

    write_config(cfg_path, config)

    msg = f"配置文件已生成: {cfg_path}"
    if args.quiet:
        print_machine_result("ok", msg, cfg_path=cfg_path, biz_line=biz_line)
    else:
        print(f"\n✅ {msg}")
        print("   后续可直接运行: python sync_to_mysql.py --biz-line " + biz_line)
        if args.employee:
            print(f"   员工: {args.employee}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
