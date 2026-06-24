"""
配置文件 - 自动化测试执行系统
包含Unity连接参数、Poco配置、报告输出目录等
"""

import os

class Config:
    """配置类"""
    
    def __init__(self, config_path=None):
        """初始化配置"""
        # 如果提供了配置文件路径，则从文件加载配置
        if config_path and os.path.exists(config_path):
            self._load_from_file(config_path)
        else:
            self._set_defaults()
    
    def _set_defaults(self):
        """设置默认配置"""
        # Unity连接配置
        self.unity_ip = 'localhost'
        self.unity_port = 5001
        self.poco_port = 5001
        
        # 测试执行配置
        self.default_wait_timeout = 3  # 默认等待时间（秒）
        self.protocol_wait_timeout = 2  # 协议等待超时时间（秒）
        self.step_timeout = 10  # 步骤执行超时时间（秒）
        
        # 目录配置
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.report_dir = os.path.join(self.base_dir, 'reports')
        self.screenshot_dir = os.path.join(self.base_dir, 'screenshots')
        self.log_dir = os.path.join(self.base_dir, 'logs')
        self.template_dir = os.path.join(self.base_dir, 'templates')
        
        # 日志文件路径
        self.log_path = os.path.join(self.log_dir, 'net_messages.log')
        
        # 网络消息监控配置
        self.net_monitor_enabled = True
        self.net_monitor_log_path = self.log_path
        
        # 截图配置
        self.screenshot_enabled = True
        self.screenshot_format = 'png'  # png 或 jpg
        self.screenshot_quality = 80  # jpg质量（1-100）
        
        # 报告配置
        self.report_enabled = True
        self.report_format = 'html'  # html 或 excel
        self.report_include_screenshots = True
        self.report_include_protocols = True
        
        # 测试执行配置
        self.stop_on_failure = False  # 失败时是否停止执行
        self.continue_on_error = True   # 出错时是否继续执行
        self.retry_count = 3            # 失败重试次数
        self.retry_interval = 1         # 重试间隔（秒）
        
        # 日志配置
        self.log_enabled = True
        self.log_level = 'INFO'  # DEBUG, INFO, WARNING, ERROR
        self.log_file = os.path.join(self.log_dir, 'test_execution.log')
        
        # 邮件通知配置（可选）
        self.email_enabled = False
        self.email_sender = ''
        self.email_password = ''
        self.email_smtp_server = 'smtp.example.com'
        self.email_smtp_port = 587
        self.email_receivers = []
        
    def _load_from_file(self, config_path):
        """从配置文件加载配置"""
        import json
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # 设置配置
            self.unity_ip = config_data.get('unity_ip', self.unity_ip)
            self.unity_port = config_data.get('unity_port', self.unity_port)
            self.poco_port = config_data.get('poco_port', self.poco_port)
            
            self.default_wait_timeout = config_data.get('default_wait_timeout', self.default_wait_timeout)
            self.protocol_wait_timeout = config_data.get('protocol_wait_timeout', self.protocol_wait_timeout)
            self.step_timeout = config_data.get('step_timeout', self.step_timeout)
            
            self.report_dir = config_data.get('report_dir', self.report_dir)
            self.screenshot_dir = config_data.get('screenshot_dir', self.screenshot_dir)
            self.log_dir = config_data.get('log_dir', self.log_dir)
            self.template_dir = config_data.get('template_dir', self.template_dir)
            
            self.log_path = config_data.get('log_path', self.log_path)
            
            self.net_monitor_enabled = config_data.get('net_monitor_enabled', self.net_monitor_enabled)
            self.net_monitor_log_path = config_data.get('net_monitor_log_path', self.net_monitor_log_path)
            
            self.screenshot_enabled = config_data.get('screenshot_enabled', self.screenshot_enabled)
            self.screenshot_format = config_data.get('screenshot_format', self.screenshot_format)
            self.screenshot_quality = config_data.get('screenshot_quality', self.screenshot_quality)
            
            self.report_enabled = config_data.get('report_enabled', self.report_enabled)
            self.report_format = config_data.get('report_format', self.report_format)
            self.report_include_screenshots = config_data.get('report_include_screenshots', self.report_include_screenshots)
            self.report_include_protocols = config_data.get('report_include_protocols', self.report_include_protocols)
            
            self.stop_on_failure = config_data.get('stop_on_failure', self.stop_on_failure)
            self.continue_on_error = config_data.get('continue_on_error', self.continue_on_error)
            self.retry_count = config_data.get('retry_count', self.retry_count)
            self.retry_interval = config_data.get('retry_interval', self.retry_interval)
            
            self.log_enabled = config_data.get('log_enabled', self.log_enabled)
            self.log_level = config_data.get('log_level', self.log_level)
            self.log_file = config_data.get('log_file', self.log_file)
            
            self.email_enabled = config_data.get('email_enabled', self.email_enabled)
            self.email_sender = config_data.get('email_sender', self.email_sender)
            self.email_password = config_data.get('email_password', self.email_password)
            self.email_smtp_server = config_data.get('email_smtp_server', self.email_smtp_server)
            self.email_smtp_port = config_data.get('email_smtp_port', self.email_smtp_port)
            self.email_receivers = config_data.get('email_receivers', self.email_receivers)
            
            print(f"✅ 配置已从 {config_path} 加载")
            
        except Exception as e:
            print(f"❌ 加载配置文件失败: {e}")
            self._set_defaults()
    
    def save_to_file(self, config_path=None):
        """保存配置到文件"""
        import json
        
        if not config_path:
            config_path = os.path.join(self.base_dir, 'config.json')
        
        try:
            config_data = {
                'unity_ip': self.unity_ip,
                'unity_port': self.unity_port,
                'poco_port': self.poco_port,
                
                'default_wait_timeout': self.default_wait_timeout,
                'protocol_wait_timeout': self.protocol_wait_timeout,
                'step_timeout': self.step_timeout,
                
                'report_dir': self.report_dir,
                'screenshot_dir': self.screenshot_dir,
                'log_dir': self.log_dir,
                'template_dir': self.template_dir,
                
                'log_path': self.log_path,
                
                'net_monitor_enabled': self.net_monitor_enabled,
                'net_monitor_log_path': self.net_monitor_log_path,
                
                'screenshot_enabled': self.screenshot_enabled,
                'screenshot_format': self.screenshot_format,
                'screenshot_quality': self.screenshot_quality,
                
                'report_enabled': self.report_enabled,
                'report_format': self.report_format,
                'report_include_screenshots': self.report_include_screenshots,
                'report_include_protocols': self.report_include_protocols,
                
                'stop_on_failure': self.stop_on_failure,
                'continue_on_error': self.continue_on_error,
                'retry_count': self.retry_count,
                'retry_interval': self.retry_interval,
                
                'log_enabled': self.log_enabled,
                'log_level': self.log_level,
                'log_file': self.log_file,
                
                'email_enabled': self.email_enabled,
                'email_sender': self.email_sender,
                'email_password': self.email_password,
                'email_smtp_server': self.email_smtp_server,
                'email_smtp_port': self.email_smtp_port,
                'email_receivers': self.email_receivers,
            }
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=4)
            
            print(f"✅ 配置已保存到 {config_path}")
            return True
            
        except Exception as e:
            print(f"❌ 保存配置文件失败: {e}")
            return False
    
    def create_directories(self):
        """创建必要的目录"""
        directories = [
            self.report_dir,
            self.screenshot_dir,
            self.log_dir,
            self.template_dir,
        ]
        
        for directory in directories:
            if directory and not os.path.exists(directory):
                try:
                    os.makedirs(directory, exist_ok=True)
                    print(f"✅ 创建目录: {directory}")
                except Exception as e:
                    print(f"❌ 创建目录失败 {directory}: {e}")
    
    def __str__(self):
        """返回配置的字符串表示"""
        return f"""
配置信息:
  Unity IP: {self.unity_ip}
  Unity 端口: {self.unity_port}
  Poco 端口: {self.poco_port}
  
  默认等待时间: {self.default_wait_timeout} 秒
  协议等待超时: {self.protocol_wait_timeout} 秒
  步骤执行超时: {self.step_timeout} 秒
  
  报告目录: {self.report_dir}
  截图目录: {self.screenshot_dir}
  日志目录: {self.log_dir}
  模板目录: {self.template_dir}
  
  日志文件路径: {self.log_path}
  
  网络监控: {'启用' if self.net_monitor_enabled else '禁用'}
  网络监控日志: {self.net_monitor_log_path}
  
  截图: {'启用' if self.screenshot_enabled else '禁用'}
  截图格式: {self.screenshot_format}
  截图质量: {self.screenshot_quality}
  
  报告: {'启用' if self.report_enabled else '禁用'}
  报告格式: {self.report_format}
  报告包含截图: {'是' if self.report_include_screenshots else '否'}
  报告包含协议: {'是' if self.report_include_protocols else '否'}
  
  失败时停止: {'是' if self.stop_on_failure else '否'}
  出错时继续: {'是' if self.continue_on_error else '否'}
  失败重试次数: {self.retry_count}
  重试间隔: {self.retry_interval} 秒
  
  日志: {'启用' if self.log_enabled else '禁用'}
  日志级别: {self.log_level}
  日志文件: {self.log_file}
  
  邮件通知: {'启用' if self.email_enabled else '禁用'}
"""
