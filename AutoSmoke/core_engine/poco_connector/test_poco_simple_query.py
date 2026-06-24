#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Poco连接测试 - 简单查询测试
不获取整个UI树，只查询几个特定元素
"""

import sys
import time

def test_poco_simple():
    """简单Poco连接测试"""
    print("=" * 80)
    print("Poco连接测试 - 简单查询")
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
        
        # 简单测试：获取根节点名称
        print("\n简单测试：")
        
        # 测试1: 获取根节点
        print("  测试1: 获取根节点...")
        try:
            root = poco()
            root_name = root.attr('name')
            print(f"    ✅ 根节点名称: {root_name}")
        except Exception as e:
            print(f"    ❌ 获取根节点失败: {e}")
        
        # 测试2: 查询所有节点数量
        print("\n  测试2: 查询所有节点数量...")
        try:
            all_nodes = poco('//*')
            count = len(all_nodes)
            print(f"    ✅ 找到 {count} 个节点")
        except Exception as e:
            print(f"    ❌ 查询失败: {e}")
        
        # 测试3: 查询特定名称的节点
        print("\n  测试3: 查询特定名称的节点...")
        test_names = ['MainCity', 'City', 'Hud', 'UI', 'Button']
        for name in test_names:
            try:
                nodes = poco(f'//{name}')
                count = len(nodes)
                if count > 0:
                    print(f"    ✅ 找到 {count} 个包含 '{name}' 的节点")
            except Exception as e:
                pass  # 忽略错误，继续查询下一个
        
        print("\n✅ 简单测试完成!")
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_poco_simple()
