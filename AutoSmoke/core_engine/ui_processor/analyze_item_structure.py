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

# 找到第一个 ClickContent 节点，然后提取其所在的 Item(Clone) 完整子树
def find_item_clone_subtree(obj, path='', result=None):
    if result is not None:
        return result
    
    if isinstance(obj, dict):
        payload = obj.get('payload', {})
        name = payload.get('name', '')
        text = payload.get('text', '')
        new_path = path + '/' + name if name else path
        
        # 如果找到 ClickContent，往上找到 Item(Clone)
        if 'ClickContent' in name and 'ClickContentManual' not in name:
            # 分割路径，找到最近的 Item(Clone)
            parts = new_path.split('/')
            for i in range(len(parts) - 1, -1, -1):
                if 'Item(Clone)' in parts[i]:
                    # 找到 Item(Clone)，现在在原数据中定位它
                    item_path = '/'.join(parts[:i+1])
                    return {'clickcontent_path': new_path, 'item_clone_path': item_path}
        
        for key, val in obj.items():
            result = find_item_clone_subtree(val, new_path, result)
            if result:
                return result
    
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            result = find_item_clone_subtree(item, path + '[' + str(i) + ']', result)
            if result:
                return result
    
    return result

# 根据路径提取完整的子树
def extract_subtree(obj, target_path, current_path='', depth=0):
    if depth > 20:
        return None
    
    if isinstance(obj, dict):
        payload = obj.get('payload', {})
        name = payload.get('name', '')
        text = payload.get('text', '')
        new_path = current_path + '/' + name if name else current_path
        
        if new_path.endswith(target_path):
            return obj
        
        for key, val in obj.items():
            result = extract_subtree(val, target_path, new_path, depth + 1)
            if result:
                return result
    
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            result = extract_subtree(item, target_path, current_path + '[' + str(i) + ']', depth)
            if result:
                return result
    
    return None

# 主逻辑
info = find_item_clone_subtree(data)
if info:
    print('找到 ClickContent：')
    print('  路径：', info['clickcontent_path'][-100:])
    print('\nItem(Clone) 路径：')
    print('  ', info['item_clone_path'][-100:])
    
    # 提取 Item(Clone) 的完整子树
    item_subtree = extract_subtree(data, info['item_clone_path'])
    
    if item_subtree:
        print('\n=== Item(Clone) 完整结构 ===\n')
        
        # 递归打印所有节点
        def print_tree(node, indent=0, max_depth=3, current_depth=0):
            if current_depth > max_depth:
                return
            
            if isinstance(node, dict):
                payload = node.get('payload', {})
                name = payload.get('name', '')
                text = payload.get('text', '')
                
                # 打印节点信息
                node_info = ' ' * indent + name
                if text:
                    node_info += ' [text=' + text[:30] + ']'
                
                # 检查 name 是否包含中文
                if has_chinese(name):
                    node_info += ' ← 包含中文！'
                
                print(node_info)
                
                # 递归打印子节点
                for key, val in node.items():
                    if key != 'payload':
                        print_tree(val, indent + 2, max_depth, current_depth + 1)
            
            elif isinstance(node, list):
                for i, item in enumerate(node):
                    print_tree(item, indent, max_depth, current_depth)
        
        print_tree(item_subtree, max_depth=10)
        
        # 现在搜索所有包含中文的字段（不仅是 text）
        print('\n\n=== 搜索包含中文的所有字段 ===\n')
        
        def find_all_chinese(node, path='', results=None, depth=0):
            if results is None:
                results = []
            if depth > 15:
                return results
            
            if isinstance(node, dict):
                payload = node.get('payload', {})
                name = payload.get('name', '')
                text = payload.get('text', '')
                new_path = path + '/' + name if name else path
                
                # 检查 text 是否包含中文
                if has_chinese(text):
                    results.append({'path': new_path, 'field': 'text', 'value': text[:50]})
                
                # 检查 name 是否包含中文
                if has_chinese(name):
                    results.append({'path': new_path, 'field': 'name', 'value': name})
                
                for key, val in node.items():
                    find_all_chinese(val, new_path, results, depth + 1)
            
            elif isinstance(node, list):
                for i, item in enumerate(node):
                    find_all_chinese(item, path + '[' + str(i) + ']', results, depth)
            
            return results
        
        chinese_nodes = find_all_chinese(item_subtree)
        if chinese_nodes:
            print('在 Item(Clone) 中找到', len(chinese_nodes), '个包含中文的节点：\n')
            for i, n in enumerate(chinese_nodes):
                print(f"  {i+1}. {n['field']}={n['value']}")
                print(f"     路径：{n['path'][-80:]}")
        else:
            print('未在 Item(Clone) 中找到包含中文的节点')
            print('这可能是因为中文文本不在这个 Item(Clone) 子树中')
    else:
        print('未能提取 Item(Clone) 子树')
else:
    print('未找到 ClickContent 节点')
