"""Fix CONFIG_DIR paths after file reorganization"""
import os
from AutoSmoke.path_utils import as_abs_path

ROOT = as_abs_path('')

files_to_fix = [
    '閮ㄧ讲宸ュ叿/deploy_tools.py',
    '鍧愭爣鎴浘/screenshot_game_content.py',
    '鍧愭爣鎴浘/screenshot_diff.py',
    '鍧愭爣鎴浘/resolution_manager.py',
    '鐐瑰嚮鎵ц/click_game_content.py',
    '鐐瑰嚮鎵ц/click_mode.py',
    '鐢ㄤ緥灞?case_step_executor.py',
    '鐢ㄤ緥灞?report_center.py',
    '鐢ㄤ緥灞?batch_runner.py',
    '瑙嗚璇嗗埆/game_content_vision.py',
    # debug_panel.py already has a different pattern
]

for rel_path in files_to_fix:
    full_path = os.path.join(ROOT, rel_path)
    if not os.path.exists(full_path):
        print(f'  鉂?涓嶅瓨鍦? {rel_path}')
        continue
    with open(full_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    old = "os.path.dirname(os.path.abspath(__file__))"
    new = "os.path.dirname(os.path.dirname(os.path.abspath(__file__)))"
    
    if old in content:
        content = content.replace(old, new)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'  鉁?宸蹭慨澶? {rel_path}')
    else:
        print(f'  鈿狅笍  妯″紡涓嶅尮閰? {rel_path}')

print('\n瀹屾垚')

