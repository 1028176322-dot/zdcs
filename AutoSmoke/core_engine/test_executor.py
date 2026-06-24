"""
# -*- coding: utf-8 -*-
测试执行器 - 连接Unity并执行测试步骤
支持点击、输入、等待、验证等操作
"""

import time
import re
from datetime import datetime
from airtest.core.api import connect_device, sleep
from poco.drivers.unity3d import UnityPoco
from poco.exceptions import PocoTargetTimeout

class TestExecutor:
    """测试执行器"""
    
    def __init__(self, config):
        """初始化测试执行器"""
        self.config = config
        self.poco = None
        self.device = None
        self.screenshot_dir = None
        self.protocol_watcher = None
        
    def connect(self):
        """连接Unity游戏"""
        try:
            # 连接Windows设备
            device_uri = f"Windows:///?title_re=Unity.*"
            self.device = connect_device(device_uri)
            
            # 连接Poco
            self.poco = UnityPoco(('localhost', self.config.poco_port), self.device)
            
            # 初始化协议监视器
            from net_monitor_watcher import NetMonitorWatcher
            self.protocol_watcher = NetMonitorWatcher(self.config.log_path)
            
            # 创建截图目录
            self.screenshot_dir = self.config.screenshot_dir
            import os
            os.makedirs(self.screenshot_dir, exist_ok=True)
            
            print("✅ Unity连接成功")
            return True
            
        except Exception as e:
            print(f"❌ Unity连接失败: {e}")
            return False
    
    def execute_step(self, step):
        """执行单个测试步骤"""
        result = {
            'success': False,
            'message': '',
            'protocols': [],
            'screenshot': None
        }
        
        action = step['action']
        step_type = step['type']
        
        try:
            if step_type == 'click':
                result = self._execute_click(action)
            elif step_type == 'input':
                result = self._execute_input(action)
            elif step_type == 'wait':
                result = self._execute_wait(action)
            elif step_type == 'verify':
                result = self._execute_verify(action)
            elif step_type == 'screenshot':
                result = self._execute_screenshot(action)
            else:
                # 尝试作为点击操作执行
                result = self._execute_click(action)
                
        except PocoTargetTimeout as e:
            result['message'] = f"元素超时: {e}"
        except Exception as e:
            result['message'] = f"执行出错: {e}"
        
        return result
    
    def _execute_click(self, action):
        """执行点击操作"""
        result = {'success': False, 'message': '', 'protocols': [], 'screenshot': None}
        
        # 解析点击目标
        target = self._parse_click_target(action)
        
        if not target:
            result['message'] = f"无法解析点击目标: {action}"
            return result
        
        try:
            # 清空协议日志
            self.protocol_watcher.clear()
            
            # 查找并点击元素
            if self.poco(target).exists():
                self.poco(target).click()
                result['success'] = True
                result['message'] = f"成功点击: {target}"
                
                # 等待协议响应
                time.sleep(self.config.protocol_wait_timeout)
                
                # 获取协议消息
                result['protocols'] = [msg.__dict__ for msg in self.protocol_watcher.poll()]
                
                # 截图
                screenshot_path = self._take_screenshot(f"click_{target}")
                result['screenshot'] = screenshot_path
                
            else:
                result['message'] = f"元素不存在: {target}"
                
        except Exception as e:
            result['message'] = f"点击失败: {e}"
        
        return result
    
    def _execute_input(self, action):
        """执行输入操作"""
        result = {'success': False, 'message': '', 'protocols': [], 'screenshot': None}
        
        # 解析输入目标和文本
        target, text = self._parse_input_action(action)
        
        if not target or not text:
            result['message'] = f"无法解析输入操作: {action}"
            return result
        
        try:
            # 清空协议日志
            self.protocol_watcher.clear()
            
            # 查找元素并输入文本
            if self.poco(target).exists():
                self.poco(target).set_text(text)
                result['success'] = True
                result['message'] = f"成功输入文本: {text} 到 {target}"
                
                # 等待协议响应
                time.sleep(self.config.protocol_wait_timeout)
                
                # 获取协议消息
                result['protocols'] = [msg.__dict__ for msg in self.protocol_watcher.poll()]
                
                # 截图
                screenshot_path = self._take_screenshot(f"input_{target}")
                result['screenshot'] = screenshot_path
                
            else:
                result['message'] = f"元素不存在: {target}"
                
        except Exception as e:
            result['message'] = f"输入失败: {e}"
        
        return result
    
    def _execute_wait(self, action):
        """执行等待操作"""
        result = {'success': False, 'message': '', 'protocols': [], 'screenshot': None}
        
        # 解析等待时间
        wait_time = self._parse_wait_time(action)
        
        try:
            time.sleep(wait_time)
            result['success'] = True
            result['message'] = f"等待 {wait_time} 秒"
                
        except Exception as e:
            result['message'] = f"等待失败: {e}"
        
        return result
    
    def _execute_verify(self, action):
        """执行验证操作"""
        result = {'success': False, 'message': '', 'protocols': [], 'screenshot': None}
        
        # 解析验证目标
        target = self._parse_verify_target(action)
        
        if not target:
            result['message'] = f"无法解析验证目标: {action}"
            return result
        
        try:
            # 验证元素是否存在
            if self.poco(target).exists():
                result['success'] = True
                result['message'] = f"验证成功: {target} 存在"
            else:
                result['message'] = f"验证失败: {target} 不存在"
                
            # 截图
            screenshot_path = self._take_screenshot(f"verify_{target}")
            result['screenshot'] = screenshot_path
                
        except Exception as e:
            result['message'] = f"验证失败: {e}"
        
        return result
    
    def _execute_screenshot(self, action):
        """执行截图操作"""
        result = {'success': False, 'message': '', 'protocols': [], 'screenshot': None}
        
        try:
            # 解析截图文件名
            filename = self._parse_screenshot_filename(action)
            
            # 截图
            screenshot_path = self._take_screenshot(filename)
            result['success'] = True
            result['message'] = f"截图成功: {screenshot_path}"
            result['screenshot'] = screenshot_path
                
        except Exception as e:
            result['message'] = f"截图失败: {e}"
        
        return result
    
    def _parse_click_target(self, action):
        """解析点击目标"""
        # 移除点击关键词
        target = re.sub(r'(点击|click|触摸|tap)', '', action, flags=re.IGNORECASE)
        target = target.strip()
        
        # 如果目标为空，尝试使用整个动作作为目标
        if not target:
            target = action
        
        return target
    
    def _parse_input_action(self, action):
        """解析输入操作"""
        # 匹配 "输入XXX到YYY" 或 "在YYY中输入XXX" 格式
        patterns = [
            r'输入(.+?)到(.+)$',
            r'在(.+?)中输入(.+)$',
            r'输入(.+)$'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, action)
            if match:
                if len(match.groups()) == 2:
                    return match.group(2).strip(), match.group(1).strip()
                else:
                    return 'input_field', match.group(1).strip()
        
        return None, None
    
    def _parse_wait_time(self, action):
        """解析等待时间"""
        # 匹配数字+N秒格式
        match = re.search(r'(\d+)\s*秒', action)
        if match:
            return int(match.group(1))
        
        # 匹配数字+分钟格式
        match = re.search(r'(\d+)\s*分钟', action)
        if match:
            return int(match.group(1)) * 60
        
        # 默认等待时间
        return self.config.default_wait_timeout
    
    def _parse_verify_target(self, action):
        """解析验证目标"""
        # 移除验证关键词
        target = re.sub(r'(检查|验证|断言|assert|check|verify)', '', action, flags=re.IGNORECASE)
        target = target.strip()
        
        # 如果目标为空，尝试使用整个动作作为目标
        if not target:
            target = action
        
        return target
    
    def _parse_screenshot_filename(self, action):
        """解析截图文件名"""
        # 移除截图关键词
        filename = re.sub(r'(截图|screenshot|捕获)', '', action, flags=re.IGNORECASE)
        filename = filename.strip()
        
        # 如果文件名为空，使用默认文件名
        if not filename:
            filename = f"screenshot_{int(time.time())}"
        
        return filename
    
    def _take_screenshot(self, name):
        """截图"""
        try:
            # 生成截图文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{name}_{timestamp}.png"
            filepath = os.path.join(self.screenshot_dir, filename)
            
            # 截图
            self.device.snapshot(filename=filepath)
            
            return filepath
            
        except Exception as e:
            print(f"截图失败: {e}")
            return None
