# -*- coding: utf-8 -*-
"""
效贷测试专家 - 版本号同步自检脚本（自动探测路径版）
用法：
  python check_version_sync.py                  # 只扫本地（工作区 + marketplace 副本 + docs + zip）
  python check_version_sync.py --github         # 本地 + 远程 GitHub 双镜像对比（需 GITHUB_PAT）
  python check_version_sync.py --json           # 输出 JSON 汇总（供 CI/脚本解析）
  python check_version_sync.py --set 1.6.2      # 报告期望版本号（与各位置比对）
  python check_version_sync.py --workspace <dir> # 显式指定工作区/仓库根目录（覆盖自动探测）
  python check_version_sync.py --market <dir>   # 显式指定 marketplace 副本目录（覆盖自动探测）

原理：把"当前版本号"应从哪些文件/字段读取列成清单，逐项提取版本号并分组比对。
路径自动探测（无需改常量，其他电脑可直接复用）：
  - 工作区/仓库根：脚本位于 <base>/scripts/ 下 → base=上一级；脚本位于 <base>/ 下 → base=脚本目录。
    以是否存在 xiaodai-testing-expert/ 镜像目录为准。
  - marketplace 副本：默认 ~/.workbuddy/plugins/marketplaces（不存在则跳过副本组）。
退出码：0=全部一致；1=存在不一致（缺文件/缺字段/版本不同）。
"""
import argparse
import base64
import json
import os
import re
import sys
import zipfile
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------
# 路径自动探测
# ---------------------------------------------------------------

def detect_base():
    """自动探测工作区/仓库根目录。
    规则：脚本在 <base>/scripts/ 下 → base=上一级；脚本在 <base>/ 下 → base=脚本所在目录。
    以 base 下存在 xiaodai-testing-expert/ 目录为判定标志。"""
    script_dir = Path(__file__).resolve().parent
    # 场景1：脚本位于 <base>/scripts/ 下（GitHub 仓库克隆布局）
    if script_dir.name == 'scripts':
        cand = script_dir.parent
        if (cand / 'xiaodai-testing-expert').is_dir():
            return cand
    # 场景2：脚本位于 <base>/ 下（本地工作区布局）
    cand = script_dir
    if (cand / 'xiaodai-testing-expert').is_dir():
        return cand
    return None


def detect_market():
    """自动探测 marketplace 副本目录：~/.workbuddy/plugins/marketplaces"""
    cand = Path.home() / '.workbuddy' / 'plugins' / 'marketplaces'
    return cand if cand.is_dir() else None


# ---------------------------------------------------------------
# 版本号提取器：每种文件类型一个函数，返回 (版本号, 说明) 或 None
# ---------------------------------------------------------------

def _read(path, encoding='utf-8'):
    with open(path, encoding=encoding) as f:
        return f.read()


def agent_version(path):
    """agent.md：frontmatter description 中最后一条 v1.x.y 版本条目（agent 体系固定 v1 开头，
    排除正文提到的 skill 层 v5.x / 其他版本号干扰）"""
    c = _read(path)
    m = re.search(r'description:\s*"(.*?)"\n', c, re.S)
    if not m:
        return None
    desc = m.group(1)
    vers = re.findall(r'v(1\.\d+\.\d+)\s*[:：]', desc)
    return vers[-1] if vers else None


def plugin_version(path):
    """plugin.json：version 字段"""
    d = json.loads(_read(path))
    return d.get('version')


def readme_version(path):
    """README.md：『版本』：vX.Y.Z 行"""
    c = _read(path)
    m = re.search(r'\*\*版本\*\*\s*[:：]\s*v?(\d+\.\d+(?:\.\d+)?)', c)
    return m.group(1) if m else None


def doc_version(path):
    """手册：头部 版本：vX.Y.Z 行"""
    c = _read(path)
    m = re.search(r'\*\*版本\*\*\s*[:：]\s*v?(\d+\.\d+(?:\.\d+)?)', c)
    return m.group(1) if m else None


