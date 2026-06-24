"""Comprehensive fix for debug_panel.py corruption"""
import sys, re

src = 'E:/zdcs/AutoSmoke/IDE/debug_panel.py'

with open(src, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix all remaining corruption patterns

# Pattern 1: Known corrupted sequences (mojibake)
fixes = {
    '\u951d\u60a3\u620a\u6d9d': '坐标截图',  # 鍧愭爣鎴浘
    '\u7535\u544a\u5c51': '用例层',  # 鐢ㄤ緥灞
    '\u70b9\u51fb\u6267': '点击执行',  # 鐐瑰嚮鎵ц
    '\u5143\u6570\u636e': '元数据',  # 鍏冩暟鎹
    '\u963b\u585e\u5904\u7406': '阻塞处理',  # 闃诲澶勭悊
    '\u90e8\u7f72\u5de5\u5177': '部署工具',  # 閮ㄧ讲宸ュ叿
}

for corrupted, correct in fixes.items():
    if corrupted in content:
        count = content.count(corrupted)
        content = content.replace(corrupted, correct)
        print(f'  Fixed {corrupted} -> {correct} ({count}x)')

# Pattern 2: Any remaining chars in Unicode Private Use Area (U+E000-U+F8FF)
# These are left from the corruption
def has_private_use_area_char(s):
    for ch in s:
        if 0xE000 <= ord(ch) <= 0xF8FF:
            return True
    return False

# Check specific sections: imports first
lines = content.split('\n')
fixed_import_lines = 0
for i, line in enumerate(lines):
    if line.strip().startswith('from ') and 'import ' in line:
        # Extract the module path part
        parts = line.split(' import ')
        if len(parts) >= 1:
            module_part = parts[0].replace('from ', '').strip()
            # Check if module_path has Private Use Area chars
            for ch in module_part:
                if 0xE000 <= ord(ch) <= 0xF8FF:
                    # Replace with nothing (remove the corrupted char)
                    module_part_clean = module_part.replace(ch, '')
                    if '.' in module_part_clean.split('.')[-1]:
                        module_part_clean = module_part_clean.replace('..', '.')
                    new_line = line.replace(module_part, module_part_clean)
                    lines[i] = new_line
                    fixed_import_lines += 1
                    break

if fixed_import_lines:
    content = '\n'.join(lines)
    print(f'  Fixed {fixed_import_lines} import lines with PUA chars')

# Pattern 3: Any remaining ??? patterns in docstrings
content = re.sub(r'"""[\?\s]+"""', '""" """', content)

# Pattern 4: Fix any remaining '""" """' to 'pass'  
content = content.replace('\n    """ """\n', '\n    pass\n')
content = content.replace('\n    """ """\r\n', '\n    pass\n')

with open(src, 'w', encoding='utf-8') as f:
    f.write(content)

import py_compile
try:
    py_compile.compile(src, doraise=True)
    print('\n✅ Syntax OK')
    sys.exit(0)
except py_compile.PyCompileError as e:
    print(f'\n❌ Error: {str(e)[:200]}')
    sys.exit(1)
