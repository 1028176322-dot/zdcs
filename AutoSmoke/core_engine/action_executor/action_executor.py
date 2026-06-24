"""
动作执行器模块
按照方案文档4.3节的接口定义实现
"""

import time
import os
import json
from typing import Optional, Tuple, Dict, Any, List


class ActionExecutor:
    """
    动作执行器
    执行各种UI交互操作（点击、输入、滑动等）
    """
    
    def __init__(self, poco_connector):
        """
        初始化动作执行器
        :param poco_connector: PocoConnector实例
        """
        self.connector = poco_connector
        self.poco = poco_connector.poco if poco_connector else None
        
    def click(self, element, timeout: int = 10) -> bool:
        """
        点击元素
        :param element: 元素名称或Poco对象
        :param timeout: 超时时间（秒）
        :return: 是否点击成功
        """
        if not self.poco:
            print("✗ Poco未连接，请先调用connector.connect()")
            return False
        
        try:
            if isinstance(element, str):
                # 如果传入的是元素名称，先查找
                poco_element = self.connector.find_element(name=element)
                if not poco_element:
                    print(f"✗ 未找到元素: {element}")
                    return False
                poco_element.click()
            else:
                # 直接点击Poco对象
                element.click()
            
            print(f"✓ 成功点击元素: {element if isinstance(element, str) else element.name}")
            return True
            
        except Exception as e:
            print(f"✗ 点击元素失败: {e}")
            return False
    
    def input(self, element, text: str, clear: bool = True) -> bool:
        """
        输入文本
        :param element: 输入框元素名称或Poco对象
        :param text: 输入文本
        :param clear: 是否清空原有文本
        :return: 是否输入成功
        """
        if not self.poco:
            print("✗ Poco未连接，请先调用connector.connect()")
            return False
        
        try:
            if isinstance(element, str):
                # 如果传入的是元素名称，先查找
                poco_element = self.connector.find_element(name=element)
                if not poco_element:
                    print(f"✗ 未找到元素: {element}")
                    return False
                
                if clear:
                    poco_element.set_text(text)
                else:
                    current_text = poco_element.get_text()
                    poco_element.set_text(current_text + text)
            else:
                # 直接输入到Poco对象
                if clear:
                    element.set_text(text)
                else:
                    current_text = element.get_text()
                    element.set_text(current_text + text)
            
            print(f"✓ 成功输入文本: {text}")
            return True
            
        except Exception as e:
            print(f"✗ 输入文本失败: {e}")
            return False
    
    def swipe(self, start_pos: Tuple[float, float], end_pos: Tuple[float, float], duration: float = 0.5) -> bool:
        """
        滑动屏幕
        :param start_pos: 起始位置 (x, y)，范围[0, 1]
        :param end_pos: 结束位置 (x, y)，范围[0, 1]
        :param duration: 滑动时长（秒）
        :return: 是否滑动成功
        """
        if not self.poco:
            print("✗ Poco未连接，请先调用connector.connect()")
            return False
        
        try:
            from airtest.core.api import swipe as airtest_swipe
            from airtest.core.api import loop_find
            
            # Airtest的swipe使用屏幕坐标（0-1范围）
            airtest_swipe(start_pos, end_pos, duration=duration)
            
            print(f"✓ 成功滑动: {start_pos} -> {end_pos}")
            return True
            
        except Exception as e:
            print(f"✗ 滑动失败: {e}")
            return False
    
    def wait(self, element_name: str, timeout: int = 10) -> Optional[Any]:
        """
        等待元素出现
        :param element_name: 元素名称
        :param timeout: 超时时间（秒）
        :return: Poco对象（成功）或None（超时）
        """
        if not self.poco:
            print("✗ Poco未连接，请先调用connector.connect()")
            return None
        
        try:
            poco_element = self.poco(element_name)
            poco_element.wait_for_appearance(timeout=timeout)
            
            print(f"✓ 元素已出现: {element_name}")
            return poco_element
            
        except Exception as e:
            print(f"✗ 等待元素超时: {element_name} ({timeout}秒)")
            return None
    
    def wait_disappear(self, element_name: str, timeout: int = 10) -> bool:
        """
        等待元素消失
        :param element_name: 元素名称
        :param timeout: 超时时间（秒）
        :return: 是否消失
        """
        if not self.poco:
            print("✗ Poco未连接，请先调用connector.connect()")
            return False
        
        try:
            poco_element = self.poco(element_name)
            poco_element.wait_for_disappearance(timeout=timeout)
            
            print(f"✓ 元素已消失: {element_name}")
            return True
            
        except Exception as e:
            print(f"✗ 等待元素消失超时: {element_name} ({timeout}秒)")
            return False
    
    def snapshot(self, filename: Optional[str] = None) -> Optional[str]:
        """
        截图
        :param filename: 文件名（可选）
        :return: 截图路径，失败返回None
        """
        return self.connector.snapshot(filename)
    
    def exists(self, element_name: str) -> bool:
        """
        检查元素是否存在
        :param element_name: 元素名称
        :return: 是否存在
        """
        if not self.poco:
            print("✗ Poco未连接，请先调用connector.connect()")
            return False
        
        try:
            poco_element = self.poco(element_name)
            return poco_element.exists()
        except Exception as e:
            return False
    
    def get_text(self, element_name: str) -> str:
        """
        获取元素文本
        :param element_name: 元素名称
        :return: 文本字符串，失败返回''
        """
        if not self.poco:
            print("✗ Poco未连接，请先调用connector.connect()")
            return ''
        
        try:
            poco_element = self.poco(element_name)
            return poco_element.get_text()
        except Exception as e:
            print(f"✗ 获取元素文本失败: {e}")
            return ''
    
    def assert_text(self, expected_text: str, element_name: Optional[str] = None, timeout: int = 10) -> bool:
        """
        断言文本存在（验证点）
        :param expected_text: 期望的文本
        :param element_name: 元素名称（可选，如果为None则搜索整个UI树）
        :param timeout: 超时时间（秒）
        :return: 是否断言成功
        """
        if not self.poco:
            print("✗ Poco未连接，请先调用connector.connect()")
            return False
        
        try:
            if element_name:
                # 检查指定元素的文本
                actual_text = self.get_text(element_name)
                if expected_text in actual_text:
                    print(f"✓ 断言成功: 期望='{expected_text}', 实际='{actual_text}'")
                    return True
                else:
                    print(f"✗ 断言失败: 期望='{expected_text}', 实际='{actual_text}'")
                    return False
            else:
                # 搜索整个UI树
                ui_tree = self.connector.dump_ui_tree()
                if not ui_tree:
                    return False
                
                from ui_processor.ui_tree_processor import UITreeProcessor
                processor = UITreeProcessor(ui_tree)
                all_texts = processor.extract_all_texts()
                
                for text in all_texts:
                    if expected_text in text:
                        print(f"✓ 断言成功: 在UI树中找到文本 '{expected_text}'")
                        return True
                
                print(f"✗ 断言失败: 未在UI树中找到文本 '{expected_text}'")
                return False
                
        except Exception as e:
            print(f"✗ 断言失败: {e}")
            return False


