"""
XMind 测试点生成脚本（完整版）

根据测试点 JSON 数据生成 XMind 文件
支持：
1. 4-5 层层级结构
2. 评审标记颜色（蓝色=新增、橙色=修改、灰色=删除）
3. 模式图标（📄/🔍/🔧）

使用方法：
    python generate_xmind.py --input <测试点.json> --output <xmind路径>
"""

import os
import json
import argparse
import zipfile
import uuid
from datetime import datetime


def gen_id():
    """生成唯一ID（32位hex，兼容效贷格式）"""
    return uuid.uuid4().hex

# XMind 标记颜色定义
MARKER_COLORS = {
    '新增': 'tag-blue',      # 蓝色
    '修改': 'tag-orange',    # 橙色
    '删除': 'tag-grey',      # 煤灰色
    '确认': None,            # 无标记
}

# 来源图标（emoji 转文本）
SOURCE_ICONS = {
    'requirement': '需求文档',
    'review': '评审验证',
    'tech': '技术方案',
    'knowledge_base': '知识库补充',
}


def create_xmind_from_json(testpoints_data: dict, output_path: str):
    """
    根据测试点 JSON 生成 XMind 文件（完整格式，兼容 XMind 8/2020）

    Args:
        testpoints_data: 测试点 JSON 数据
        output_path: 输出 XMind 文件路径
    """
    # XMind 文件是 ZIP 格式，包含 content.json、manifest.json、metadata.json、Revisions/
    content = generate_xmind_content(testpoints_data)

    # manifest.json（XMind 8 必需）
    manifest = {
        "file-entries": {
            "content.json": {},
            "metadata.json": {},
            "Revisions/": {}
        }
    }

    # metadata.json
    metadata = {
        "creator": {
            "name": "XMind",
            "version": "3.7.0"
        },
        "createdDate": datetime.now().strftime("%Y-%m-%d")
    }

    # 创建 XMind 文件（ZIP_STORED 格式，效贷标准）
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_STORED) as zf:
        zf.writestr('content.json', json.dumps(content, ensure_ascii=False, indent=2))
        zf.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False))
        zf.writestr('metadata.json', json.dumps(metadata, ensure_ascii=False))
        zf.writestr('Revisions/', '')  # 空目录

    print(f"✅ XMind 文件已生成: {output_path}")
    print_statistics(testpoints_data)


def generate_xmind_content(testpoints_data: dict) -> list:
    """
    生成 XMind content.json 内容

    XMind 8 格式：content.json 是一个列表，第一个元素是 sheet

    Returns:
        list: XMind content 数据
    """
    metadata = testpoints_data.get('metadata', {})
    title = metadata.get('title', '测试点')

    # 创建 sheet
    sheet = {
        'id': gen_id(),
        'title': title,
        'rootTopic': generate_root_topic(testpoints_data)
    }

    return [sheet]


def generate_root_topic(testpoints_data: dict) -> dict:
    """
    生成根节点

    Args:
        testpoints_data: 测试点 JSON 数据

    Returns:
        dict: 根节点数据
    """
    metadata = testpoints_data.get('metadata', {})
    title = metadata.get('title', '测试点')

    root_topic = {
        'id': gen_id(),
        'title': title,
        'structureClass': 'org.xmind.ui.map.unbalanced',  # XMind 结构类
        'children': {
            'attached': []
        }
    }

    # 添加一级节点（来源分类）
    modules = testpoints_data.get('modules', [])
    for module in modules:
        child_topic = generate_topic(module, level=1)
        root_topic['children']['attached'].append(child_topic)

    return root_topic


