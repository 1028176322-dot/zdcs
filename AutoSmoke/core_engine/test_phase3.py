"""
# -*- coding: utf-8 -*-
测试执行器测试脚本
验证TestCase和TestExecutor的功能（无需Unity连接）
"""

import sys
import os
import json

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from action_executor.action_executor import TestCase, TestExecutor


def test_test_case():
    """测试TestCase类"""
    print("=" * 80)
    print("测试TestCase类")
    print("=" * 80)
    
    # 创建测试用例
    case = TestCase(case_id='TC001', name='点击按钮测试', description='测试按钮点击功能')
    
    # 添加步骤
    case.add_step('click', 'Button', '', 10)
    case.add_step('wait', 'Panel', '', 5)
    case.add_step('assert', '', '按钮已点击', 10)
    
    print(f"✓ 创建测试用例: {case.case_id} - {case.name}")
    print(f"  描述: {case.description}")
    print(f"  步骤数: {len(case.steps)}")
    
    # 打印步骤
    print("\n  步骤详情：")
    for i, step in enumerate(case.steps, 1):
        print(f"    {i}. {step['action']} {step['target']} {step['value']} (timeout={step['timeout']}秒)")
    
    # 转换为字典
    case_dict = case.to_dict()
    print(f"\n✓ 转换为字典: {len(case_dict)} 个字段")
    
    # 从字典恢复
    case2 = TestCase.from_dict(case_dict)
    print(f"✓ 从字典恢复: {case2.case_id} - {case2.name}")
    print(f"  步骤数: {len(case2.steps)}")
    
    print("\n" + "=" * 80)
    print("TestCase类测试完成")
    print("=" * 80)
    
    return case


def test_load_test_cases():
    """测试加载测试用例"""
    print("\n" + "=" * 80)
    print("测试加载测试用例")
    print("=" * 80)
    
    # 从JSON文件加载
    json_file = '../data_access/test_cases.json'
    
    if not os.path.exists(json_file):
        print(f"✗ 文件不存在: {json_file}")
        return None
    
    # 创建PocoConnector（mock）
    class MockConnector:
        def __init__(self):
            self.poco = None
            self.device = None
    
    mock_connector = MockConnector()
    
    # 创建TestExecutor
    executor = TestExecutor(mock_connector)
    
    # 加载测试用例
    if executor.load_test_cases(json_file):
        print(f"✓ 成功加载 {len(executor.test_cases)} 个测试用例")
        
        # 打印测试用例
        print("\n  测试用例列表：")
        print("-" * 80)
        print(f"{'序号':<6} {'用例ID':<12} {'名称':<30} {'步骤数':<8}")
        print("-" * 80)
        
        for i, case in enumerate(executor.test_cases, 1):
            print(f"{i:<6} {case.case_id:<12} {case.name:<30} {len(case.steps):<8}")
        
        print("-" * 80)
        
        # 打印第一个用例的详细步骤
        if executor.test_cases:
            first_case = executor.test_cases[0]
            print(f"\n  用例详情: {first_case.case_id} - {first_case.name}")
            print(f"  描述: {first_case.description}")
            print(f"  步骤详情：")
            for j, step in enumerate(first_case.steps, 1):
                print(f"    {j}. {step['action']} {step['target']} {step['value']}")
        
        return executor
    else:
        print(f"✗ 加载测试用例失败")
        return None


def test_export_results():
    """测试导出结果"""
    print("\n" + "=" * 80)
    print("测试导出结果")
    print("=" * 80)
    
    # 创建模拟结果
    class MockConnector:
        def __init__(self):
            self.poco = None
            self.device = None
    
    mock_connector = MockConnector()
    executor = TestExecutor(mock_connector)
    
    # 创建测试用例
    case1 = TestCase(case_id='TC001', name='测试1')
    case1.add_step('click', 'Button')
    case1.result = True
    case1.error_message = ''
    
    case2 = TestCase(case_id='TC002', name='测试2')
    case2.add_step('input', 'InputField', '测试文本')
    case2.result = False
    case2.error_message = '断言失败: 期望文本未找到'
    
    executor.test_cases = [case1, case2]
    executor.results = [
        {'case_id': case1.case_id, 'name': case1.name, 'result': case1.result, 'error_message': case1.error_message},
        {'case_id': case2.case_id, 'name': case2.name, 'result': case2.result, 'error_message': case2.error_message}
    ]
    
    # 导出为JSON
    json_file = '../data_access/reports/test_results.json'
    os.makedirs(os.path.dirname(json_file), exist_ok=True)
    executor.export_results(json_file)
    
    # 导出为HTML
    html_file = '../data_access/reports/test_report.html'
    executor.export_results(html_file)
    
    print("\n" + "=" * 80)
    print("导出结果测试完成")
    print("=" * 80)


def create_sample_excel():
    """创建示例Excel测试用例文件"""
    print("\n" + "=" * 80)
    print("创建示例Excel测试用例文件")
    print("=" * 80)
    
    try:
        import pandas as pd
        
        # 创建测试用例数据
        data = [
            ['TC001', '点击探险家试炼', '测试点击功能', 'click', 'ClickContent', ''],
            ['TC002', '输入文本测试', '测试输入功能', 'input', 'InputField', '测试文本'],
            ['TC003', '滑动屏幕测试', '测试滑动功能', 'swipe', '', '0.5,0.8,0.5,0.2'],
            ['TC004', '等待元素测试', '测试等待功能', 'wait', 'Panel', ''],
            ['TC005', '断言文本测试', '测试断言功能', 'assert', '', '探险家试炼']
        ]
        
        df = pd.DataFrame(data, columns=['用例ID', '用例名称', '用例描述', '动作', '目标', '值'])
        
        # 保存为Excel
        excel_file = '../data_access/test_cases.xlsx'
        os.makedirs(os.path.dirname(excel_file), exist_ok=True)
        df.to_excel(excel_file, index=False)
        
        print(f"✓ Excel文件已创建: {excel_file}")
        print(f"  共 {len(data)} 个测试用例")
        
    except ImportError:
        print("⚠ pandas未安装，无法创建Excel文件")
        print("  请运行: pip install pandas openpyxl")
    
    print("\n" + "=" * 80)


if __name__ == '__main__':
    # 测试TestCase类
    case = test_test_case()
    
    # 测试加载测试用例
    executor = test_load_test_cases()
    
    # 测试导出结果
    test_export_results()
    
    # 创建示例Excel文件
    create_sample_excel()
    
    print("\n所有测试完成！")
