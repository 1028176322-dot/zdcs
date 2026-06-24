import json

# 读取最新的 UI 树
with open('reports/runtime_capture/ui_tree_20260611_140456.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 查找 ClickContent 和 TxtDesc 的位置
def find_nodes(obj, path='', clickcontent_nodes=None, txtdesc_nodes=None):
    if clickcontent_nodes is None:
        clickcontent_nodes = []
    if txtdesc_nodes is None:
        txtdesc_nodes = []
    
    if isinstance(obj, dict):
        name = obj.get('name', '')
        payload = obj.get('payload', {})
        node_name = payload.get('name', '')
        
        new_path = path + '/' + node_name if node_name else path
        
        if 'ClickContent' in node_name and 'ClickContentManual' not in node_name:
            clickcontent_nodes.append({'path': new_path, 'node': obj})
        
        if 'TxtDesc' in node_name:
            txtdesc_nodes.append({'path': new_path, 'node': obj})
        
        for key, val in obj.items():
            find_nodes(val, new_path, clickcontent_nodes, txtdesc_nodes)
    
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            find_nodes(item, path + '[' + str(i) + ']', clickcontent_nodes, txtdesc_nodes)
    
    return clickcontent_nodes, txtdesc_nodes

clickcontent_nodes, txtdesc_nodes = find_nodes(data)

print('找到', len(clickcontent_nodes), '个 ClickContent 节点')
print('找到', len(txtdesc_nodes), '个 TxtDesc 节点')

if clickcontent_nodes and txtdesc_nodes:
    # 取第一个 ClickContent 和第一个 TxtDesc
    cc_path = clickcontent_nodes[0]['path']
    td_path = txtdesc_nodes[0]['path']
    
    print('\n第一个 ClickContent 路径：')
    print(cc_path)
    
    print('\n第一个 TxtDesc 路径：')
    print(td_path)
    
    # 分析关系
    cc_parts = cc_path.strip('/').split('/')
    td_parts = td_path.strip('/').split('/')
    
    print('\n路径分析：')
    print('ClickContent 深度：', len(cc_parts))
    print('TxtDesc 深度：', len(td_parts))
    
    # 找到共同祖先
    common = []
    for i in range(min(len(cc_parts), len(td_parts))):
        if cc_parts[i] == td_parts[i]:
            common.append(cc_parts[i])
        else:
            break
    
    print('共同祖先：', '/' + '/'.join(common))
    print('ClickContent 相对于共同祖先的路径：', '/' + '/'.join(cc_parts[len(common):]))
    print('TxtDesc 相对于共同祖先的路径：', '/' + '/'.join(td_parts[len(common):]))
    
    # 计算需要往上几层
    print('\n结论：')
    print('TxtDesc 在 ClickContent 的', end='')
    if len(common) == len(cc_parts):
        print('同一节点或其子节点中')
    else:
        levels_up = len(cc_parts) - len(common)
        print('往上', levels_up, '层')
        if levels_up == 1:
            print('→ TxtDesc 是 ClickContent 的兄弟节点（同一父节点下）')
        elif levels_up == 2:
            print('→ TxtDesc 是 ClickContent 的叔伯节点（同一祖父节点下）')
        else:
            print('→ TxtDesc 在 ClickContent 的祖先的第', levels_up, '层')
