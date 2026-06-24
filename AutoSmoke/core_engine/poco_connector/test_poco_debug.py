#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Poco Unity连接测试 - 调试版本
"""

import sys
import time

def test_poco_connection():
    """测试Poco连接"""
    print("=" * 80)
    print("Poco Unity连接测试 - 调试版本")
    print("=" * 80)
    
    try:
        # 导入airtest并手动初始化设备
        print("\n导入airtest并手动初始化设备...")
        from airtest.core.api import connect_device
        
        # 使用connect_device
        print("  使用connect_device('Windows://')...")
        device = connect_device('Windows://')
        print(f"  ✅ 设备连接成功: {device}")
        
        # 导入poco
        print("\n导入poco模块...")
        from poco.drivers.unity3d import UnityPoco
        
        # 创建UnityPoco实例
        print("创建UnityPoco实例...")
        poco = UnityPoco()
        
        # 等待Poco初始化
        print("等待Poco初始化...")
        time.sleep(2)
        
        # 调试：获取根节点并打印信息
        print("\n调试：获取根节点...")
        
        # 获取根节点
        root = poco()
        print(f"  根节点: {root}")
        
        # 打印根节点的属性
        print("\n  根节点属性:")
        print(f"    name: {root.attr('name')}")
        print(f"    type: {root.attr('type')}")
        print(f"    clickable: {root.attr('clickable')}")
        print(f"    visible: {root.attr('visible')}")
        
        # 获取子节点
        print("\n  获取子节点...")
        children = root.children()
        children_count = len(children)
        print(f"    子节点数量: {children_count}")
        
        # 打印前10个子节点的信息
        print("\n  前10个子节点:")
        for i, child in enumerate(children[:10]):
            print(f"    {i+1}. name: {child.attr('name')}, type: {child.attr('type')}, clickable: {child.attr('clickable')}")
        
        # 尝试查询所有节点
        print("\n  尝试查询所有节点...")
        try:
            all_nodes = poco('//*')
            all_nodes_count = len(all_nodes)
            print(f"    ✅ 找到 {all_nodes_count} 个节点")
            
            # 打印前10个节点的信息
            print("\n  前10个节点:")
            for i, node in enumerate(all_nodes[:10]):
                print(f"    {i+1}. name: {node.attr('name')}, type: {node.attr('type')}, clickable: {node.attr('clickable')}")
        except Exception as e:
            print(f"    ❌ 查询失败: {e}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_poco_connection()
