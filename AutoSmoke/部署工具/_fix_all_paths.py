"""统一修复所有路径问题：使用 path_utils 替代硬编码/目录深度计算"""
import os, re

ROOT = 'E:/zdcs/AutoSmoke'

# ========== Step 1: 修复主代码中的 CONFIG_DIR ==========
print('=== Step 1: 修复 CONFIG_DIR 使用 path_utils ===')

# 需要修复 CONFIG_DIR 的文件
files_config_dir = [
    '部署工具/deploy_tools.py',
    '坐标截图/coordinate_mapper.py',
    '视觉识别/game_content_vision.py',
    '坐标截图/resolution_manager.py',
    '坐标截图/screenshot_game_content.py',
    '坐标截图/screenshot_diff.py',
    '用例层/batch_runner.py',
    '用例层/case_step_executor.py',
    '用例层/report_center.py',
    '点击执行/click_mode.py',
    '点击执行/click_game_content.py',
]

for rel_path in files_config_dir:
    full = os.path.join(ROOT, rel_path)
    if not os.path.exists(full):
        continue
    with open(full, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    # 替换 CONFIG_DIR 行
    old = "os.path.dirname(os.path.dirname(os.path.abspath(__file__)))"
    new = "str(path_utils.AUTOSMOKE_ROOT)"
    if old in content:
        content = content.replace(old, new)
    else:
        # 尝试其他变体
        old2 = "os.path.dirname(os.path.abspath(__file__))"
        if old2 in content:
            content = content.replace(old2, new)

    # 添加 path_utils 导入
    if 'from path_utils import' not in content and 'import path_utils' not in content:
        # 找到 import 块末尾，插入 path_utils
        lines = content.split('\n')
        insert_pos = 0
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                insert_pos = i + 1
        # 再往后找空行
        while insert_pos < len(lines) and lines[insert_pos].strip():
            insert_pos += 1
        lines.insert(insert_pos, 'from path_utils import AUTOSMOKE_ROOT as CONFIG_DIR')
        content = '\n'.join(lines)

    # 移除旧的 CONFIG_DIR 行中重复赋值
    # 有些文件有 CONFIG_DIR = CONFIG_DIR（自我赋值）
    if 'CONFIG_DIR = CONFIG_DIR' in content:
        content = content.replace('CONFIG_DIR = CONFIG_DIR', 'CONFIG_DIR = str(path_utils.AUTOSMOKE_ROOT)')
        # 这句已不会出现，上面的替换已经处理

    if content != original:
        with open(full, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'  ✅ {rel_path}')
    else:
        print(f'  ⚠️  无需更改: {rel_path}')

# ========== Step 2: 修复 debug_panel.py 的 CONFIG_DIR ==========
print('\n=== Step 2: 修复 debug_panel.py ===')
dp_path = os.path.join(ROOT, 'ide', 'debug_panel.py')
# debug_panel already has a different pattern - it's at line 40 and 38
# Let me check what it currently has
with open(dp_path, 'r', encoding='utf-8') as f:
    content = f.read()

original = content

# Replace the old CONFIG_DIR with path_utils
old_cd = "CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))"
new_cd = "from path_utils import AUTOSMOKE_ROOT as CONFIG_DIR"
if old_cd in content:
    content = content.replace(old_cd, new_cd)
    # Also remove the old _script_dir/_project_root logic since we now use path_utils
    content = content.replace('''# 确保能找到项目模块（当前脚本在 IDE/ 下，项目根是父目录）
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_script_dir)
for p in [_project_root, _script_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)''', '''# 确保能找到项目模块
from path_utils import AUTOSMOKE_ROOT as _project_root
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))''')

if content != original:
    with open(dp_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('  ✅ ide/debug_panel.py')
else:
    print('  ⚠️  无需更改: ide/debug_panel.py')

# ========== Step 3: 修复旧脚本中的硬编码路径 ==========
print('\n=== Step 3: 修复旧脚本中的硬编码 E: 路径 ===')

legacy_dir = os.path.join(ROOT, '旧脚本')
for fname in os.listdir(legacy_dir):
    if not fname.endswith('.py'):
        continue
    fpath = os.path.join(legacy_dir, fname)
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    changed = False

    # 替换 sys.path.insert 中的硬编码
    if "sys.path.insert(0, 'E:/zdcs/AutoSmoke')" in content:
        content = content.replace(
            "sys.path.insert(0, 'E:/zdcs/AutoSmoke')",
            "import sys, os\nsys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))"
        )
        changed = True

    # 替换 Path('E:/zdcs/AutoSmoke/...') → 动态路径
    patterns = [
        ("Path('E:/zdcs/AutoSmoke/screenshots')", "Path(__file__).parent.parent / 'screenshots'"),
        ("Path('E:/zdcs/AutoSmoke/config.json')", "Path(__file__).parent.parent / 'config.json'"),
        ("'E:/zdcs/AutoSmoke/screenshots/'", "str(Path(__file__).parent.parent / 'screenshots'/"),
        ('"E:/zdcs/AutoSmoke/screenshots/', ''),
    ]
    for old_pat, new_pat in patterns:
        if old_pat in content:
            content = content.replace(old_pat, new_pat)
            changed = True

    # 替换 output_path 等中的 E:/zdcs/AutoSmoke/
    # 更通用的模式：替换 E:/zdcs/AutoSmoke/ 为动态路径
    # 但需要小心避免破坏其他内容
    e_paths = re.findall(r'["\']E:[/\\]zdcs[/\\]AutoSmoke[/\\]([^"\']*)["\']', content)
    for matched in e_paths:
        old_str = f'"E:/zdcs/AutoSmoke/{matched}"'
        # 构建动态路径
        path_parts = matched.strip('/\\').split('/')
        py_path = 'Path(__file__).parent.parent'
        for part in path_parts:
            py_path += f" / '{part}'"
        new_str = f'str({py_path})'
        if old_str in content:
            content = content.replace(old_str, new_str)
            changed = True
        old_str2 = f"'E:/zdcs/AutoSmoke/{matched}'"
        if old_str2 in content:
            content = content.replace(old_str2, new_str)
            changed = True

    # 添加必要的导入
    if changed and 'from pathlib import Path' not in content:
        # 在 import 块末尾添加
        lines = content.split('\n')
        insert_pos = 0
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                insert_pos = i + 1
        while insert_pos < len(lines) and lines[insert_pos].strip():
            insert_pos += 1
        if insert_pos > 0:
            lines.insert(insert_pos, 'from pathlib import Path')
            content = '\n'.join(lines)

    if content != original:
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'  ✅ {fname}')
    else:
        print(f'  - {fname}（无需更改）')

# ========== Step 4: 修复 archive 中的硬编码路径 ==========
print('\n=== Step 4: 修复 archive 中的硬编码路径 ===')

archive_dir = os.path.join(ROOT, 'archive')
for root_dir, dirs, files in os.walk(archive_dir):
    for fname in files:
        if not fname.endswith('.py'):
            continue
        fpath = os.path.join(root_dir, fname)
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read()

        original = content
        changed = False

        # 替换 E:/zdcs/AutoSmoke/ 硬编码路径
        e_paths = re.findall(r'["\']E:[/\\]zdcs[/\\]AutoSmoke[/\\]([^"\']*)["\']', content)
        for matched in e_paths:
            old_str = f'"E:/zdcs/AutoSmoke/{matched}"'
            path_parts = matched.strip('/\\').split('/')
            py_path = 'Path(__file__).parent.parent'
            for part in path_parts:
                py_path += f" / '{part}'"
            new_str = f'str({py_path})'
            if old_str in content:
                content = content.replace(old_str, new_str)
                changed = True
            old_str2 = f"'E:/zdcs/AutoSmoke/{matched}'"
            if old_str2 in content:
                content = content.replace(old_str2, new_str)
                changed = True

        # 替换 E:/s1/k3client/ 硬编码路径
        s_paths = re.findall(r'["\']E:[/\\]s1[/\\]k3client[^"\']*["\']', content)
        for old_path in s_paths:
            # 替换为 Path(__file__).parent / ... 的相对路径
            # 对于 Unity 项目路径，使用变量替换
            content = content.replace(old_path, '"UNITY_PROJECT_PATH"  # TODO: 从配置读取')
            changed = True

        # 添加 pathlib 导入
        if changed and 'from pathlib import Path' not in content:
            lines = content.split('\n')
            insert_pos = 0
            for i, line in enumerate(lines):
                if line.startswith('import ') or line.startswith('from '):
                    insert_pos = i + 1
            while insert_pos < len(lines) and lines[insert_pos].strip():
                insert_pos += 1
            if insert_pos > 0:
                lines.insert(insert_pos, 'from pathlib import Path')
                content = '\n'.join(lines)

        if content != original:
            with open(fpath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f'  ✅ {fname} ({os.path.relpath(fpath, ROOT)})')

print('\n=== 全部完成 ===')
