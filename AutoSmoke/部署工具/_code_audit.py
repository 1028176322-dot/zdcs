"""AutoSmoke 代码完整性审计 - 检查所有文件是否损坏"""
import os, sys, re, py_compile, io
from pathlib import Path

ROOT = Path('E:/zdcs/AutoSmoke')
REPORT = []

def log(msg, level="INFO"):
    REPORT.append((level, msg))
    icon = {"INFO": "  ", "WARN": "⚠️", "ERROR": "❌", "OK": "✅"}.get(level, "  ")
    print(f"  {icon} [{level}] {msg}")

def check_file(path):
    """检查单个文件"""
    rel = path.relative_to(ROOT)
    issues = []
    
    # 1. 检查文件是否存在
    if not path.exists():
        log(f"{rel} 文件不存在", "ERROR")
        return False
    
    # 2. 尝试编译
    try:
        py_compile.compile(str(path), doraise=True)
    except py_compile.PyCompileError as e:
        log(f"{rel} ❌ 编译失败: {str(e)[:150]}", "ERROR")
        issues.append("compile_error")
    
    # 3. 检查 UTF-8 编码
    try:
        text = path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        log(f"{rel} ❌ 不是有效的 UTF-8", "ERROR")
        return False
    
    # 4. 检查中文目录名 import 是否损坏
    for line in text.split('\n'):
        stripped = line.strip()
        if stripped.startswith('from ') and 'import ' in stripped:
            module = stripped.split(' import ')[0].replace('from ', '')
            # 检查中文目录名后是否有损坏字符
            for ch in module:
                if 0xE000 <= ord(ch) <= 0xF8FF:  # Unicode Private Use Area
                    log(f"{rel} import 路径含 PUA 字符: {stripped[:80]}", "ERROR")
                    issues.append("corrupted_import")
                    break
    
    # 5. 检查硬编码绝对路径 (盘符路径)
    if rel.suffix == '.py':
        # 检查 E: 盘硬编码
        hardcoded = re.findall(r'["\'][A-Za-z]:[\\/][^"\']*["\']', text)
        # 过滤掉合法模式（如 'C:\\Windows' 之类的系统路径, 注释中的示例等）
        hardcoded = [h for h in hardcoded if 'AutoSmoke' in h or 'k3client' in h or 's1' in h]
        for h in hardcoded:
            log(f"{rel} 含硬编码绝对路径: {h[:60]}", "WARN")
            issues.append("hardcoded_path")
    
    # 6. 检查 docstring 是否损坏
    if '"""???"""' in text or '""" ??? """' in text:
        log(f"{rel} 含损坏的文档字符串", "ERROR")
        issues.append("corrupted_docstring")
    
    # 7. 检查缺少 # -*- coding: utf-8 -*-
    if rel.suffix == '.py' and not any('coding' in line for line in text.split('\n')[:3]):
        log(f"{rel} 缺少 # -*- coding: utf-8 -*-", "WARN")
        issues.append("missing_coding")
    
    if not issues:
        log(f"{rel} ✅", "OK")
        return True
    return False


def main():
    print("=" * 60)
    print("AutoSmoke 代码完整性审计")
    print(f"根目录: {ROOT}")
    print("=" * 60)
    
    # 待检查目录
    dirs_to_check = [
        '定位', '坐标截图', '点击执行', '用例层', '元数据',
        '视觉识别', '阻塞处理', 'IDE', '部署工具', '旧脚本',
        'core_engine',
    ]
    
    checked = 0
    errors = 0
    warnings = 0
    
    for dir_name in dirs_to_check:
        dir_path = ROOT / dir_name
        if not dir_path.exists():
            log(f"目录 {dir_name}/ 不存在", "WARN")
            continue
        
        py_files = sorted(dir_path.glob('*.py'))
        if not py_files:
            log(f"{dir_name}/ 无 .py 文件", "WARN")
            continue
        
        print(f"\n📁 {dir_name}/ ({len(py_files)} 文件)")
        for f in py_files:
            checked += 1
            ok = check_file(f)
            if not ok:
                errors += 1
    
    # 也检查根目录的 .py 文件
    root_py = sorted(ROOT.glob('*.py'))
    if root_py:
        print(f"\n📁 根目录 ({len(root_py)} 文件)")
        for f in root_py:
            checked += 1
            ok = check_file(f)
            if not ok:
                errors += 1
    
    print(f"\n{'=' * 60}")
    print(f"审计完成: {checked} 个文件")
    error_count = sum(1 for l in REPORT if l[0] == "ERROR")
    warn_count = sum(1 for l in REPORT if l[0] == "WARN")
    if error_count:
        print(f"❌ {error_count} 个错误, {warn_count} 个警告")
    elif warn_count:
        print(f"⚠️  {warn_count} 个警告")
    else:
        print("✅ 全部通过")

if __name__ == '__main__':
    main()
