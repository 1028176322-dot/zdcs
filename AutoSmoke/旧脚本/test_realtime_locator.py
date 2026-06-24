#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时测试游戏画面定位
从Unity实时截取画面，检测游戏内容区域
"""

import sys
import os
import time
import json
import numpy as np

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import ImageGrab, Image, ImageDraw
from core_engine.game_content_locator import find_game_content_rect


def crop_game_view(full_img, coords):
    """按配置裁剪 GameView 区域。"""
    left, top, right, bottom = (
        int(coords['left']),
        int(coords['top']),
        int(coords['right']),
        int(coords['bottom'])
    )
    return full_img.crop((left, top, right, bottom)), (left, top, right, bottom)


def expand_game_view_bottom_if_needed(config, result, padding=4):
    """截图高度不足时，按 expectedContentBottom 反推并扩大第一层底部。"""
    if result.get('status') != 'GAME_VIEW_CAPTURE_TOO_SHORT':
        return False

    debug_info = result.get('debug_info') or {}
    expected_bottom = int(debug_info.get('expectedContentBottom', 0))
    panel_height = int(debug_info.get('panelImageHeight', 0))
    missing = expected_bottom - panel_height
    if missing <= 0:
        return False

    coords = config['game_view_coords']
    if coords.get('auto_expanded_bottom'):
        print('⚠️ GameView bottom 已自动扩展过，本次不再继续扩大。')
        return False

    old_bottom = int(coords['bottom'])
    new_bottom = old_bottom + missing + padding

    coords['bottom'] = new_bottom
    coords['height'] = new_bottom - int(coords['top'])
    coords['auto_expanded_bottom'] = True
    coords['expand_reason'] = (
        f"contentBottom={expected_bottom}, panelHeight={panel_height}, "
        f"missing={missing}, padding={padding}"
    )

    print(
        f"⚠️ GameView 截图高度不足，自动扩大 bottom: "
        f"{old_bottom} -> {new_bottom} (+{new_bottom - old_bottom}px)"
    )
    return True


def test_realtime():
    """实时测试"""
    
    # 读取配置
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 截取所有屏幕（实时）
    print('正在截取Unity实时画面...')
    full_img = ImageGrab.grab(all_screens=True)
    full_img_np = np.array(full_img)
    
    game_view_coords = config.get('game_view_coords')
    if not game_view_coords:
        print('❌ 未找到GameView坐标配置')
        return

    # 保存GameView截图
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    debug_dir = f'screenshots/debug_{timestamp}'
    os.makedirs(debug_dir, exist_ok=True)

    result = None
    game_view_img = None
    game_view_np = None

    for attempt in range(2):
        game_view_img, crop_box = crop_game_view(full_img, config['game_view_coords'])
        game_view_np = np.array(game_view_img)

        left, top, right, bottom = crop_box
        print(f'裁剪到GameView区域: ({left}, {top}, {right}, {bottom})')

        suffix = '' if attempt == 0 else '_expanded'
        game_view_path = f'{debug_dir}/game_view_realtime{suffix}.png'
        game_view_img.save(game_view_path)
        print(f'✅ GameView实时截图已保存: {game_view_path}')

        print('\n开始分析游戏画面区域...')
        result = find_game_content_rect(
            game_view_np,
            design_width=config.get('game_resolution', {}).get('width', 1170),
            design_height=config.get('game_resolution', {}).get('height', 2532),
            debug=True,
            debug_dir=debug_dir
        )

        config['game_content_result'] = result
        config['game_content_result']['timestamp'] = timestamp

        if attempt == 0 and expand_game_view_bottom_if_needed(config, result):
            continue

        if result.get('status') == 'GAME_VIEW_CAPTURE_TOO_SHORT':
            print('⚠️ 扩展后仍然高度不足，本次不再继续扩大 bottom，请检查内容区宽度/渲染区识别。')

        if not result:
            break
        break

    if result and result.get('gameContentRect'):
        print(f'\n✅ 游戏画面区域分析结果: {result}')

        content = result['gameContentRect']
        gc_left = int(content['left'])
        gc_top = int(content['top'])
        gc_right = gc_left + int(content['width'])
        gc_bottom = gc_top + int(content['height'])

        config['game_content_rect'] = {
            'left': gc_left,
            'top': gc_top,
            'right': gc_right,
            'bottom': gc_bottom,
            'width': gc_right - gc_left,
            'height': gc_bottom - gc_top,
            'timestamp': timestamp,
            'status': result.get('status')
        }

        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print('✅ 游戏画面区域与 GameView 坐标已保存到 config.json')

        # 在GameView截图中标注
        annotated_img = game_view_img.copy()
        draw = ImageDraw.Draw(annotated_img)
        
        # 标注工具栏区域（蓝色）
        draw.rectangle(
            [0, 0, game_view_np.shape[1], gc_top],
            outline=(0, 0, 255),
            width=3
        )
        
        # 标注内容区域（红色）
        draw.rectangle(
            [gc_left, gc_top, gc_right, gc_bottom],
            outline=(255, 0, 0),
            width=5
        )
        
        # 添加文字说明
        draw.text((gc_left, gc_top - 40), 
                 f'Toolbar: 0-{gc_top}',
                 fill=(0, 0, 255))
        draw.text((gc_left, gc_top - 20), 
                 f'Content: ({gc_left}, {gc_top}, {gc_right}, {gc_bottom})',
                 fill=(255, 0, 0))
        
        annotated_path = f'{debug_dir}/game_view_annotated_realtime.png'
        annotated_img.save(annotated_path)
        print(f'✅ 标注截图已保存: {annotated_path}')
        
        print(f'\n请查看这个文件确认位置：')
        print(f'{os.path.abspath(annotated_path)}')
    else:
        print('❌ 未找到游戏画面区域')


if __name__ == '__main__':
    test_realtime()
