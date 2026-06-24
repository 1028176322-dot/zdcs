"""Fix mojibake in debug_panel.py - hardcoded replacement map"""
import sys, py_compile

src = 'E:/zdcs/AutoSmoke/IDE/debug_panel.py'

with open(src, 'r', encoding='utf-8') as f:
    content = f.read()

# Hardcoded mapping of corrupted sequences → correct Chinese
fixes = [
    ('鍧愭爣鎴浘', '坐标截图'),
    ('鐢ㄤ緥灞', '用例层'),
    ('鐐瑰嚮鎵ц', '点击执行'),
    ('鍏冩暟鎹', '元数据'),
    ('闃诲澶勭悊', '阻塞处理'),
    ('琛岃', '视觉'),
    ('閮ㄧ讲宸ュ叿', '部署工具'),
    ('綰垮浘', '截图'),
    ('鐐瑰嚮', '点击'),
    ('澶勭悊', '处理'),
]

found = 0
for corrupted, correct in fixes:
    if corrupted in content:
        count = content.count(corrupted)
        content = content.replace(corrupted, correct)
        found += count
        print(f'  {corrupted} → {correct} ({count} occurrences)')

if found == 0:
    print('No corrupted patterns found - file may already be fixed or differently corrupted')
    # Try to identify any file with non-printable/non-ASCII issue
    for i, line in enumerate(content.split('\n')):
        for ch in line:
            if 0xE000 <= ord(ch) <= 0xF8FF:  # Private Use Area
                print(f'  Private Use Area char U+{ord(ch):04X} at line {i+1}')
                break

with open(src, 'w', encoding='utf-8') as f:
    f.write(content)

try:
    py_compile.compile(src, doraise=True)
    print(f'\n✅ Syntax OK (fixed {found} occurrences)')
    sys.exit(0)
except py_compile.PyCompileError as e:
    print(f'\n❌ Still has error: {str(e)[:200]}')
    sys.exit(1)