def prompt_version(path):
    """prompts：末尾硬指令段 'vX.Y.Z 强制' 标注"""
    c = _read(path)
    m = re.search(r'v(\d+\.\d+(?:\.\d+)?)\s*强制', c)
    return m.group(1) if m else None


def zip_skill_version(path):
    """time-tracking-skill.zip：v5.x 版本号（skill 独立体系）。
    优先取 prompts/time_tracking.md（权威版本来源），其次 README.md；取最大版本号"""
    z = zipfile.ZipFile(path)
    order = ['prompts/time_tracking.md', 'README.md', 'SKILL.md']
    for target in order:
        for n in z.namelist():
            if n.endswith(target):
                c = z.read(n).decode('utf-8', errors='ignore')
                vers = re.findall(r'v(5\.\d+)\b', c)
                if vers:
                    # 取最大版本（文件里可能有旧版本历史引用，如"v5.3 → v5.4"）
                    return max(vers, key=lambda s: [int(x) for x in s.split('.')])
    return None


# ---------------------------------------------------------------
# 位置清单（动态布局识别）
# ---------------------------------------------------------------

SUBS = ['experts/plugins/xiaodai-testing-expert', 'my-experts/plugins/xiaodai-testing-expert',
        'xiaodai-test-expert-marketplace/plugins/xiaodai-testing-expert',
        'xiaodai-test-expert-marketplace/xiaodai-testing-expert']
PROMPTS = ['document_consolidate', 'knowledge_base_archive', 'requirement_review',
           'testcase_refine', 'testpoint_generate']
DOCS = ['效贷功能测试专家-测试人员使用指导手册.md', '效贷功能测试专家-管理员指导手册.md']


def build_manifest(base, market):
    """返回 [(组名, 位置说明, 版本提取器, 路径)]
    布局自适应：本地工作区布局（base/agent.md、base/skills/）与
    GitHub 仓库克隆布局（base/plugins/xiaodai-testing-expert/、base/xiaodai-testing-expert/）均可。"""
    base = Path(base)
    m = []
    mk = lambda g, label, fn, p: m.append((g, label, fn, str(p)))

    # 识别镜像位置：本地工作区/仓库共用 xiaodai-testing-expert/，仓库额外有 plugins/xiaodai-testing-expert/
    mirrors = []
    if (base / 'xiaodai-testing-expert').is_dir():
        mirrors.append(base / 'xiaodai-testing-expert')
    if (base / 'plugins' / 'xiaodai-testing-expert').is_dir():
        mirrors.append(base / 'plugins' / 'xiaodai-testing-expert')

    # A. agent 组
    if (base / 'agent.md').is_file():
        mk('A.agent', '工作区根 agent.md', agent_version, base / 'agent.md')
    for i, mir in enumerate(mirrors):
        tag = '镜像' if i == 0 else '镜像2(plugins)'
        mk('A.agent', tag + ' agents', agent_version, mir / 'agents' / 'xiaodai-testing-expert.md')
    if market:
        for sub in SUBS:
            mk('A.agent', '副本 ' + sub, agent_version,
               Path(market) / sub / 'agents' / 'xiaodai-testing-expert.md')

    # B. plugin 组
    for i, mir in enumerate(mirrors):
        tag = '镜像' if i == 0 else '镜像2(plugins)'
        mk('B.plugin', tag + ' plugin.json', plugin_version, mir / '.codebuddy-plugin' / 'plugin.json')
    if market:
        for sub in SUBS:
            mk('B.plugin', '副本 ' + sub, plugin_version,
               Path(market) / sub / '.codebuddy-plugin' / 'plugin.json')

    # C. README 组
    if (base / 'README.md').is_file():
        mk('C.readme', '工作区根 README', readme_version, base / 'README.md')
    for i, mir in enumerate(mirrors):
        tag = '镜像' if i == 0 else '镜像2(plugins)'
        mk('C.readme', tag + ' README', readme_version, mir / 'README.md')

    # D. docs 组（base/docs/ 为仓库克隆布局；marketplace 副本为本地布局）
    # 仅当手册文件实际存在时才添加（工作区布局的 docs/ 可能只有 images/，无手册）
    if (base / 'docs').is_dir():
        for doc in DOCS:
            p = base / 'docs' / doc
            if p.is_file():
                mk('D.docs', 'base/docs/' + doc, doc_version, p)
    if market:
        for sub in ['my-experts', 'xiaodai-test-expert-marketplace']:
            for doc in DOCS:
                mk('D.docs', '副本 docs/' + sub + '/' + doc, doc_version,
                   Path(market) / sub / 'docs' / doc)

    # E. prompts 组
    prompt_bases = []
    if (base / 'skills' / 'ai-testcase-workflow-skill').is_dir():
        prompt_bases.append(('工作区', base / 'skills' / 'ai-testcase-workflow-skill'))
    for i, mir in enumerate(mirrors):
        tag = '镜像' if i == 0 else '镜像2(plugins)'
        prompt_bases.append((tag, mir / 'skills' / 'ai-testcase-workflow-skill'))
    for tag, pb in prompt_bases:
        for pr in PROMPTS:
            mk('E.prompts', tag + ' prompts/' + pr, prompt_version, pb / 'prompts' / (pr + '.md'))

    # F. skill/zip 组（独立 v5.x 体系，只报告不参与比对）
    if (base / 'time-tracking-skill.zip').is_file():
        mk('F.zip', 'time-tracking-skill.zip', zip_skill_version, base / 'time-tracking-skill.zip')
    return m


