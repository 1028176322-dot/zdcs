import json

# 读取最新的 UI 树
with open('reports/runtime_capture/ui_tree_20260611_140456.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 找到第一个 ClickContent，然后提取其所在的 Item(Clone) 的完整子树
def find_clickcontent_and_extract_item(obj, path='', result=None):
    if result is not None:
        return result
    
    if isinstance(obj, dict):
        payload = obj.get('payload', {})
        name = payload.get('name', '')
        text = payload.get('text', '')
        new_path = path + '/' + name if name else path
        
        if 'ClickContent' in name and 'ClickContentManual' not in name:
            # 找到了 ClickContent，现在向上找到 Item(Clone)
            parts = new_path.split('/')
            item_clone_path = ''
            for i in range(len(parts) - 1, -1, -1):
                if 'Item(Clone)' in parts[i]:
                    item_clone_path = '/'.join(parts[:i+1])
                    break
            
            if item_clone_path:
                return {'clickcontent_path': new_path, 'item_clone_path': item_clone_path}
        
        for key, val in obj.items():
            result = find_clickcontent_and_extract_item(val, new_path, result)
            if result:
                return result
    
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            result = find_clickcontent_and_extract_item(item, path + '[' + str(i) + ']', result)
            if result:
                return result
    
    return None

# 根据路径提取完整的子树
def extract_subtree(obj, target_path, current_path='', depth=0):
    if depth > 20:
        return None
    
    if isinstance(obj, dict):
        payload = obj.get('payload', {})
        name = payload.get('name', '')
        text = payload.get('text', '')
        new_path = current_path + '/' + name if name else current_path
        
        if new_path == target_path or new_path.endswith(target_path):
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

# 递归打印所有节点（限制深度）
def print_all_nodes(node, indent=0, max_depth=10, current_depth=0):
    if current_depth > max_depth:
        return
    
    if isinstance(node, dict):
        payload = node.get('payload', {})
        name = payload.get('name', '')
        text = payload.get('text', '')
        
        info = ' ' * (indent * 2) + '└─ ' + name
        if text:
            info += ' [text=' + text[:40] + ']'
        
        print(info)
        
        for key, val in node.items():
            if key != 'payload':
                print_all_nodes(val, indent + 1, max_depth, current_depth + 1)
    
    elif isinstance(node, list):
        for i, item in enumerate(node):
            print_all_nodes(item, indent, max_depth, current_depth)

# 主逻辑
print('=== 提取 ClickContent 所在的 Item(Clone) 完整子树 ===\n')

result = find_clickcontent_and_extract_item(data)
if result:
    print('找到 ClickContent：')
    print('  路径：', result['clickcontent_path'][-120:])
    print('\n所在的 Item(Clone) 路径：')
    print(' ', result['item_clone_path'][-100:])
    
    # 提取 Item(Clone) 的完整子树
    item_subtree = extract_subtree(data, result['item_clone_path'])
    
    if item_subtree:
        print('\n=== Item(Clone) 完整结构（深度限制 10）===\n')
        print_all_nodes(item_subtree, max_depth=10)
        
        # 现在搜索这个 Item(Clone) 下是否有 TxtDesc
        print('\n\n=== 在 Item(Clone) 下搜索 TxtDesc ===\n')
        
        def find_txtdesc_in_subtree(node, path='', depth=0):
            if depth > 15:
                return None
            
            if isinstance(node, dict):
                payload = node.get('payload', {})
                name = payload.get('name', '')
                text = payload.get('text', '')
                new_path = path + '/' + name if name else path
                
                if 'TxtDesc' in name:
                    return {'path': new_path, 'text': text}
                
                for key, val in node.items():
                    result = find_txtdesc_in_subtree(val, new_path, depth + 1)
                    if result:
                        return result
            
            elif isinstance(node, list):
                for i, item in enumerate(node):
                    result = find_txtdesc_in_subtree(item, path + '[' + str(i) + ']', depth)
                    if result:
                        return result
            
            return None
        
        txtdesc = find_txtdesc_in_subtree(item_subtree)
        if txtdesc:
            print('✅ 找到了 TxtDesc！')
            print('  路径：', txtdesc['path'][-100:])
            print('  text：', txtdesc['text'])
        else:
            print('❌ 未找到 TxtDesc')
            print('这说明 TxtDesc 不在这个 Item(Clone) 下')
            print('可能 TxtDesc 和 ClickContent 不在同一个 Item(Clone) 下')
    else:
        print('未能提取 Item(Clone) 子树')
else:
    print('未找到 ClickContent 节点')
