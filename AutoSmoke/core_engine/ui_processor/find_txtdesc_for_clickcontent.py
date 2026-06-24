import json

# 读取最新的 UI 树
with open('reports/runtime_capture/ui_tree_20260611_140456.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 方法：找到 ClickContent，然后向上找到 Item(Clone)，然后在这个 Item(Clone) 下查找 TxtDesc
def find_clickcontent_and_its_item_clone(obj, path='', result=None):
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
                return {
                    'clickcontent_path': new_path,
                    'item_clone_path': item_clone_path,
                    'clickcontent_text': text
                }
        
        for key, val in obj.items():
            result = find_clickcontent_and_its_item_clone(val, new_path, result)
            if result:
                return result
    
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            result = find_clickcontent_and_its_item_clone(item, path + '[' + str(i) + ']', result)
            if result:
                return result
    
    return result

# 在指定的 Item(Clone) 下查找 TxtDesc
def find_txtdesc_in_item_clone(obj, target_path, current_path='', depth=0):
    if depth > 20:
        return None
    
    if isinstance(obj, dict):
        payload = obj.get('payload', {})
        name = payload.get('name', '')
        text = payload.get('text', '')
        new_path = current_path + '/' + name if name else current_path
        
        # 如果路径匹配，在这个节点下查找 TxtDesc
        if new_path == target_path or new_path.endswith(target_path):
            # 找到了目标 Item(Clone)，现在递归查找 TxtDesc
            def search_txtdesc(node, path, d):
                if d > 10:
                    return None
                
                if isinstance(node, dict):
                    payload = node.get('payload', {})
                    node_name = payload.get('name', '')
                    node_text = payload.get('text', '')
                    
                    if 'TxtDesc' in node_name:
                        return {'path': path + '/' + node_name, 'text': node_text}
                    
                    for key, val in node.items():
                        result = search_txtdesc(val, path + '/' + node_name if node_name else path, d + 1)
                        if result:
                            return result
                
                elif isinstance(node, list):
                    for i, item in enumerate(node):
                        result = search_txtdesc(item, path + '[' + str(i) + ']', d + 1)
                        if result:
                            return result
                
                return None
            
            return search_txtdesc(obj, new_path, 0)
        
        # 否则继续递归
        for key, val in obj.items():
            result = find_txtdesc_in_item_clone(val, target_path, new_path, depth)
            if result:
                return result
    
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            result = find_txtdesc_in_item_clone(item, target_path, current_path + '[' + str(i) + ']', depth)
            if result:
                return result
    
    return None

# 主逻辑
print('=== 查找 ClickContent 所在的 Item(Clone) 及其下的 TxtDesc ===\n')

result = find_clickcontent_and_its_item_clone(data)
if result:
    print('找到 ClickContent：')
    print('  路径：', result['clickcontent_path'][-120:])
    print('  text：', result['clickcontent_text'])
    print('\n所在的 Item(Clone) 路径：')
    print(' ', result['item_clone_path'][-100:])
    
    # 在这个 Item(Clone) 下查找 TxtDesc
    print('\n在 Item(Clone) 下查找 TxtDesc...\n')
    txtdesc = find_txtdesc_in_item_clone(data, result['item_clone_path'])
    
    if txtdesc:
        print('✅ 找到了 TxtDesc！')
        print('  路径：', txtdesc['path'][-100:])
        print('  text：', txtdesc['text'])
    else:
        print('❌ 未找到 TxtDesc')
        print('这说明 TxtDesc 不在 ClickContent 所在的 Item(Clone) 下')
        
        # 查找所有 TxtDesc，看它们在哪个 Item(Clone) 下
        print('\n查找所有 TxtDesc 节点...\n')
        
        def find_all_txtdesc(obj, path='', results=None):
            if results is None:
                results = []
            
            if isinstance(obj, dict):
                payload = obj.get('payload', {})
                name = payload.get('name', '')
                text = payload.get('text', '')
                new_path = path + '/' + name if name else path
                
                if 'TxtDesc' in name:
                    # 找到 Item(Clone) 祖先
                    parts = new_path.split('/')
                    item_clone_path = ''
                    for i in range(len(parts) - 1, -1, -1):
                        if 'Item(Clone)' in parts[i]:
                            item_clone_path = '/'.join(parts[:i+1])
                            break
                    
                    results.append({
                        'txtdesc_path': new_path,
                        'item_clone_path': item_clone_path,
                        'text': text
                    })
                
                for key, val in obj.items():
                    find_all_txtdesc(val, new_path, results)
            
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    find_all_txtdesc(item, path + '[' + str(i) + ']', results)
            
            return results
        
        all_txtdesc = find_all_txtdesc(data)
        print(f'找到 {len(all_txtdesc)} 个 TxtDesc 节点：\n')
        
        for i, td in enumerate(all_txtdesc[:10]):  # 只显示前10个
            print(f'{i+1}. text={td["text"]}')
            print(f'   TxtDesc 路径：{td["txtdesc_path"][-80:]}')
            print(f'   Item(Clone) 路径：{td["item_clone_path"][-80:]}\n')
else:
    print('未找到 ClickContent 节点')