# ---------------------------------------------------------------
# GitHub 远程镜像（可选）
# ---------------------------------------------------------------

def gh_get(url):
    pat = os.environ.get('GITHUB_PAT', '')
    req = urllib.request.Request(url, headers={
        'Authorization': 'Bearer ' + pat,
        'Accept': 'application/vnd.github+json',
    })
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode('utf-8'))


def gh_file_version(repo, path, extractor):
    """从 GitHub 拉文件内容并用本地提取器取版本号（路径需 URL 编码）"""
    import urllib.parse
    url = 'https://api.github.com/repos/%s/contents/%s?ref=main' % (
        repo, urllib.parse.quote(path, safe='/'))
    d = gh_get(url)
    raw = base64.b64decode(d['content'])
    import tempfile
    suffix = os.path.splitext(path)[1] or '.tmp'
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False, mode='wb') as f:
        f.write(raw)
        tmp = f.name
    try:
        return extractor(tmp)
    finally:
        os.unlink(tmp)


# ---------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--github', action='store_true', help='对比 GitHub 双镜像（需 GITHUB_PAT）')
    ap.add_argument('--json', action='store_true', help='输出 JSON 汇总')
    ap.add_argument('--set', metavar='X.Y.Z', help='期望版本号，与各位置比对')
    ap.add_argument('--workspace', metavar='DIR', help='显式指定工作区/仓库根目录（覆盖自动探测）')
    ap.add_argument('--market', metavar='DIR', help='显式指定 marketplace 副本目录（覆盖自动探测）')
    args = ap.parse_args()

    base = Path(args.workspace) if args.workspace else detect_base()
    if args.market:
        market = Path(args.market)
        if not market.is_dir():
            print('WARNING: 指定 --market 目录不存在: %s（跳过副本组）' % market)
            market = None
    else:
        market = detect_market()
    if base is None:
        print('ERROR: 无法自动探测工作区根目录（未找到 xiaodai-testing-expert/ 镜像目录）')
        print('       请用 --workspace <dir> 显式指定，或把脚本放在 <base>/scripts/ 或 <base>/ 下运行')
        sys.exit(2)
    print('工作区/仓库根:', base)
    print('marketplace 副本:', market if market else '(未找到，跳过副本组)')
    print()

    manifest = build_manifest(base, market)
    results = []  # (组, 位置, 版本号|None|ERR, 路径)

    for g, label, fn, path in manifest:
        if os.path.exists(path):
            try:
                v = fn(path)
            except Exception as e:
                v = 'ERR:' + str(e)[:60]
        else:
            v = 'MISSING'
        results.append((g, label, v, path))

    if args.github:
        pat = os.environ.get('GITHUB_PAT', '')
        if not pat:
            print('ERROR: --github 需要 GITHUB_PAT 环境变量')
            sys.exit(2)
        repo = 'hansonzhang0606-ux/xiaodai-test-expert'
        gh_checks = [
            ('A.agent', 'GH plugins/ agents', agent_version,
             'plugins/xiaodai-testing-expert/agents/xiaodai-testing-expert.md'),
            ('A.agent', 'GH xiaodai-testing-expert/ agents', agent_version,
             'xiaodai-testing-expert/agents/xiaodai-testing-expert.md'),
            ('B.plugin', 'GH plugins/ plugin.json', plugin_version,
             'plugins/xiaodai-testing-expert/.codebuddy-plugin/plugin.json'),
            ('B.plugin', 'GH xiaodai-testing-expert/ plugin.json', plugin_version,
             'xiaodai-testing-expert/.codebuddy-plugin/plugin.json'),
            ('C.readme', 'GH 根 README', readme_version, 'README.md'),
            ('C.readme', 'GH plugins/ README', readme_version,
             'plugins/xiaodai-testing-expert/README.md'),
            ('C.readme', 'GH xiaodai-testing-expert/ README', readme_version,
             'xiaodai-testing-expert/README.md'),
            ('D.docs', 'GH docs/测试人员手册', doc_version,
             'docs/效贷功能测试专家-测试人员使用指导手册.md'),
            ('D.docs', 'GH docs/管理员手册', doc_version,
             'docs/效贷功能测试专家-管理员指导手册.md'),
        ]
        for g, label, fn, path in gh_checks:
            try:
                v = gh_file_version(repo, path, fn)
            except Exception as e:
                v = 'ERR:' + str(e)[:60]
            results.append((g, label, v, 'https://github.com/' + repo + '/blob/main/' + path))

    # 分组汇总
    groups = {}
    for g, label, v, path in results:
        groups.setdefault(g, []).append((label, v, path))

    if args.json:
        out = {'base': str(base), 'market': str(market) if market else None}
        for g, items in groups.items():
            out[g] = [{'loc': l, 'version': v} for l, v, _ in items]
        print(json.dumps(out, ensure_ascii=False, indent=1))
        sys.exit(0)

    expected = args.set
    problems = []
    for g in sorted(groups):
        items = groups[g]
        print('== %s ==' % g)
        versions = set()
        for label, v, path in items:
            print('   %-58s %s' % (label, v))
            if isinstance(v, str) and v and not v.startswith(('ERR', 'MISSING')):
                versions.add(v)
        valid = [v for v in versions if v and not v.startswith(('ERR', 'MISSING'))]
        if g == 'F.zip':
            print('   (独立 v5.x 体系，不参与 agent 版本比对)')
        else:
            if len(valid) > 1:
                problems.append('%s 组版本不一致: %s' % (g, sorted(valid)))
            if expected and valid and any(v != expected for v in valid):
                problems.append('%s 组与期望版本 %s 不符: %s' % (g, expected, sorted(valid)))
        print()

    if problems:
        print('⚠️ 发现不一致:')
        for p in problems:
            print('  - ' + p)
        sys.exit(1)
    else:
        print('✅ 全部一致' + ('（期望版本 %s）' % expected if expected else ''))
        sys.exit(0)


if __name__ == '__main__':
    main()