class TestCase:
    """
    测试用例类
    表示一个测试用例，包含多个测试步骤
    """
    
    def __init__(self, case_id: str, name: str, description: str = ''):
        """
        初始化测试用例
        :param case_id: 用例ID
        :param name: 用例名称
        :param description: 用例描述
        """
        self.case_id = case_id
        self.name = name
        self.description = description
        self.steps = []  # 测试步骤列表
        self.result = None  # 测试结果：None=未执行，True=通过，False=失败
        self.error_message = ''  # 错误信息
        
    def add_step(self, action: str, target: str, value: str = '', timeout: int = 10):
        """
        添加测试步骤
        :param action: 动作类型（click, input, swipe, wait, assert等）
        :param target: 目标元素
        :param value: 值（如输入文本、滑动终点等）
        :param timeout: 超时时间（秒）
        """
        step = {
            'action': action,
            'target': target,
            'value': value,
            'timeout': timeout
        }
        self.steps.append(step)
        
    def to_dict(self) -> Dict:
        """转换为字典（用于保存为JSON）"""
        return {
            'case_id': self.case_id,
            'name': self.name,
            'description': self.description,
            'steps': self.steps,
            'result': self.result,
            'error_message': self.error_message
        }
    
    @staticmethod
    def from_dict(data: Dict):
        """从字典创建（用于从JSON加载）"""
        case = TestCase(
            case_id=data.get('case_id', ''),
            name=data.get('name', ''),
            description=data.get('description', '')
        )
        case.steps = data.get('steps', [])
        case.result = data.get('result')
        case.error_message = data.get('error_message', '')
        return case


