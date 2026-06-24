"""
# -*- coding: utf-8 -*-
测试报告生成器 - 生成HTML测试报告
支持测试结果统计、截图展示、协议信息展示
"""

import os
import json
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

class TestReporter:
    """测试报告生成器"""
    
    def __init__(self, report_dir):
        """初始化报告生成器"""
        self.report_dir = report_dir
        self.results = []
        
        # 确保报告目录存在
        os.makedirs(report_dir, exist_ok=True)
        
        # 创建截图子目录
        self.screenshot_dir = os.path.join(report_dir, 'screenshots')
        os.makedirs(self.screenshot_dir, exist_ok=True)
        
    def update_result(self, result):
        """更新测试结果"""
        self.results.append(result)
        
    def generate_report(self, results=None):
        """生成HTML测试报告"""
        if results is None:
            results = self.results
        
        if not results:
            print("没有测试结果可生成报告")
            return None
        
        print(f"正在生成测试报告，共 {len(results)} 个测试结果...")
        
        # 统计测试结果
        stats = self._calculate_stats(results)
        
        # 准备报告数据
        report_data = {
            'title': '自动化测试报告',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'stats': stats,
            'results': results,
            'screenshot_dir': 'screenshots'
        }
        
        # 生成HTML报告
        report_path = self._generate_html_report(report_data)
        
        print(f"✅ 测试报告已生成: {report_path}")
        return report_path
    
    def _calculate_stats(self, results):
        """计算测试结果统计"""
        stats = {
            'total': len(results),
            'passed': 0,
            'failed': 0,
            'errors': 0,
            'pass_rate': 0.0,
            'total_duration': 0.0
        }
        
        for result in results:
            # 统计状态
            status = result.get('status', 'FAIL')
            if status == 'PASS':
                stats['passed'] += 1
            elif status == 'FAIL':
                stats['failed'] += 1
            else:
                stats['errors'] += 1
            
            # 统计执行时间
            duration = result.get('duration', 0)
            if isinstance(duration, (int, float)):
                stats['total_duration'] += duration
        
        # 计算通过率
        if stats['total'] > 0:
            stats['pass_rate'] = round(stats['passed'] / stats['total'] * 100, 2)
        
        return stats
    
    def _generate_html_report(self, data):
        """生成HTML测试报告"""
        # 创建Jinja2环境
        env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
        
        # 定义HTML模板
        html_template = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .summary {
            background-color: white;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .stats {
            display: flex;
            justify-content: space-around;
            margin-top: 20px;
        }
        .stat-item {
            text-align: center;
            padding: 10px;
            border-radius: 5px;
            min-width: 120px;
        }
        .stat-item.passed {
            background-color: #d4edda;
            color: #155724;
        }
        .stat-item.failed {
            background-color: #f8d7da;
            color: #721c24;
        }
        .stat-item.errors {
            background-color: #fff3cd;
            color: #856404;
        }
        .stat-item.total {
            background-color: #d1ecf1;
            color: #0c5460;
        }
        .stat-value {
            font-size: 24px;
            font-weight: bold;
        }
        .stat-label {
            font-size: 14px;
            margin-top: 5px;
        }
        .test-case {
            background-color: white;
            padding: 15px;
            margin-bottom: 15px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .test-case.passed {
            border-left: 5px solid #28a745;
        }
        .test-case.failed {
            border-left: 5px solid #dc3545;
        }
        .test-case.error {
            border-left: 5px solid #ffc107;
        }
        .test-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
        }
        .test-name {
            font-size: 18px;
            font-weight: bold;
        }
        .test-status {
            padding: 5px 10px;
            border-radius: 3px;
            font-weight: bold;
        }
        .test-status.passed {
            background-color: #d4edda;
            color: #155724;
        }
        .test-status.failed {
            background-color: #f8d7da;
            color: #721c24;
        }
        .test-status.error {
            background-color: #fff3cd;
            color: #856404;
        }
        .test-details {
            margin-top: 10px;
            color: #666;
        }
        .test-details div {
            margin-bottom: 5px;
        }
        .screenshots {
            margin-top: 15px;
        }
        .screenshots img {
            max-width: 300px;
            max-height: 200px;
            margin-right: 10px;
            margin-bottom: 10px;
            border: 1px solid #ddd;
            border-radius: 3px;
        }
        .protocols {
            margin-top: 15px;
            background-color: #f8f9fa;
            padding: 10px;
            border-radius: 3px;
        }
        .protocol-item {
            margin-bottom: 5px;
            font-family: monospace;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <h1>{{ title }}</h1>
    <div class="summary">
        <h2>测试摘要</h2>
        <p>报告生成时间: {{ timestamp }}</p>
        <div class="stats">
            <div class="stat-item total">
                <div class="stat-value">{{ stats.total }}</div>
                <div class="stat-label">总测试用例</div>
            </div>
            <div class="stat-item passed">
                <div class="stat-value">{{ stats.passed }}</div>
                <div class="stat-label">通过</div>
            </div>
            <div class="stat-item failed">
                <div class="stat-value">{{ stats.failed }}</div>
                <div class="stat-label">失败</div>
            </div>
            <div class="stat-item errors">
                <div class="stat-value">{{ stats.errors }}</div>
                <div class="stat-label">错误</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{{ stats.pass_rate }}%</div>
                <div class="stat-label">通过率</div>
            </div>
        </div>
        <p>总执行时间: {{ "%.2f"|format(stats.total_duration) }} 秒</p>
    </div>
    
    <h2>测试用例详情</h2>
    {% for result in results %}
    <div class="test-case {{ result.status|lower }}">
        <div class="test-header">
            <div class="test-name">{{ result.name }}</div>
            <div class="test-status {{ result.status|lower }}">{{ result.status }}</div>
        </div>
        <div class="test-details">
            <div><strong>测试用例ID:</strong> {{ result.id }}</div>
            <div><strong>功能模块:</strong> {{ result.module }}</div>
            <div><strong>优先级:</strong> {{ result.priority }}</div>
            <div><strong>消息:</strong> {{ result.message }}</div>
            <div><strong>开始时间:</strong> {{ result.start_time }}</div>
            <div><strong>结束时间:</strong> {{ result.end_time }}</div>
            <div><strong>执行时间:</strong> {{ "%.2f"|format(result.duration) }} 秒</div>
            <div><strong>执行步骤:</strong> {{ result.steps_executed }}/{{ result.steps_total }}</div>
        </div>
        
        {% if result.screenshots %}
        <div class="screenshots">
            <h3>截图</h3>
            {% for screenshot in result.screenshots %}
            <img src="{{ screenshot_dir }}/{{ screenshot.split('/')[-1] }}" alt="Screenshot">
            {% endfor %}
        </div>
        {% endif %}
        
        {% if result.protocols %}
        <div class="protocols">
            <h3>协议消息</h3>
            {% for protocol in result.protocols %}
            <div class="protocol-item">{{ protocol.time }} | {{ protocol.dir }} | {{ protocol.type }}</div>
            {% endfor %}
        </div>
        {% endif %}
    </div>
    {% endfor %}
</body>
</html>
"""
        
        # 渲染HTML
        try:
            from jinja2 import Template
            template = Template(html_template)
            html_content = template.render(**data)
            
            # 保存HTML文件
            report_path = os.path.join(self.report_dir, 'test_report.html')
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # 复制截图到报告目录
            self._copy_screenshots(results)
            
            return report_path
            
        except Exception as e:
            print(f"生成HTML报告失败: {e}")
            return None
    
    def _copy_screenshots(self, results):
        """复制截图到报告目录"""
        import shutil
        
        for result in results:
            if result.get('screenshots'):
                for screenshot in result['screenshots']:
                    if screenshot and os.path.exists(screenshot):
                        try:
                            filename = os.path.basename(screenshot)
                            dest_path = os.path.join(self.screenshot_dir, filename)
                            shutil.copy2(screenshot, dest_path)
                        except Exception as e:
                            print(f"复制截图失败 {screenshot}: {e}")
    
    def generate_text_report(self, results=None):
        """生成文本格式测试报告"""
        if results is None:
            results = self.results
        
        if not results:
            return "没有测试结果"
        
        # 统计测试结果
        stats = self._calculate_stats(results)
        
        # 生成文本报告
        lines = []
        lines.append("=" * 50)
        lines.append("自动化测试报告")
        lines.append("=" * 50)
        lines.append(f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        lines.append("测试结果统计:")
        lines.append(f"  总测试用例: {stats['total']}")
        lines.append(f"  通过: {stats['passed']}")
        lines.append(f"  失败: {stats['failed']}")
        lines.append(f"  错误: {stats['errors']}")
        lines.append(f"  通过率: {stats['pass_rate']}%")
        lines.append(f"  总执行时间: {stats['total_duration']:.2f} 秒")
        lines.append("")
        lines.append("测试用例详情:")
        lines.append("-" * 50)
        
        for i, result in enumerate(results, 1):
            status_text = "✅ 通过" if result['status'] == 'PASS' else "❌ 失败"
            lines.append(f"{i}. {result['name']} - {status_text}")
            lines.append(f"   ID: {result['id']}")
            lines.append(f"   模块: {result['module']}")
            lines.append(f"   优先级: {result['priority']}")
            lines.append(f"   消息: {result['message']}")
            lines.append(f"   时间: {result['start_time']} - {result['end_time']}")
            lines.append(f"   执行时间: {result['duration']:.2f}秒")
            lines.append(f"   步骤: {result['steps_executed']}/{result['steps_total']}")
            
            if result.get('protocols'):
                lines.append(f"   协议消息: {len(result['protocols'])} 条")
            
            lines.append("")
        
        return "\n".join(lines)
