import json

# 读取最新的 UI 树
with open('reports/runtime_capture/ui_tree_20260611_140456.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 查找包含中文的文本
import re

def has_chinese(text):
    if not text or not isinstance(text, str):
        return False
    for c in text:
        if '\u4e00' <= c <= '\u9fff':
            return True
    return False

# 找到第一个 ClickContent 节点，然后查找其附近（同一 Item(Clone) 下）包含中文的节点
def find_nearby_chinese(obj, depth=0, clickcontent_path=None, results=None, current_path=''):
    if results is None:
        results = []
    
    if isinstance(obj, dict):
        payload = obj.get('payload', {})
        name = payload.get('name', '')
        text = payload.get('text', '')
        path = current_path + '/' + name if name else current_path
        
        # 如果找到了 ClickContent，开始记录附近的节点
        if clickcontent_path is None and 'ClickContent' in name and 'ClickContentManual' not in name:
            clickcontent_path = path
            # 往回找祖先，然后找兄弟节点
            results.append({'type': 'ClickContent', 'path': path, 'text': text})
        
        # 如果已经在 ClickContent 附近，记录包含中文的节点
        if clickcontent_path is not None and has_chinese(text):
            results.append({'type': 'ChineseText', 'path': path, 'text': text[:50]})
        
        for key, val in obj.items():
            find_nearby_chinese(val, depth + 1, clickcontent_path, results, path)
    
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            find_nearby_chinese(item, depth + 1, clickcontent_path, results, current_path + '[' + str(i) + ']')
    
    return results

results = find_nearby_chinese(data)

print('找到', len(results), '个相关节点：')
for r in results[:20]:  # 显示前20个
    print(r['type'], ':', r['path'][-80:], '| text=', r.get('text', ''))

# 更精确的方法：找到 ClickContent，然后找同一 Item(Clone) 下的所有节点
print('\n\n=== 方法2：查找 ClickContent 同一 Item(Clone) 下的所有文本节点 ===\n')

def find_item_with_clickcontent(obj, path='', results=None):
    if results is None:
        results = []
    
    if isinstance(obj, dict):
        payload = obj.get('payload', {})
        name = payload.get('name', '')
        text = payload.get('text', '')
        new_path = path + '/' + name if name else path
        
        # 如果包含 ClickContent，打印整个 Item(Clone) 的结构
        if 'ClickContent' in name and 'ClickContentManual' not in name:
            # 找到共同的 Item(Clone) 祖先
            parts = new_path.split('/')
            item_clone_path = ''
            for i, part in enumerate(parts):
                item_clone_path += '/' + part
                if 'Item(Clone)' in part and i < len(parts) - 1:
                    # 这是 ClickContent 所在的 Item(Clone)
                    results.append({'clickcontent_path': new_path, 'item_clone_path': item_clone_path})
                    break
        
        for key, val in obj.items():
            find_item_with_clickcontent(val, new_path, results)
    
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            find_item_with_clickcontent(item, path + '[' + str(i) + ']', results)
    
    return results

# 重新实现：找到 ClickContent，然后提取其所在的 Item(Clone) 的所有子节点文本
def extract_item_clone(obj, target_path, current_path='', depth=0):
    if depth > 20:  # 防止无限递归
        return None
    
    if isinstance(obj, dict):
        payload = obj.get('payload', {})
        name = payload.get('name', '')
        text = payload.get('text', '')
        new_path = current_path + '/' + name if name else current_path
        
        # 如果路径匹配，提取这个节点的所有子节点
        if target_path.endswith(new_path):
            result = {'path': new_path, 'text': text, 'children': []}
            for key, val in obj.items():
                if key != 'payload':
                    child = extract_item_clone(val, '', new_path + '/' + key, depth + 1)
                    if child:
                        result['children'].append(child)
            return result
        
        # 否则继续递归
        for key, val in obj.items():
            result = extract_item_clone(val, target_path, new_path, depth)
            if result:
                return result
    
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            result = extract_item_clone(item, target_path, current_path + '[' + str(i) + ']', depth)
            if result:
                return result
    
    return None

# 简化：直接打印第一个 ClickContent 所在的 Item(Clone) 的所有兄弟节点
print('正在查找第一个 ClickContent 附近的所有节点...\n')

def find_clickcontent_and_siblings(obj, path='', result=None, current_path=''):
    if result is not None:
        return result
    
    if isinstance(obj, dict):
        payload = obj.get('payload', {})
        name = payload.get('name', '')
        text = payload.get('text', '')
        new_path = current_path + '/' + name if name else current_path
        
        if 'ClickContent' in name and 'ClickContentManual' not in name:
            # 找到了 ClickContent，现在找同一父节点下的所有兄弟节点
            parent_path = '/'.join(new_path.split('/')[:-1])
            return {'clickcontent': new_path, 'parent': parent_path}
        
        for key, val in obj.items():
            result = find_clickcontent_and_siblings(val, path, result, new_path)
            if result:
                return result
    
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            result = find_clickcontent_and_siblings(item, path, result, current_path + '[' + str(i) + ']')
            if result:
                return result
    
    return result

info = find_clickcontent_and_siblings(data)
if info:
    print('ClickContent 路径：', info['clickcontent'][-100:])
    print('父节点路径：', info['parent'][-100:])
    
    # 现在找父节点下的所有子节点
    print('\n父节点下的所有子节点：')
    
    def find_parent_and_children(obj, target_path, current_path='', depth=0):
        if depth > 20:
            return None
        
        if isinstance(obj, dict):
            payload = obj.get('payload', {})
            name = payload.get('name', '')
            text = payload.get('text', '')
            new_path = current_path + '/' + name if name else current_path
            
            if new_path.endswith(target_path):
                # 找到了父节点，打印所有子节点
                children = []
                for key, val in obj.items():
                    if isinstance(val, dict) and 'payload' in val:
                        child_payload = val.get('payload', {})
                        child_name = child_payload.get('name', '')
                        child_text = child_payload.get('text', '')
                        children.append({'name': child_name, 'text': child_text})
                    elif isinstance(val, list):
                        for i, item in enumerate(val):
                            if isinstance(item, dict) and 'payload' in item:
                                child_payload = item.get('payload', {})
                                child_name = child_payload.get('name', '')
                                child_text = child_payload.get('text', '')
                                children.append({'name': child_name, 'text': child_text})
                return children
            
            for key, val in obj.items():
                result = find_parent_and_children(val, target_path, new_path, depth + 1)
                if result:
                    return result
        
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                result = find_parent_and_children(item, target_path, current_path + '[' + str(i) + ']', depth)
                if result:
                    return result
        
        return None
    
    children = find_parent_and_children(data, info['parent'])
    if children:
        for i, child in enumerate(children):
            print(f"  {i+1}. {child['name']} | text={child['text'][:50] if child['text'] else '(空)'}")
    else:
        print('未找到父节点的子节点')
