"""
验证脚本：获取当前界面的所有 UI 元素信息（Python 端修复文本）
包括：文本、按钮、图标、可点击元素等
"""
import sys
import json
import time

try:
    from airtest.core.api import *
    from poco.drivers.unity3d import UnityPoco
except ImportError as e:
    print(f"导入错误: {e}")
    print("请先安装依赖: pip install airtest pocoui")
    sys.exit(1)

def find_nearby_text(target_node, all_nodes, max_distance=200):
    """
    为 target_node 查找附近包含中文/字母的文本
    基于空间位置（距离最近的文本节点）
    """
    target_pos = target_node.get('payload', {}).get('pos', [0, 0])
    target_size = target_node.get('payload', {}).get('size', [0, 0])
    
    # 计算 target 的边界框
    tx, ty = target_pos
    tw, th = target_size
    target_left = tx - tw/2
    target_right = tx + tw/2
    target_top = ty - th/2
    target_bottom = ty + th/2
    
    best_text = None
    best_distance = float('inf')
    
    for node in all_nodes:
        # 跳过自己
        if node == target_node:
            continue
        
        # 只查找有文本的节点
        text = node.get('payload', {}).get('text', '')
        if not text:
            continue
        
        # 检查是否包含中文或字母
        if not any('\u4e00' <= c <= '\u9fff' or c.isalpha() for c in text):
            continue
        
        # 计算距离
        node_pos = node.get('payload', {}).get('pos', [0, 0])
        node_size = node.get('payload', {}).get('size', [0, 0])
        
        nx, ny = node_pos
        nw, nh = node_size
        node_left = nx - nw/2
        node_right = nx + nw/2
        node_top = ny - nh/2
        node_bottom = ny + nh/2
        
        # 计算中心点距离
        dx = abs(tx - nx)
        dy = abs(ty - ny)
        distance = (dx**2 + dy**2) ** 0.5
        
        # 如果在 max_distance 范围内，且距离更近
        if distance < max_distance and distance < best_distance:
            best_distance = distance
            best_text = text
    
    return best_text

def fix_text_in_python(ui_tree):
    """
    在 Python 端修复 text 字段（通用方案）
    适用于所有 text 为空的节点
    """
    print("\n" + "=" * 60)
    print("开始在 Python 端修复 text 字段...")
    print("=" * 60)
    
    # 1. 提取所有节点（扁平化）
    all_nodes = []
    
    def extract_nodes(obj):
        if isinstance(obj, dict):
            payload = obj.get('payload', {})
            all_nodes.append(obj)
            for child in obj.get('children', []):
                extract_nodes(child)
        elif isinstance(obj, list):
            for item in obj:
                extract_nodes(item)
    
    extract_nodes(ui_tree)
    print(f"共提取 {len(all_nodes)} 个节点")
    
    # 2. 为每个 text 为空的节点查找附近文本
    fixed_count = 0
    for node in all_nodes:
        payload = node.get('payload', {})
        text = payload.get('text', '')
        clickable = payload.get('clickable', False)
        
        # 只修复：可点击 且 text 为空的节点
        if clickable and not text:
            nearby_text = find_nearby_text(node, all_nodes)
            if nearby_text:
                node['payload']['text'] = nearby_text
                fixed_count += 1
                print(f"  ✅ 修复: {payload.get('name', '')} → text='{nearby_text}'")
    
    print(f"\n修复完成！共修复 {fixed_count} 个节点")
    return ui_tree, all_nodes

