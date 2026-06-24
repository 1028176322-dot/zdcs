#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查看一个ClickContent元素的完整结构
"""
import json
from pathlib import Path

# 读取UI树
with open(str(Path(__file__).parent.parent / 'reports' / 'runtime_capture' / 'ui_tree_20260611_120143.json'), 'r', encoding='utf-8') as f:
    data = json.load(f)

print("查找第一个ClickContent元素的结构...\n")

def find_first_clickcontent(node, depth=0):
    """查找第一个ClickContent元素"""
    if not isinstance(node, dict):
        return None
    
    payload = node.get('payload', {})
    
    # 检查是否可点击
    if payload.get('clickable') == True and payload.get('name') == 'ClickContent':
        return node
    
    # 递归查找子节点
    for child in node.get('children', []):
        result = find_first_clickcontent(child, depth + 1)
        if result:
            return result
    
    return None

# 查找第一个ClickContent
clickcontent = find_first_clickcontent(data)

if clickcontent:
    print("找到第一个ClickContent元素！")
    print("\n完整结构:")
    print(json.dumps(clickcontent, ensure_ascii=False, indent=2))
    
    # 查找父节点
    print("\n" + "="*80)
    print("现在查找ClickContent的父节点和兄弟节点...")
    
    # 需要在完整树中查找父节点
    # 这需要修改查找函数，让它返回路径
    def find_node_with_path(node, target_node, path=""):
        """查找节点并返回其路径和父节点"""
        if not isinstance(node, dict):
            return None, None, None
        
        # 检查是否是目标节点
        if node == target_node:
            return node, path, None
        
        # 检查子节点
        for i, child in enumerate(node.get('children', [])):
            child_path = path + "/" + node.get('name', '')
            if child == target_node:
                return child, child_path, node
            
            # 递归查找
            result, result_path, parent = find_node_with_path(child, target_node, child_path)
            if result:
                return result, result_path, parent
        
        return None, None, None
    
    # 这个方法是错的，因为node == target_node会比较对象引用
    # 让我用不同的方法：直接搜索UI树，打印ClickContent的上下文
    
else:
    print("未找到ClickContent元素")
