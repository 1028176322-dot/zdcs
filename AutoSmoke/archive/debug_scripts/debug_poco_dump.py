"""
调试脚本：检查 Poco dump 返回的原始数据
"""
import sys
import json

try:
    from airtest.core.api import *
    from poco.drivers.unity3d import UnityPoco
except ImportError as e:
    print(f"导入错误: {e}")
    sys.exit(1)

def debug_poco_dump():
    """检查 Poco dump 返回的原始数据"""
    
    print("=" * 60)
    print("开始连接 Poco...")
    print("=" * 60)
    
    # 连接 Unity
    try:
        init_device('Windows')
        poco = UnityPoco()
        print("[成功] Poco 连接成功")
    except Exception as e:
        print(f"[失败] Poco 连接失败: {e}")
        return
    
    # 获取 UI 树
    print("\n正在调用 poco.agent.call('dump')...")
    try:
        raw_data = poco.agent.call("dump")
        print(f"[成功] 返回数据类型: {type(raw_data)}")
        print(f"[成功] 返回数据大小: {len(str(raw_data))} 字节")
        
        # 打印原始数据（前500字符）
        raw_str = str(raw_data)
        print(f"\n原始数据（前500字符）：")
        print(raw_str[:500])
        print("...")
        
        # 尝试解析为 JSON
        print(f"\n尝试解析为 JSON...")
        try:
            if isinstance(raw_data, str):
                data = json.loads(raw_data)
            else:
                data = raw_data
            
            print(f"[成功] JSON 解析成功")
            print(f"数据类型: {type(data)}")
            
            if isinstance(data, dict):
                print(f"字典键: {list(data.keys())}")
            elif isinstance(data, list):
                print(f"列表长度: {len(data)}")
            
            # 保存到文件
            with open('reports/runtime_capture/debug_raw_dump.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"\n完整数据已保存到: reports/runtime_capture/debug_raw_dump.json")
            
        except json.JSONDecodeError as e:
            print(f"[失败] JSON 解析失败: {e}")
            
    except Exception as e:
        print(f"[失败] UI 树获取失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_poco_dump()