def analyze_ui_tree():
    """分析当前 UI 树，提取所有元素信息"""
    
    print("=" * 60)
    print("开始 dump UI 树...")
    print("=" * 60)
    
    # 连接 Unity
    try:
        auto_setup(__file__)
        init_device('Windows')
        poco = UnityPoco()
        print("[成功] Poco 连接成功")
    except Exception as e:
        print(f"[失败] Poco 连接失败: {e}")
        return
    
    # 获取 UI 树
    try:
        ui_tree = poco.dump()
        print(f"[成功] UI 树获取成功，类型: {type(ui_tree)}")
        print(f"[成功] UI 树大小: {len(str(ui_tree))} 字节")
    except Exception as e:
        print(f"[失败] UI 树获取失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 【关键】在 Python 端修复 text 字段
    ui_tree, all_nodes = fix_text_in_python(ui_tree)
    
    # 保存修复后的 UI 树到文件
    import os
    os.makedirs('reports/runtime_capture', exist_ok=True)
    with open('reports/runtime_capture/ui_tree_fixed.json', 'w', encoding='utf-8') as f:
        json.dump(ui_tree, f, ensure_ascii=False, indent=2)
    print(f"\n[成功] 修复后的 UI 树已保存到: reports/runtime_capture/ui_tree_fixed.json")
    
    # 分类统计
    print("\n" + "=" * 60)
    print("分类统计：")
    print("=" * 60)
    
    # 1. 有文本的节点
    text_nodes = [n for n in all_nodes if n.get('payload', {}).get('text', '')]
    print(f"\n1. 有文本的节点: {len(text_nodes)} 个")
    for i, node in enumerate(text_nodes[:20]):  # 只显示前20个
        payload = node.get('payload', {})
        print(f"   {i+1}. text='{payload.get('text', '')}' | name={payload.get('name', '')} | clickable={payload.get('clickable', False)}")
    if len(text_nodes) > 20:
        print(f"   ... (还有 {len(text_nodes) - 20} 个)")
    
    # 2. 可点击的节点
    clickable_nodes = [n for n in all_nodes if n.get('payload', {}).get('clickable', False)]
    print(f"\n2. 可点击的节点: {len(clickable_nodes)} 个")
    for i, node in enumerate(clickable_nodes[:30]):  # 只显示前30个
        payload = node.get('payload', {})
        text_display = payload.get('text', '') if payload.get('text', '') else '(空)'
        print(f"   {i+1}. text={text_display} | name={payload.get('name', '')}")
    if len(clickable_nodes) > 30:
        print(f"   ... (还有 {len(clickable_nodes) - 30} 个)")
    
    # 3. 图标节点（包含 Icon 关键词，且不可点击）
    icon_nodes = [n for n in all_nodes 
                  if 'Icon' in n.get('payload', {}).get('name', '') and not n.get('payload', {}).get('clickable', False)]
    print(f"\n3. 图标节点 (Icon): {len(icon_nodes)} 个")
    for i, node in enumerate(icon_nodes[:20]):
        payload = node.get('payload', {})
        print(f"   {i+1}. name={payload.get('name', '')} | text={payload.get('text', '') if payload.get('text', '') else '(空)'}")
    if len(icon_nodes) > 20:
        print(f"   ... (还有 {len(icon_nodes) - 20} 个)")
    
    # 4. 按钮节点（包含 Btn 关键词）
    btn_nodes = [n for n in all_nodes if 'Btn' in n.get('payload', {}).get('name', '')]
    print(f"\n4. 按钮节点 (Btn): {len(btn_nodes)} 个")
    for i, node in enumerate(btn_nodes[:20]):
        payload = node.get('payload', {})
        text_display = payload.get('text', '') if payload.get('text', '') else '(空)'
        print(f"   {i+1}. text={text_display} | name={payload.get('name', '')} | clickable={payload.get('clickable', False)}")
    if len(btn_nodes) > 20:
        print(f"   ... (还有 {len(btn_nodes) - 20} 个)")
    
    # 5. text 为空的节点（需要修复的）
    empty_text_nodes = [n for n in all_nodes 
                        if not n.get('payload', {}).get('text', '') 
                        and n.get('payload', {}).get('clickable', False)]
    print(f"\n5. ⚠️  可点击但 text 为空的节点: {len(empty_text_nodes)} 个")
    for i, node in enumerate(empty_text_nodes[:30]):
        payload = node.get('payload', {})
        print(f"   {i+1}. name={payload.get('name', '')} | type={payload.get('type', '')}")
    if len(empty_text_nodes) > 30:
        print(f"   ... (还有 {len(empty_text_nodes) - 30} 个)")
    
    # 保存完整结果到文件
    output_file = 'reports/runtime_capture/ui_full_analysis_fixed.json'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'total_nodes': len(all_nodes),
            'text_nodes': [n.get('payload', {}) for n in text_nodes],
            'clickable_nodes': [n.get('payload', {}) for n in clickable_nodes],
            'icon_nodes': [n.get('payload', {}) for n in icon_nodes],
            'btn_nodes': [n.get('payload', {}) for n in btn_nodes],
            'empty_text_nodes': [n.get('payload', {}) for n in empty_text_nodes]
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n完整分析结果已保存到: {output_file}")
    
    print("\n" + "=" * 60)
    print("建议：")
    print("=" * 60)
    if len(empty_text_nodes) > 0:
        print(f"⚠️  仍有 {len(empty_text_nodes)} 个可点击节点 text 为空")
        print("   → 可能这些节点的附近没有包含中文/字母的文本节点")
        print("   → 可以尝试增大 max_distance 参数")
    else:
        print("✅ 所有可点击节点都有文本！")
    
    return all_nodes

if __name__ == "__main__":
    analyze_ui_tree()
