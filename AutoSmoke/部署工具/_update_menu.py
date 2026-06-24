# -*- coding: utf-8 -*-
"""
批量更新 AutoSmoke Unity 菜单为中文 1 级页签分类
"""
from pathlib import Path

TOOLS = Path("E:/zdcs/AutoSmoke/tools")

# 替换映射: 旧 MenuItem 路径 → 新 MenuItem 路径
REPLACEMENTS = {
    # ── GameViewLocator.cs ──
    'MenuItem("AutoSmoke/Locate Game View")':
        'MenuItem("AutoSmoke/定位/定位 Game 视图 _&L")',

    # ── AutoSmokeGameViewBridge.cs ──
    'MenuItem("AutoSmoke/Export GameView State _#E")':
        'MenuItem("AutoSmoke/直连定位/导出状态 _#&E")',
    'MenuItem("AutoSmoke/Start GameView Bridge _#B")':
        'MenuItem("AutoSmoke/直连定位/启动 Bridge _#&B")',
    'MenuItem("AutoSmoke/Stop GameView Bridge")':
        'MenuItem("AutoSmoke/直连定位/停止 Bridge")',
    'MenuItem("AutoSmoke/Open State File")':
        'MenuItem("AutoSmoke/直连定位/打开状态文件")',

    # ── AutoSmokeMetadataExporter.cs ──
    'MenuItem("AutoSmoke/Export Metadata", false, 110)':
        'MenuItem("AutoSmoke/元数据/导出元数据", false, 110)',
    'MenuItem("AutoSmoke/Export Metadata (Verbose)", false, 111)':
        'MenuItem("AutoSmoke/元数据/导出元数据(详细)", false, 111)',
    'MenuItem("AutoSmoke/Metadata - Open Output Folder", false, 210)':
        'MenuItem("AutoSmoke/元数据/打开输出目录", false, 210)',
    'MenuItem("AutoSmoke/Metadata - Force Export Now", false, 211)':
        'MenuItem("AutoSmoke/元数据/强制立即导出", false, 211)',
}

for cs_file in sorted(TOOLS.glob("*.cs")):
    text = cs_file.read_text(encoding="utf-8")
    original = text
    for old, new in REPLACEMENTS.items():
        text = text.replace(old, new)
    if text != original:
        cs_file.write_text(text, encoding="utf-8")
        print(f"✅ {cs_file.name} 已更新")
