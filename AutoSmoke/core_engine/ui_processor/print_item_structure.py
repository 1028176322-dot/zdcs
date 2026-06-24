import json

# 读取最新的 UI 树
with open('reports/runtime_capture/ui_tree_20260611_140456.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 导入正则表达式，用于检测中文
import re

def has_chinese(text):
    if not text or not isinstance(text, str):
        return False
    for c in text:
        if '\u4e00' <= c <= '\u9fff':
            return True
    return False

# 方法1：找到 ClickContent 节点，然后打印其祖先链
print('=== 方法1：打印 ClickContent 的祖先链 ===\n')

def find_clickcontent_and_print_ancestors(obj, path='', parent_chain=None):
    if parent_chain is None:
        parent_chain = []
    
    if isinstance(obj, dict):
        payload = obj.get('payload', {})
        name = payload.get('name', '')
        text = payload.get('text', '')
        new_path = path + '/' + name if name else path
        
        # 将当前节点加入祖先链
        new_chain = parent_chain + [{'name': name, 'path': new_path, 'text': text}]
        
        # 如果找到 ClickContent
        if 'ClickContent' in name and 'ClickContentManual' not in name:
            print('找到 ClickContent！')
            print('路径：', new_path[-100:])
            print('\n祖先链：')
            for i, ancestor in enumerate(new_chain):
                indent = '  ' * i
                print(f"{indent}└─ {ancestor['name']} (text={ancestor['text'][:30] if ancestor['text'] else '(空)'})")
            return True
        
        # 继续递归
        for key, val in obj.items():
            if isinstance(val, (dict, list)):
                if find_clickcontent_and_print_ancestors(val, new_path, new_chain):
                    return True
    
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            if find_clickcontent_and_print_ancestors(item, path + '[' + str(i) + ']', parent_chain):
                return True
    
    return False

find_clickcontent_and_print_ancestors(data)

# 方法2：找到 Item(Clone) 节点，打印其完整子树（限制深度）
print('\n\n=== 方法2：打印第一个 Item(Clone) 的完整子树 ===\n')

def find_and_print_item_clone(obj, path='', found=False):
    if found:
        return True
    
    if isinstance(obj, dict):
        payload = obj.get('payload', {})
        name = payload.get('name', '')
        text = payload.get('text', '')
        new_path = path + '/' + name if name else path
        
        # 如果找到 Item(Clone)
        if 'Item(Clone)' in name and not found:
            print(f"找到 Item(Clone)：{name}")
            print(f"路径：{new_path[-100:]}")
            print('\n完整子树（深度限制10）：\n')
            
            # 打印完整子树
            def print_subtree(node, indent=0, max_depth=10, current_depth=0):
                if current_depth > max_depth:
                    return
                
                if isinstance(node, dict):
                    payload = node.get('payload', {})
                    node_name = payload.get('name', '')
                    node_text = payload.get('text', '')
                    
                    # 打印节点信息
                    info = ' ' * (indent * 2) + '└─ ' + node_name
                    if node_text:
                        info += ' [text=' + node_text[:30] + ']'
                    if has_chinese(node_name):
                        info += ' ← 名称含中文！'
                    if has_chinese(node_text):
                        info += ' ← 文本含中文！'
                    print(info)
                    
                    # 递归打印子节点
                    for key, val in node.items():
                        if isinstance(val, (dict, list)):
                            print_subtree(val, indent + 1, max_depth, current_depth + 1)
                
                elif isinstance(node, list):
                    for i, item in enumerate(node):
                        print_subtree(item, indent, max_depth, current_depth)
            
            print_subtree(obj, max_depth=8)
            return True
        
        # 继续递归
        for key, val in obj.items():
            if isinstance(val, (dict, list)):
                if find_and_print_item_clone(val, new_path, found):
                    return True
    
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            if find_and_print_item_clone(item, path + '[' + str(i) + ']', found):
                return True
    
    return False

find_and_print_item_clone(data)
