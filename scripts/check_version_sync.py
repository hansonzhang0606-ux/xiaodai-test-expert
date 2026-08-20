# -*- coding: utf-8 -*-
"""
效贷测试专家 - 版本号同步自检脚本
用法：
  python check_version_sync.py                  # 只扫本地（工作区 + marketplace 副本 + docs + zip）
  python check_version_sync.py --github         # 本地 + 远程 GitHub 双镜像对比（需 GITHUB_PAT）
  python check_version_sync.py --json           # 输出 JSON 汇总（供 CI/脚本解析）
  python check_version_sync.py --set 1.6.2      # 报告期望版本号（与各位置比对）

原理：把"当前版本号"应从哪些文件/字段读取列成清单，逐项提取版本号并分组比对。
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

WORKSPACE = r'D:\##AI转型\效贷测试专家-WorkBuddy'
MARKET = r'C:\Users\kingdee\.workbuddy\plugins\marketplaces'

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
# 位置清单
# ---------------------------------------------------------------

def build_manifest():
    """返回 [(组名, 位置说明, 版本提取器, 路径)]"""
    m = []
    mk = lambda g, label, fn, p: m.append((g, label, fn, p))

    # A. agent 组
    for label, p in [
        ('工作区根 agent.md', os.path.join(WORKSPACE, 'agent.md')),
        ('工作区镜像 agents', os.path.join(WORKSPACE, 'xiaodai-testing-expert', 'agents', 'xiaodai-testing-expert.md')),
    ]:
        mk('A.agent', label, agent_version, p)
    for sub in ['experts/plugins/xiaodai-testing-expert', 'my-experts/plugins/xiaodai-testing-expert',
                'xiaodai-test-expert-marketplace/plugins/xiaodai-testing-expert',
                'xiaodai-test-expert-marketplace/xiaodai-testing-expert']:
        mk('A.agent', '副本 ' + sub, agent_version,
           os.path.join(MARKET, sub, 'agents', 'xiaodai-testing-expert.md'))

    # B. plugin 组
    mk('B.plugin', '工作区镜像 plugin.json', plugin_version,
       os.path.join(WORKSPACE, 'xiaodai-testing-expert', '.codebuddy-plugin', 'plugin.json'))
    for sub in ['experts/plugins/xiaodai-testing-expert', 'my-experts/plugins/xiaodai-testing-expert',
                'xiaodai-test-expert-marketplace/plugins/xiaodai-testing-expert',
                'xiaodai-test-expert-marketplace/xiaodai-testing-expert']:
        mk('B.plugin', '副本 ' + sub, plugin_version,
           os.path.join(MARKET, sub, '.codebuddy-plugin', 'plugin.json'))

    # C. README 组
    for label, p in [
        ('工作区根 README', os.path.join(WORKSPACE, 'README.md')),
        ('工作区镜像 README', os.path.join(WORKSPACE, 'xiaodai-testing-expert', 'README.md')),
    ]:
        mk('C.readme', label, readme_version, p)

    # D. docs 组
    for sub in ['my-experts/docs', 'xiaodai-test-expert-marketplace/docs']:
        for doc in ['效贷功能测试专家-测试人员使用指导手册.md', '效贷功能测试专家-管理员指导手册.md']:
            mk('D.docs', '副本 docs/' + sub.split('/')[0] + '/' + doc, doc_version,
               os.path.join(MARKET, sub, doc))

    # E. prompts 组（工作区 + 镜像）
    for base in ['skills/ai-testcase-workflow-skill', 'xiaodai-testing-expert/skills/ai-testcase-workflow-skill']:
        for pr in ['document_consolidate', 'knowledge_base_archive', 'requirement_review',
                   'testcase_refine', 'testpoint_generate']:
            mk('E.prompts', base + '/prompts/' + pr, prompt_version,
               os.path.join(WORKSPACE, base, 'prompts', pr + '.md'))

    # F. skill/zip 组（独立 v5.x 体系，只报告不参与比对）
    mk('F.zip', '工作区 time-tracking-skill.zip', zip_skill_version,
       os.path.join(WORKSPACE, 'time-tracking-skill.zip'))
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
    # 写入临时内存对象交给提取器：提取器都走文件路径，这里用临时文件
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
    args = ap.parse_args()

    manifest = build_manifest()
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
        out = {}
        for g, items in groups.items():
            out[g] = [{'loc': l, 'version': v} for l, v, _ in items]
        print(json.dumps(out, ensure_ascii=False, indent=1))
        sys.exit(0)

    # 文本输出 + 一致性判定
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
        # 一致性判定：组内非 ERR 版本应统一；若指定 expected 则必须匹配（F.zip 独立 v5.x 体系跳过）
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
