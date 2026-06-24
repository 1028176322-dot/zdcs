# -*- coding: utf-8 -*-
"""AutoSmoke 脚本文件分类迁移脚本"""
import os, sys, shutil, json, glob
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 精确的文件 → 目录映射
FILE_MAP = {
    'locate_game_area_smart.py':    '定位',
    'game_content_locator.py':       '定位',
    'game_view_locator.py':          '定位',
    'locate_active_region.py':       '定位',
    'locate_game_area_simple.py':    '定位',
    'locate_game_area_winapi.py':    '定位',
    'detect_game_bottom.py':         '定位',
    'coordinate_mapper.py':          '坐标截图',
    'screenshot_game_content.py':    '坐标截图',
    'screenshot_diff.py':            '坐标截图',
    'resolution_manager.py':         '坐标截图',
    'click_game_content.py':         '点击执行',
    'click_mode.py':                 '点击执行',
    'simple_click_test.py':          '点击执行',
    'test_click_position.py':        '点击执行',
    'test_actual_click.py':          '点击执行',
    'case_step_parser.py':           '用例层',
    'case_step_executor.py':         '用例层',
    'batch_runner.py':               '用例层',
    'report_center.py':              '用例层',
    'metadata_reader.py':            '元数据',
    'target_locator.py':             '元数据',
    'accessibility_scanner.py':      '元数据',
    'element_mapping.py':            '元数据',
    'test_locate.py':                '元数据',
    'game_content_vision.py':        '视觉识别',
    'game_content_locator.py':       '定位',
    'blocker_rules.py':              '阻塞处理',
    'blocker_detector.py':           '阻塞处理',
    'blocker_resolver.py':           '阻塞处理',
    'post_action_guard.py':          '阻塞处理',
    'ui_state_checker.py':           '阻塞处理',
    'debug_panel.py':                'IDE',
    'deploy_tools.py':               '部署工具',
    'test_all_screens.py':           '旧脚本',
    'test_all_screens_simple.py':    '旧脚本',
    'test_secondary_screen.py':      '旧脚本',
    'test_secondary_screen_api.py':  '旧脚本',
    'test_secondary_screen_bitblt.py':'旧脚本',
    'test_secondary_screen_ctypes.py':'旧脚本',
    'test_secondary_screen_print.py':'旧脚本',
    'test_game_view_coords.py':      '旧脚本',
    'test_realtime_locator.py':      '旧脚本',
}

if __name__ == '__main__':
    for fname, category in sorted(FILE_MAP.items()):
        src = ROOT / fname
        dst_dir = ROOT / category
        dst_dir.mkdir(parents=True, exist_ok=True)
        init_file = dst_dir / '__init__.py'
        if not init_file.exists():
            init_file.write_text(f'# {category}\n', encoding='utf-8')
        if src.exists():
            shutil.move(str(src), str(dst_dir / fname))
            print(f'{fname} -> {category}/')
    print('Done')
