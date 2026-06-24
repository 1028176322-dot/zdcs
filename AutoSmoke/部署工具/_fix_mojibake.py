"""Fix corrupted Chinese chars in debug_panel.py after _fix_all_paths damage"""
import sys

src = 'E:/zdcs/AutoSmoke/IDE/debug_panel.py'

with open(src, 'r', encoding='utf-8') as f:
    content = f.read()

# The corruption happened because Chinese characters were read as Latin-1
# and written as UTF-8, creating mojibake. We need to reverse this.

# First, try to reverse the double-encoding
# The original text was UTF-8 bytes interpreted as Latin-1,
# then those Latin-1 chars were written as UTF-8
# So: UTF-8 -> Latin-1 decode -> UTF-8 decode should restore it

try:
    # Step 1: Encode the corrupted text as Latin-1 (get original bytes)
    intermediate = content.encode('latin-1')
    # Step 2: Decode those bytes as UTF-8 (get original text)
    restored = intermediate.decode('utf-8')
    
    with open(src, 'w', encoding='utf-8') as f:
        f.write(restored)
    
    import py_compile
    try:
        py_compile.compile(src, doraise=True)
        print('RESTORED - Syntax OK')
        sys.exit(0)
    except py_compile.PyCompileError as e:
        print(f'Still has error after restoration: {str(e)[:200]}')
        sys.exit(1)
        
except UnicodeEncodeError as e:
    print(f'Cannot encode as latin-1: {e}')
    sys.exit(1)
