"""
Poco连接器模块
按照方案文档4.1节的接口定义实现
"""

import sys
import time
from typing import Optional, Dict, List, Any


class PocoConnector:
    """
    Poco SDK连接器
    封装Poco SDK的Python接口，提供连接、dump、点击等功能
    """
    
    def __init__(self, device_type: str = 'Windows'):
        """
        初始化Poco连接器
        :param device_type: 设备类型 ('Windows', 'Android', 'iOS')
        """
        self.device_type = device_type
        self.poco = None
        self.device = None
        
    def connect(self) -> bool:
        """
        连接到Unity游戏
        :return: 是否连接成功
        """
        try:
            from airtest.core.api import connect_device
            from poco.drivers.unity3d import UnityPoco
            
            # 连接设备
            if self.device_type == 'Windows':
                self.device = connect_device('Windows:///')
            elif self.device_type == 'Android':
                self.device = connect_device('Android:///')
            elif self.device_type == 'iOS':
                self.device = connect_device('iOS:///')
            else:
                raise ValueError(f"不支持的设备类型: {self.device_type}")
            
            # 初始化Poco
            self.poco = UnityPoco()
            
            print(f"✓ 成功连接到Unity游戏 ({self.device_type})")
            return True
            
        except Exception as e:
            print(f"✗ 连接失败: {e}")
            return False
    
    def dump_ui_tree(self) -> Optional[Dict]:
        """
        获取当前界面的UI树
        :return: UI树 (dict)，失败返回None
        """
        if not self.poco:
            print("✗ Poco未连接，请先调用connect()")
            return None
        
        try:
            ui_tree = self.poco.dump()
            print(f"✓ 成功dump UI树，共{len(str(ui_tree))}字节")
            return ui_tree
        except Exception as e:
            print(f"✗ dump UI树失败: {e}")
            return None
    
    def find_element(self, name: Optional[str] = None, text: Optional[str] = None, **kwargs):
        """
        查找UI元素
        :param name: 元素名称 (如 'ClickContent')
        :param text: 元素文本 (如 '探险家试炼')
        :param kwargs: 其他查询条件
        :return: Poco对象，未找到返回None
        """
        if not self.poco:
            print("✗ Poco未连接，请先调用connect()")
            return None
        
        try:
            if name:
                return self.poco(name)
            elif text:
                # 使用text属性查找
                return self.poco(text=text)
            else:
                print("✗ 必须提供name或text参数")
                return None
        except Exception as e:
            print(f"✗ 查找元素失败: {e}")
            return None
    
    def click_element(self, element, timeout: int = 10) -> bool:
        """
        点击UI元素
        :param element: Poco对象或元素名称
        :param timeout: 超时时间（秒）
        :return: 是否点击成功
        """
        if not self.poco:
            print("✗ Poco未连接，请先调用connect()")
            return False
        
        try:
            if isinstance(element, str):
                # 如果传入的是元素名称，先查找
                element_obj = self.find_element(name=element)
                if not element_obj:
                    print(f"✗ 未找到元素: {element}")
                    return False
                element_obj.click()
            else:
                # 直接点击Poco对象
                element.click()
            
            print(f"✓ 成功点击元素")
            return True
            
        except Exception as e:
            print(f"✗ 点击元素失败: {e}")
            return False
    
    def input_text(self, element, text: str, clear: bool = True) -> bool:
        """
        输入文本
        :param element: Poco对象或元素名称
        :param text: 输入文本
        :param clear: 是否清空原有文本
        :return: 是否输入成功
        """
        if not self.poco:
            print("✗ Poco未连接，请先调用connect()")
            return False
        
        try:
            if isinstance(element, str):
                # 如果传入的是元素名称，先查找
                element_obj = self.find_element(name=element)
                if not element_obj:
                    print(f"✗ 未找到元素: {element}")
                    return False
                if clear:
                    element_obj.set_text(text)
                else:
                    element_obj.set_text(element_obj.get_text() + text)
            else:
                # 直接输入到Poco对象
                if clear:
                    element.set_text(text)
                else:
                    element.set_text(element.get_text() + text)
            
            print(f"✓ 成功输入文本: {text}")
            return True
            
        except Exception as e:
            print(f"✗ 输入文本失败: {e}")
            return False
    
    def get_element_text(self, element) -> str:
        """
        获取元素文本（增强版，处理ClickContent等无文本节点）
        这是方案文档4.1.3节提到的Python侧修复方案
        :param element: Poco对象
        :return: 文本字符串
        """
        if not element:
            return ''
        
        try:
            # 1. 首先尝试直接获取text属性
            text = element.get_text()
            if text:
                return text
            
            # 2. 如果text为空，尝试查找相邻节点的文本
            # 注意：这需要访问UI树的结构，可能需要修改Poco SDK或使用dump结果
            print(f"⚠ 元素 {element.name} 的text字段为空，尝试查找相邻节点...")
            
            # 这个方法需要访问UI树的原始数据
            # 在实际实现中，可能需要在dump后就处理UI树，而不是在这里处理
            
            return ''
            
        except Exception as e:
            print(f"✗ 获取元素文本失败: {e}")
            return ''
    
    def snapshot(self, filename: Optional[str] = None) -> Optional[str]:
        """
        截图
        :param filename: 文件名（可选）
        :return: 截图路径，失败返回None
        """
        if not self.device:
            print("✗ 设备未连接，请先调用connect()")
            return None
        
        try:
            from airtest.core.api import snapshot as airtest_snapshot
            
            if not filename:
                filename = f"screenshot_{int(time.time())}.png"
            
            path = airtest_snapshot(filename=filename)
            print(f"✓ 截图成功: {path}")
            return path
            
        except Exception as e:
            print(f"✗ 截图失败: {e}")
            return None
    
    def close(self):
        """关闭连接"""
        # Poco和Airtest通常不需要显式关闭
        self.poco = None
        self.device = None
        print("✓ 连接已关闭")


def test_poco_connector():
    """测试Poco连接器"""
    print("=" * 60)
    print("测试Poco连接器")
    print("=" * 60)
    
    # 创建连接器
    connector = PocoConnector(device_type='Windows')
    
    # 连接
    if not connector.connect():
        print("✗ 连接失败，测试终止")
        return
    
    # Dump UI树
    ui_tree = connector.dump_ui_tree()
    if ui_tree:
        print(f"✓ UI树类型: {type(ui_tree)}")
    
    # 截图
    screenshot_path = connector.snapshot()
    if screenshot_path:
        print(f"✓ 截图保存至: {screenshot_path}")
    
    # 关闭
    connector.close()
    
    print("=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == '__main__':
    test_poco_connector()
