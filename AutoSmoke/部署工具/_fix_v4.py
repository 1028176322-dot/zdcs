"""Fix docstrings and remaining syntax issues in debug_panel.py"""
import sys, py_compile, re

src = 'E:/zdcs/AutoSmoke/IDE/debug_panel.py'

with open(src, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Replace """"""" (7 quotes) with proper empty docstring """ """
content = content.replace('"""""""', '""" """')

# Fix 2: Find any other odd quote patterns
# Search for patterns like """" (4 quotes) that break parsing
# These happen when close is missing - replace with """ 
content = content.replace('""""', '"""')

# Fix 3: Check for unterminated docstrings by counting pairs
# First, let's check if we have an even number of """
triple_count = content.count('"""')
print(f'Total triple quotes: {triple_count} (should be even)')

# Verify
try:
    py_compile.compile(src, doraise=True)
    print('✅ Syntax OK')
    sys.exit(0)
except py_compile.PyCompileError as e:
    print(f'❌ Error: {str(e)[:300]}')

# If still broken, let's try to find the problematic line
lines = content.split('\n')
problematic = []
for i, line in enumerate(lines):
    # Find lines with odd number of quotes
    quote_count = line.count('"')
    if quote_count > 0 and quote_count % 2 != 0:
        problematic.append((i+1, line.strip()[:80]))

if problematic:
    print(f'\nLines with odd number of quotes ({len(problematic)}):')
    for ln, text in problematic[:10]:
        print(f'  L{ln}: {text}')

with open(src, 'w', encoding='utf-8') as f:
    f.write(content)
