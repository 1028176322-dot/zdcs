"""Fix debug_panel.py - comprehensive recovery of corrupted Chinese chars"""
import re, sys

src = 'E:/zdcs/AutoSmoke/IDE/debug_panel.py'

with open(src, 'r', encoding='utf-8') as f:
    content = f.read()

# The fix script corrupted Chinese characters. Let's fix all known patterns.
# Known correct Chinese directory names:
correct_names = {
    '坐标截图', '点击执行', '用例层', '元数据', 
    '阻塞处理', '视觉识别', '部署工具', 'IDE', '定位'
}

# Known correct Chinese package import patterns
# These appear in the file as: from <corrupted>.module import Xxx
# We need to fix: 鍧愭爣鎴浘 -> 坐标截图, etc.

# Build a comprehensive mapping of corrupted->correct
# The corruption happened when Chinese chars were written through ASCII-only str operations
# This typically results in '?' replacement
import_fixes = {}

# Read all lines and find corrupted imports
lines = content.split('\n')
for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped.startswith('from ') and 'import ' in stripped:
        # Extract the module path
        parts = stripped.split(' import ')
        if len(parts) >= 1:
            module_part = parts[0].replace('from ', '').strip()
            # Check if module_part has any non-ASCII chars that look corrupted
            for ch in module_part:
                if ord(ch) > 127 and ch not in '坐标截图点击执行用例层元数据阻塞处理视觉识别部署工具定位':
                    # This is a corrupted character
                    print(f'Corrupted import at line {i+1}: {stripped[:80]}')
                    break

# Since the corruption is pervasive, let's try a bulk fix approach
# The corrupted chars are specific mojibake. Let's build a mapping by scanning the file.

# First, let me try to identify the specific corrupted byte sequences
# Common mojibake for these Chinese chars:

mojibake_map = {
    # '坐标截图'
    '\u951d\u60a3': '坐标',  # partial
    '\u951d\u60a3\u620a\u6d9d': '坐标截图',
    # Detect patterns programmatically
}

# Actually let me try the smart approach - re-read the file as Latin-1
# and then try to decode the non-ASCII parts
fixed_count = 0
result_lines = []

for i, line in enumerate(lines):
    original_line = line
    # Try to fix corrupted characters by reverse-engineering
    # For each line with Chinese mojibake, try to decode it properly
    try:
        # Try to re-encode as latin-1 and decode as utf-8
        line_bytes = line.encode('latin-1', errors='replace')
        decoded = line_bytes.decode('utf-8', errors='replace')
        # Check if we got real Chinese characters back
        if any(ord(c) > 0x4E00 and ord(c) < 0x9FFF for c in decoded):
            if decoded != line:
                # Verify this looks like valid code
                if decoded.count('"') % 2 == 0 or '"""' in decoded:
                    result_lines.append(decoded)
                    if decoded != line:
                        fixed_count += 1
                    continue
    except:
        pass
    result_lines.append(line)

content = '\n'.join(result_lines)

if fixed_count > 0:
    print(f'Fixed {fixed_count} lines via latin-1 re-encoding')

with open(src, 'w', encoding='utf-8') as f:
    f.write(content)

import py_compile
try:
    py_compile.compile(src, doraise=True)
    print('✅ Syntax OK')
    sys.exit(0)
except py_compile.PyCompileError as e:
    print(f'❌ Still has error: {str(e)[:300]}')
    sys.exit(1)