class TestExecutor:
    """
    测试执行器
    执行测试用例，记录结果
    """
    
    def __init__(self, poco_connector):
        """
        初始化测试执行器
        :param poco_connector: PocoConnector实例
        """
        self.connector = poco_connector
        self.executor = ActionExecutor(poco_connector)
        self.test_cases = []  # 测试用例列表
        self.results = []  # 执行结果列表
        
    def load_test_cases(self, filepath: str) -> bool:
        """
        加载测试用例（支持JSON、Excel格式）
        :param filepath: 文件路径
        :return: 是否加载成功
        """
        try:
            if filepath.endswith('.json'):
                return self._load_from_json(filepath)
            elif filepath.endswith(('.xlsx', '.xls')):
                return self._load_from_excel(filepath)
            else:
                print(f"✗ 不支持的文件格式: {filepath}")
                return False
        except Exception as e:
            print(f"✗ 加载测试用例失败: {e}")
            return False
    
    def _load_from_json(self, filepath: str) -> bool:
        """从JSON文件加载测试用例"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.test_cases = []
            for case_data in data.get('test_cases', []):
                case = TestCase.from_dict(case_data)
                self.test_cases.append(case)
            
            print(f"✓ 从JSON加载了 {len(self.test_cases)} 个测试用例")
            return True
            
        except Exception as e:
            print(f"✗ 从JSON加载失败: {e}")
            return False
    
    def _load_from_excel(self, filepath: str) -> bool:
        """从Excel文件加载测试用例"""
        try:
            import pandas as pd
            
            df = pd.read_excel(filepath)
            
            self.test_cases = []
            
            for _, row in df.iterrows():
                case = TestCase(
                    case_id=str(row.get('用例ID', '')),
                    name=str(row.get('用例名称', '')),
                    description=str(row.get('用例描述', ''))
                )
                
                # 解析步骤（假设步骤在单独的sheet中，或在同一行中用JSON表示）
                # 这里简化为：每个用例只有一个步骤
                step_action = str(row.get('动作', ''))
                step_target = str(row.get('目标', ''))
                step_value = str(row.get('值', ''))
                
                if step_action and step_target:
                    case.add_step(step_action, step_target, step_value)
                
                self.test_cases.append(case)
            
            print(f"✓ 从Excel加载了 {len(self.test_cases)} 个测试用例")
            return True
            
        except Exception as e:
            print(f"✗ 从Excel加载失败: {e}")
            return False
    
    def execute_all(self) -> List[Dict]:
        """
        执行所有测试用例
        :return: 执行结果列表
        """
        if not self.test_cases:
            print("⚠ 没有测试用例可执行")
            return []
        
        print(f"\n{'=' * 80}")
        print(f"开始执行 {len(self.test_cases)} 个测试用例")
        print(f"{'=' * 80}\n")
        
        self.results = []
        
        for i, case in enumerate(self.test_cases, 1):
            print(f"\n[用例 {i}/{len(self.test_cases)}] {case.case_id} - {case.name}")
            print("-" * 80)
            
            result = self.execute_case(case)
            self.results.append(result)
            
            status = "✓ 通过" if result['result'] else "✗ 失败"
            print(f"\n{status}: {result.get('error_message', '')}")
        
        # 打印汇总
        self._print_summary()
        
        return self.results
    
    def execute_case(self, case: TestCase) -> Dict:
        """
        执行单个测试用例
        :param case: 测试用例
        :return: 执行结果
        """
        for step_num, step in enumerate(case.steps, 1):
            action = step.get('action', '')
            target = step.get('target', '')
            value = step.get('value', '')
            timeout = step.get('timeout', 10)
            
            print(f"\n  步骤 {step_num}: {action} {target} {value}".strip())
            
            try:
                if action == 'click':
                    success = self.executor.click(target, timeout)
                elif action == 'input':
                    success = self.executor.input(target, value)
                elif action == 'swipe':
                    # value格式： "0.3,0.5,0.7,0.5" (start_x,start_y,end_x,end_y)
                    values = [float(v.strip()) for v in value.split(',')]
                    success = self.executor.swipe(
                        (values[0], values[1]),
                        (values[2], values[3])
                    )
                elif action == 'wait':
                    result = self.executor.wait(target, timeout)
                    success = result is not None
                elif action == 'assert':
                    success = self.executor.assert_text(value, target if target else None)
                else:
                    print(f"    ✗ 未知动作: {action}")
                    case.result = False
                    case.error_message = f"未知动作: {action}"
                    return {
                        'case_id': case.case_id,
                        'name': case.name,
                        'result': False,
                        'error_message': f"未知动作: {action}"
                    }
                
                if not success:
                    case.result = False
                    case.error_message = f"步骤 {step_num} 失败: {action} {target}"
                    return {
                        'case_id': case.case_id,
                        'name': case.name,
                        'result': False,
                        'error_message': case.error_message
                    }
                    
            except Exception as e:
                case.result = False
                case.error_message = f"步骤 {step_num} 异常: {e}"
                return {
                    'case_id': case.case_id,
                    'name': case.name,
                    'result': False,
                    'error_message': case.error_message
                }
        
        # 所有步骤执行成功
        case.result = True
        case.error_message = ''
        return {
            'case_id': case.case_id,
            'name': case.name,
            'result': True,
            'error_message': ''
        }
    
    def _print_summary(self):
        """打印执行汇总"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r['result'])
        failed = total - passed
        
        print(f"\n{'=' * 80}")
        print(f"执行汇总")
        print(f"{'=' * 80}")
        print(f"  总数: {total}")
        print(f"  通过: {passed}")
        print(f"  失败: {failed}")
        print(f"  通过率: {passed/total*100:.1f}%")
        print(f"{'=' * 80}\n")
    
    def export_results(self, filepath: str):
        """
        导出执行结果
        :param filepath: 文件路径（支持JSON、HTML格式）
        """
        try:
            if filepath.endswith('.json'):
                self._export_json(filepath)
            elif filepath.endswith('.html'):
                self._export_html(filepath)
            else:
                print(f"✗ 不支持的文件格式: {filepath}")
        except Exception as e:
            print(f"✗ 导出结果失败: {e}")
    
    def _export_json(self, filepath: str):
        """导出为JSON"""
        import json
        
        data = {
            'total': len(self.results),
            'passed': sum(1 for r in self.results if r['result']),
            'failed': sum(1 for r in self.results if not r['result']),
            'results': self.results
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✓ 结果已导出至: {filepath}")
    
    def _export_html(self, filepath: str):
        """导出为HTML报告"""
        # 简化实现：生成简单的HTML表格
        html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>测试报告</title>
    <style>
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        .pass {{ color: green; }}
        .fail {{ color: red; }}
    </style>
</head>
<body>
    <h1>测试报告</h1>
    <p>总数: {total}, 通过: {passed}, 失败: {failed}</p>
    <table>
        <tr>
            <th>用例ID</th>
            <th>名称</th>
            <th>结果</th>
            <th>错误信息</th>
        </tr>
        {rows}
    </table>
</body>
</html>"""
        
        rows = ''
        for r in self.results:
            status_class = 'pass' if r['result'] else 'fail'
            status_text = '通过' if r['result'] else '失败'
            rows += f"""
        <tr>
            <td>{r['case_id']}</td>
            <td>{r['name']}</td>
            <td class="{status_class}">{status_text}</td>
            <td>{r['error_message']}</td>
        </tr>"""
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r['result'])
        failed = total - passed
        
        html = html.format(
            total=total,
            passed=passed,
            failed=failed,
            rows=rows
        )
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"✓ 报告已导出至: {filepath}")


def test_action_executor():
    """测试动作执行器（需要Unity游戏运行）"""
    print("=" * 80)
    print("测试动作执行器")
    print("=" * 80)
    
    # 注意：这个测试需要Unity游戏运行
    # 这里只是演示接口使用
    
    print("\n⚠ 注意：这个测试需要Unity游戏运行")
    print("  请确保在Unity Editor中按Play按钮，或启动Standalone版本")
    
    # 创建连接器
    from core_engine.poco_connector.poco_connector import PocoConnector
    connector = PocoConnector(device_type='Windows')
    
    # 连接
    if not connector.connect():
        print("✗ 连接失败，测试终止")
        return
    
    # 创建动作执行器
    executor = ActionExecutor(connector)
    
    # 示例：点击按钮
    # executor.click('Button')
    
    # 示例：输入文本
    # executor.input('InputField', '测试文本')
    
    # 示例：等待元素
    # element = executor.wait('SomeElement')
    
    # 示例：断言文本
    # executor.assert_text('期望的文本')
    
    # 关闭连接
    connector.close()
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


def test_test_executor():
    """测试测试执行器"""
    print("=" * 80)
    print("测试测试执行器")
    print("=" * 80)
    
    # 创建测试用例
    case1 = TestCase(case_id='TC001', name='点击按钮测试')
    case1.add_step('click', 'Button')
    case1.add_step('assert', '', '按钮已点击')
    
    case2 = TestCase(case_id='TC002', name='输入文本测试')
    case2.add_step('input', 'InputField', '测试文本')
    case2.add_step('assert', 'InputField', '测试文本')
    
    # 保存为JSON
    import json
    test_data = {
        'test_cases': [case1.to_dict(), case2.to_dict()]
    }
    
    json_file = 'test_cases.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(test_data, f, ensure_ascii=False, indent=2)
    
    print(f"✓ 测试用例已保存至: {json_file}")
    
    # 加载测试用例
    from core_engine.action_executor.action_executor import TestExecutor
    from core_engine.poco_connector.poco_connector import PocoConnector
    
    connector = PocoConnector(device_type='Windows')
    executor = TestExecutor(connector)
    
    if executor.load_test_cases(json_file):
        print(f"✓ 成功加载测试用例")
        # 注意：这里不实际执行，因为需要Unity游戏运行
        print("⚠ 测试用例已加载，但不执行（需要Unity游戏运行）")
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


if __name__ == '__main__':
    # 测试动作执行器（需要Unity游戏运行）
    # test_action_executor()
    
    # 测试测试执行器（不需要Unity游戏运行）
    test_test_executor()
