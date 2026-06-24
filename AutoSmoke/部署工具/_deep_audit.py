"""AutoSmoke 功能完整性深度审计"""
import os, sys, json, importlib, py_compile
from pathlib import Path

ROOT = Path('E:/zdcs/AutoSmoke')

# 核心模块清单（文档完成状态中的全部模块）
CORE_MODULES = {
    # 定位层
    '定位.locate_game_area_smart': 'GameView智能定位',
    '定位.game_view_locator': 'GameView坐标辅助',
    '定位.locate_active_region': '活跃区域定位',
    'core_engine.game_content_locator': 'GameContent三层定位',
    
    # 坐标截图
    '坐标截图.coordinate_mapper': '6种坐标互转',
    '坐标截图.screenshot_game_content': '纯游戏截图',
    '坐标截图.screenshot_diff': '截图差异对比',
    '坐标截图.resolution_manager': '动态分辨率',
    
    # 点击执行
    '点击执行.click_game_content': '点击执行器',
    '点击执行.click_mode': '点击模式抽象',
    
    # 用例层
    '用例层.case_step_parser': '步骤解析器',
    '用例层.case_step_executor': '步骤执行器',
    '用例层.batch_runner': '批量执行',
    '用例层.report_center': '报告中心',
    
    # 视觉识别
    '视觉识别.game_content_vision': 'OCR/模板匹配',
    
    # 阻塞处理
    '阻塞处理.blocker_rules': '阻塞规则',
    '阻塞处理.blocker_detector': '阻塞检测',
    '阻塞处理.blocker_resolver': '阻塞处理',
    '阻塞处理.post_action_guard': '守卫编排',
    '阻塞处理.ui_state_checker': '状态检查',
    
    # 元数据
    '元数据.metadata_reader': '元数据读取',
    '元数据.target_locator': '目标定位',
    '元数据.accessibility_scanner': '可测性扫描',
    '元数据.element_mapping': '元素映射',
    
    # 部署工具
    '部署工具.deploy_tools': '部署管理器',
    
    # IDE
    'IDE.debug_panel': '调试面板',
    
    # 根目录工具
    'config_manager': '配置管理',
    'path_utils': '路径工具',
}

results = {'ok': 0, 'fail': 0, 'warn': 0, 'details': []}

def check(module_path, description):
    """检查单个模块"""
    file_path = ROOT / (module_path.replace('.', '/') + '.py')
    if not file_path.exists():
        results['fail'] += 1
        results['details'].append(f'❌ {module_path} ({description}) 文件不存在')
        return
    
    issues = []
    
    # 1. 编译检查
    try:
        py_compile.compile(str(file_path), doraise=True)
    except py_compile.PyCompileError as e:
        issues.append(f'编译失败: {str(e)[:100]}')
    
    # 2. 硬编码路径检查
    text = file_path.read_text(encoding='utf-8')
    import re
    hardcoded = re.findall(r'["\'][A-Za-z]:[\\/][^"\']*["\']', text)
    hardcoded = [h for h in hardcoded if 'AutoSmoke' in h or 'k3client' in h]
    for h in hardcoded:
        issues.append(f'硬编码路径: {h[:50]}')
    
    # 3. 中文乱码检查
    if '?' * 3 in text or '\ufffd' in text:
        issues.append('含乱码字符')
    
    # 4. import 完整性 (检查 from xxx import yyy 中的 xxx 模块是否存在)
    for line in text.split('\n'):
        line = line.strip()
        if line.startswith('from ') and ' import ' in line:
            module_part = line.split(' import ')[0].replace('from ', '').strip()
            # 检查本地模块引用
            parts = module_part.split('.')
            if len(parts) >= 2 and parts[0] in ['定位','坐标截图','点击执行','用例层','元数据','视觉识别','阻塞处理','IDE','部署工具']:
                local_path = ROOT / f"{module_part.replace('.', '/')}.py"
                if not local_path.exists():
                    # Try __init__.py
                    local_path = ROOT / module_part.replace('.', '/') / '__init__.py'
                    if not local_path.exists():
                        issues.append(f'导入模块不存在: {module_part}')
    
    if not issues:
        results['ok'] += 1
        results['details'].append(f'✅ {module_path} ({description})')
    else:
        results['fail'] += 1
        results['details'].append(f'❌ {module_path}: {"; ".join(issues[:3])}')

print('=' * 60)
print('AutoSmoke 功能完整性深度审计')
print(f'共 {len(CORE_MODULES)} 个核心模块')
print('=' * 60)

for module_path, desc in CORE_MODULES.items():
    check(module_path, desc)

print(f'\n{"=" * 60}')
print(f'结果: ✅ {results["ok"]} 通过, ❌ {results["fail"]} 失败')
print(f'{"=" * 60}')

if results['fail'] > 0:
    print('\n失败详情:')
    for d in results['details']:
        if '❌' in d:
            print(f'  {d}')
