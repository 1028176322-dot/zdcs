#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Poco连接 - 活动界面（简化版）
"""
import sys
import time
import json

# 导入airtest
from airtest.core.api import connect_device, auto_setup
print("✅ airtest导入成功")

# 初始化airtest
auto_setup(__file__)
print("✅ airtest初始化成功")

# 连接Windows设备
print("\n连接Windows设备...")
connect_device('Windows://')
print("✅ Windows设备连接成功")

# 导入并创建UnityPoco
from poco.drivers.unity3d import UnityPoco
print("\n创建UnityPoco实例...")
poco = UnityPoco()
print("✅ UnityPoco实例创建成功")
from pathlib import Path

# 等待Poco连接
print("\n等待Poco连接...")
time.sleep(2)

# 尝试获取UI树
print("\n获取UI树...")
print("   (如果界面复杂，这可能需要一些时间...)")

try:
    # 使用rpc.call('Dump')获取UI树
    ui_tree = poco.agent.rpc.call('Dump')
    print(f"✅ UI树获取成功")
    print(f"  UI树类型: {type(ui_tree)}")
    
    # 保存到文件
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_file = fstr(Path(__file__).parent.parent / 'reports' / 'runtime_capture' / 'ui_tree_{timestamp}.json')
    
    # 尝试保存UI树
    try:
        # 转换为可序列化的格式
        def convert_to_serializable(obj):
            if isinstance(obj, dict):
                return {k: convert_to_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_serializable(item) for item in obj]
            elif hasattr(obj, '__dict__'):
                return str(obj)
            else:
                return obj
        
        serializable_ui_tree = convert_to_serializable(ui_tree)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(serializable_ui_tree, f, ensure_ascii=False, indent=2)
        print(f"✅ UI树已保存到: {output_file}")
    except Exception as e:
        print(f"⚠️ UI树保存失败: {e}")
        # 尝试直接保存原始UI树
        try:
            with open(output_file.replace('.json', '.txt'), 'w', encoding='utf-8') as f:
                f.write(str(ui_tree))
            print(f"✅ UI树(字符串格式)已保存到: {output_file.replace('.json', '.txt')}")
        except Exception as e2:
            print(f"❌ UI树保存失败: {e2}")
    
    # 尝试使用poco()获取根节点
    print("\n尝试使用poco()获取根节点...")
    root = poco()
    print(f"✅ 根节点获取成功")
    
    # 查询所有节点
    print("\n查询所有UI节点...")
    all_nodes = poco('//*')
    print(f"  找到 {len(all_nodes)} 个节点")
    
    if len(all_nodes) > 0:
        print("\n前10个节点:")
        for i, node in enumerate(all_nodes[:10]):
            try:
                name = node.attr('name')
                print(f"  {i+1}. {name}")
            except:
                print(f"  {i+1}. (无法获取名称)")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    
except Exception as e:
    print(f"\n❌ 获取UI树失败: {e}")
    import traceback
    traceback.print_exc()