def generate_topic(module_data: dict, level: int = 1) -> dict:
    """
    递归生成 XMind 节点

    Args:
        module_data: 模块数据
        level: 当前层级

    Returns:
        dict: 节点数据
    """
    topic_id = gen_id()
    title = module_data.get('name', '')

    # 添加来源图标
    source = module_data.get('source', '')
    if level == 1 and source in SOURCE_ICONS:
        # 一级节点添加来源标识
        title = f"{SOURCE_ICONS[source]} - {title}"

    topic = {
        'id': topic_id,
        'title': title,
        'children': {
            'attached': []
        }
    }

    # 添加评审标记（如果有）
    marker_type = module_data.get('marker_type', '')
    if marker_type and MARKER_COLORS.get(marker_type):
        topic['markers'] = [{'markerId': MARKER_COLORS[marker_type]}]

    # 处理子模块
    sub_modules = module_data.get('sub_modules', [])
    for sub_module in sub_modules:
        child_topic = generate_topic(sub_module, level + 1)
        topic['children']['attached'].append(child_topic)

    # 处理测试点（叶子节点）
    testpoints = module_data.get('testpoints', [])
    for testpoint in testpoints:
        leaf_topic = {
            'id': gen_id(),
            'title': testpoint
        }

        # 检查测试点的评审标记
        tp_marker = module_data.get('testpoint_markers', {}).get(testpoint, '')
        if tp_marker and MARKER_COLORS.get(tp_marker):
            leaf_topic['markers'] = [{'markerId': MARKER_COLORS[tp_marker]}]

        topic['children']['attached'].append(leaf_topic)

    return topic


def print_statistics(testpoints_data: dict):
    """
    打印测试点统计

    Args:
        testpoints_data: 测试点 JSON 数据
    """
    metadata = testpoints_data.get('metadata', {})
    statistics = testpoints_data.get('statistics', {})

    print("\n" + "=" * 60)
    print("测试点统计")
    print("=" * 60)

    if statistics:
        total = statistics.get('total_testpoints', 0)
        by_source = statistics.get('by_source', {})
        by_type = statistics.get('by_type', {})

        print(f"总测试点数: {total}")

        if by_source:
            print("\n按来源分布:")
            for source, count in by_source.items():
                print(f"  - {source}: {count}")

        if by_type:
            print("\n按类型分布:")
            for type_name, count in by_type.items():
                print(f"  - {type_name}: {count}")

    print("\n提示: 请使用 XMind 软件打开文件进行评审")
    print("      蓝色标记 = 新增，橙色标记 = 修改，灰色标记 = 删除")
    print("=" * 60)


def create_xmind_json_alternative(testpoints_data: dict, output_path: str):
    """
    替代方案：生成 XMind 可导入的 JSON 格式

    当无法直接生成 XMind 时，输出结构化 JSON
    """
    # 生成 XMind 兼容格式
    xmind_json = {
        'title': testpoints_data.get('metadata', {}).get('title', '测试点'),
        'structure': 'mindmap',
        'root': convert_to_xmind_tree(testpoints_data)
    }

    json_path = output_path.replace('.xmind', '_import.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(xmind_json, f, ensure_ascii=False, indent=2)

    print(f"[INFO] 已生成 XMind 导入格式 JSON: {json_path}")
    print(f"       请使用 XMind 软件导入此文件")


def convert_to_xmind_tree(testpoints_data: dict) -> dict:
    """
    转换为 XMind 导入格式树结构

    Args:
        testpoints_data: 测试点 JSON 数据

    Returns:
        dict: XMind 树结构
    """
    def convert_node(module: dict) -> dict:
        children = []

        for sub_module in module.get('sub_modules', []):
            children.append(convert_node(sub_module))

        for testpoint in module.get('testpoints', []):
            children.append({
                'title': testpoint,
                'children': [],
                'marker': module.get('marker_type', None)
            })

        return {
            'title': module.get('name', ''),
            'children': children,
            'marker': module.get('marker_type', None)
        }

    root_children = []
    for module in testpoints_data.get('modules', []):
        root_children.append(convert_node(module))

    return {
        'title': testpoints_data.get('metadata', {}).get('title', '测试点'),
        'children': root_children
    }


def main():
    parser = argparse.ArgumentParser(description='生成 XMind 测试点文件')

    parser.add_argument('--input', '-i', required=True, help='测试点 JSON 文件路径')
    parser.add_argument('--output', '-o', required=True, help='输出 XMind 文件路径')

    args = parser.parse_args()

    # 读取测试点 JSON
    if not os.path.exists(args.input):
        print(f"[FAIL] 文件不存在: {args.input}")
        return

    with open(args.input, 'r', encoding='utf-8') as f:
        testpoints_data = json.load(f)

    # 生成 XMind
    create_xmind_from_json(testpoints_data, args.output)


if __name__ == '__main__':
    main()