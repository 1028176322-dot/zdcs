"""完全重建 debug_panel.py 的 INDEX_HTML 模板"""
from pathlib import Path
import re, py_compile

src = Path('E:/zdcs/AutoSmoke/IDE/debug_panel.py')
text = src.read_text(encoding='utf-8')

# 找到 INDEX_HTML 的起止位置
start = text.find('INDEX_HTML = """')
end = text.find('"""', start + 15)  # 第一个 """ (open)
# 找到闭合的 """
close_idx = text.find('"""', end + 3)  # skip the open one
# Actually we need to find the ACTUAL closing """
# Let me search for the </html>""" pattern
close_marker = '</html>"""'
close_idx = text.find(close_marker)
if close_idx > 0:
    close_idx += len(close_marker)
else:
    # Fallback: find the """ that closes INDEX_HTML by looking after start
    search_start = start + 15
    while True:
        idx = text.find('"""', search_start)
        if idx == -1:
            break
        # Check if this looks like a closing (followed by code)
        after = text[idx+3:idx+10].strip()
        if after.startswith('\n# ') or after.startswith('\n\n@app') or after.startswith('\ndef '):
            close_idx = idx + 3
            break
        search_start = idx + 3

# 提取前后部分
before = text[:start]  # Python code before INDEX_HTML
after = text[close_idx:]  # Python code after INDEX_HTML

# ============================================================
# 重建正确的 INDEX_HTML
# ============================================================

INDEX_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>AutoSmoke 调试面板</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, 'Microsoft YaHei', sans-serif; background: #f0f2f5; color: #333; }
        .header { background: #1a1a2e; color: #eee; padding: 16px 24px; display: flex; align-items: center; gap: 16px; }
        .header h1 { font-size: 20px; }
        .header .status { font-size: 13px; padding: 4px 12px; border-radius: 12px; }
        .status-ok { background: #27ae60; }
        .status-err { background: #e74c3c; }
        .container { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; max-width: 1400px; margin: 16px auto; padding: 0 16px; }
        .card { background: #fff; border-radius: 10px; padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
        .card h2 { font-size: 15px; margin-bottom: 12px; color: #1a1a2e; border-bottom: 2px solid #eef; padding-bottom: 8px; }
        .info-grid { display: grid; grid-template-columns: auto 1fr; gap: 6px 12px; font-size: 13px; }
        .info-grid .label { color: #888; white-space: nowrap; }
        .info-grid .value { font-weight: 500; word-break: break-all; }
        .info-grid .value.ok { color: #27ae60; }
        .info-grid .value.warn { color: #e67e22; }
        .btn { display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; border: none; border-radius: 6px; cursor: pointer; font-size: 13px; transition: all .15s; }
        .btn:hover { opacity: .85; }
        .btn-primary { background: #3498db; color: #fff; }
        .btn-success { background: #27ae60; color: #fff; }
        .btn-danger { background: #e74c3c; color: #fff; }
        .btn-sm { padding: 4px 10px; font-size: 12px; }
        .btn-group { display: flex; gap: 4px; flex-wrap: wrap; margin-top: 6px; }
        .screenshot-wrap { position: relative; background: #fafafa; border-radius: 8px; overflow: hidden; min-height: 100px; }
        .screenshot-wrap img { width: 100%; height: auto; display: block; cursor: crosshair; }
        .screenshot-wrap .label { position: absolute; top: 4px; left: 4px; background: rgba(0,0,0,0.6); color: #fff; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
        .log-area { background: #1e1e1e; color: #d4d4d4; font-family: 'Consolas', monospace; font-size: 12px; padding: 8px; border-radius: 6px; height: 200px; overflow-y: auto; white-space: pre-wrap; }
        .step-input { width: 100%; padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 13px; margin-bottom: 6px; }
        .step-input:focus { outline: none; border-color: #3498db; }
        .step-list { max-height: 300px; overflow-y: auto; }
        .step-item { padding: 8px; border-left: 3px solid #ddd; margin-bottom: 4px; font-size: 13px; }
        .step-item.PASS { border-color: #27ae60; background: #f0faf4; }
        .step-item.FAIL { border-color: #e74c3c; background: #fef0ef; }
        .step-item.BLOCKED { border-color: #95a5a6; background: #f8f9fa; }
        .step-item.WARNING { border-color: #f1c40f; background: #fefcef; }
        .step-item.SKIPPED { border-color: #bdc3c7; background: #f8f9fa; color: #999; }
        .step-item .step-action { font-weight: bold; }
        .step-item .step-detail { font-size: 12px; color: #666; margin-top: 2px; }
        .tabs { display: flex; gap: 4px; margin-bottom: 8px; }
        .tab { padding: 6px 14px; border-radius: 6px 6px 0 0; cursor: pointer; font-size: 13px; background: #eee; }
        .tab.active { background: #fff; border-bottom: 2px solid #3498db; font-weight: bold; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .loading { opacity: 0.5; pointer-events: none; }
        pre { font-size: 12px; max-height: 300px; overflow: auto; }
        .full-width { grid-column: 1 / -1; }
    </style>
</head>
<body>
<div class="header">
    <h1>\U0001f527 AutoSmoke \u8c03\u8bd5\u9762\u677f</h1>
    <span class="status" id="headerStatus">\u68c0\u67e5\u4e2d...</span>
    <span style="font-size:12px;color:#999;" id="headerTime"></span>
</div>

<div class="container" id="app">
    <!-- \u5de6\u4fa7\uff1a\u5b9a\u4f4d\u4fe1\u606f -->
    <div class="card">
        <h2>\U0001f4d0 \u5b9a\u4f4d\u72b6\u6001</h2>
        <div class="info-grid" id="locInfo">
            <span class="label">GameView:</span><span class="value" id="gv">-</span>
            <span class="label">GameContent:</span><span class="value" id="gc">-</span>
            <span class="label">\u5206\u8fa8\u7387:</span><span class="value" id="res">-</span>
            <span class="label">Scale:</span><span class="value" id="scale">-</span>
            <span class="label">Scale\u5dee\u5f02:</span><span class="value" id="scaleDiff">-</span>
            <span class="label">\u5c4f\u5e55\u504f\u79fb:</span><span class="value" id="offset">-</span>
            <span class="label">Mapper:</span><span class="value" id="mapperStatus">-</span>
        </div>
        <div class="btn-group">
            <button class="btn btn-primary" onclick="refreshStatus()">\U0001f504 \u5237\u65b0\u72b6\u6001</button>
            <button class="btn btn-success" onclick="captureContent()">\U0001f4f8 \u622a\u53d6 GameContent</button>
            <button class="btn btn-danger btn-sm" onclick="testClick()">\U0001f5b1\ufe0f \u6d4b\u8bd5\u70b9\u51fb\u4e2d\u5fc3</button>
        </div>
    </div>

    <!-- \u53f3\u4fa7\uff1a\u622a\u56fe\u9884\u89c8 -->
    <div class="card">
        <h2>\U0001f5bc\ufe0f GameContent \u622a\u56fe</h2>
        <div class="screenshot-wrap">
            <img id="screenshotImg" class="screenshot" src="" alt="GameContent" style="display:none">
            <div id="noScreenshot" style="padding:40px;text-align:center;color:#999;">\u70b9\u51fb\u4e0a\u65b9\u6309\u94ae\u622a\u53d6</div>
        </div>
    </div>

    <!-- \u963b\u585e\u68c0\u6d4b -->
    <div class="card">
        <h2>\U0001f6a7 \u963b\u585e\u68c0\u6d4b</h2>
        <div class="info-grid" id="blockerInfo">
            <span class="label">\u72b6\u6001:</span><span class="value" id="blockerStatus">-</span>
            <span class="label">\u7c7b\u578b:</span><span class="value" id="blockerType">-</span>
            <span class="label">\u5173\u952e\u8bcd:</span><span class="value" id="blockerKeywords">-</span>
            <span class="label">\u5371\u9669\u7b49\u7ea7:</span><span class="value" id="blockerDanger">-</span>
        </div>
        <div class="step-list" id="blockerHistory" style="margin-top:8px;max-height:180px;overflow-y:auto;"></div>
        <div class="btn-group">
            <button class="btn btn-primary btn-sm" onclick="detectBlocker()">\U0001f50d \u68c0\u6d4b\u963b\u585e</button>
            <button class="btn btn-success btn-sm" onclick="resolveBlocker()">\U0001f6e0\ufe0f \u5904\u7406\u963b\u585e</button>
            <button class="btn btn-sm" onclick="document.getElementById('blockerHistory').innerHTML=''">\u6e05\u7a7a\u8bb0\u5f55</button>
        </div>
    </div>

    <!-- \u5143\u6570\u636e\u9762\u677f -->
    <div class="card" id="metadataCard">
        <h2>\U0001f4ca \u5143\u6570\u636e</h2>
        <div class="tabs" id="metaTabs" style="margin-bottom:8px;">
            <div class="tab active" onclick="switchMetaTab('status')">\u72b6\u6001</div>
            <div class="tab" onclick="switchMetaTab('elements')">\u5143\u7d20\u5217\u8868</div>
            <div class="tab" onclick="switchMetaTab('search')">\u641c\u7d22</div>
            <div class="tab" onclick="switchMetaTab('mapping')">\u8bed\u4e49\u6620\u5c04</div>
        </div>

        <div class="tab-content active" id="meta-status">
            <div class="info-grid">
                <span class="label">\u9875\u9762 ID:</span><span class="value" id="metaPageId">-</span>
                <span class="label">\u573a\u666f:</span><span class="value" id="metaScene">-</span>
                <span class="label">Play Mode:</span><span class="value" id="metaPlaying">-</span>
                <span class="label">UI \u5143\u7d20:</span><span class="value" id="metaTotal">-</span>
                <span class="label">\u53ef\u70b9\u51fb:</span><span class="value" id="metaClickable">-</span>
                <span class="label">\u5f39\u7a97:</span><span class="value" id="metaPopups">-</span>
            </div>
            <div style="margin-top:8px;">
                <span class="label">\u7c7b\u578b\u5206\u5e03:</span>
                <div id="metaTypeDist" style="font-size:13px;color:#666;margin-top:4px;"></div>
            </div>
            <div style="margin-top:8px;display:flex;gap:4px;">
                <span class="label" style="width:auto;">\u53ef\u6d4b\u6027\u8bc4\u5206:</span>
                <span class="value" id="accessScore">-</span>
            </div>
            <div class="btn-group" style="margin-top:8px;">
                <button class="btn btn-primary btn-sm" onclick="refreshMeta()">\U0001f504 \u5237\u65b0</button>
                <button class="btn btn-sm" onclick="runAccessibilityScan()">\U0001f50d \u53ef\u6d4b\u6027\u626b\u63cf</button>
                <button class="btn btn-sm" onclick="exportEnhancedTree()">\U0001f4e4 \u5bfc\u51fa\u589e\u5f3a\u6811</button>
            </div>
            <div class="step-list" id="accessIssues" style="margin-top:8px;max-height:200px;overflow-y:auto;font-size:12px;"></div>
        </div>

        <div class="tab-content" id="meta-elements">
            <div style="margin-bottom:8px;display:flex;gap:4px;flex-wrap:wrap;">
                <select id="metaTypeFilter" style="flex:1;padding:4px;border:1px solid #ddd;border-radius:4px;">
                    <option value="">\u6240\u6709\u7c7b\u578b</option>
                    <option value="Button">Button</option>
                    <option value="Text">Text</option>
                    <option value="Image">Image</option>
                    <option value="Panel">Panel</option>
                    <option value="Slider">Slider</option>
                    <option value="Node">Node</option>
                </select>
                <select id="metaClickFilter" style="width:100px;padding:4px;border:1px solid #ddd;border-radius:4px;">
                    <option value="">\u5168\u90e8</option>
                    <option value="true">\u53ef\u70b9\u51fb</option>
                    <option value="false">\u4e0d\u53ef\u70b9\u51fb</option>
                </select>
                <button class="btn btn-sm" onclick="loadMetaElements()">\u7b5b\u9009</button>
            </div>
            <div class="step-list" id="metaElementList" style="max-height:350px;overflow-y:auto;"></div>
        </div>

        <div class="tab-content" id="meta-search">
            <input class="step-input" id="metaSearchInput" placeholder="\u641c\u7d22 testId / name / path / text"
                   onkeydown="if(event.key==='Enter') metaSearch()">
            <button class="btn btn-primary btn-sm" onclick="metaSearch()">\U0001f50d \u641c\u7d22</button>
            <div class="step-list" id="metaSearchResults" style="max-height:350px;overflow-y:auto;margin-top:8px;"></div>
        </div>

        <div class="tab-content" id="meta-mapping">
            <div class="tabs" id="mapTabs" style="margin-bottom:6px;">
                <div class="tab active" onclick="switchMapTab('annotate')">\u6807\u6ce8\u5143\u7d20</div>
                <div class="tab" onclick="switchMapTab('list')">\u5df2\u6620\u5c04</div>
                <div class="tab" onclick="switchMapTab('reverse')">\u622a\u56fe\u53cd\u67e5</div>
            </div>

            <div class="tab-content active" id="map-annotate">
                <select id="mapElementSelect" style="width:100%;padding:6px;border:1px solid #ddd;border-radius:4px;margin-bottom:6px;font-size:13px;">
                    <option value="">\u2190 \u5148\u52a0\u8f7d\u5143\u7d20\u5217\u8868</option>
                </select>
                <button class="btn btn-sm" onclick="loadMapElements()" style="margin-bottom:6px;">\U0001f504 \u52a0\u8f7d\u5143\u7d20</button>
                <div id="mapForm" style="font-size:13px;">
                    <input class="step-input" id="mapDisplayName" placeholder="\u663e\u793a\u540d\u79f0 (\u5982: \u4f7f\u7528\u6309\u94ae)" style="margin-bottom:4px;">
                    <input class="step-input" id="mapTestId" placeholder="testId (\u5982: bag.button.use)" style="margin-bottom:4px;">
                    <select id="mapRole" style="width:100%;padding:5px;border:1px solid #ddd;border-radius:4px;margin-bottom:4px;">
                        <option value="">\u9009\u62e9\u89d2\u8272...</option>
                        <option value="action">action - \u64cd\u4f5c\u6309\u94ae</option>
                        <option value="navigation">navigation - \u5bfc\u822a</option>
                        <option value="input">input - \u8f93\u5165</option>
                        <option value="display">display - \u5c55\u793a</option>
                        <option value="container">container - \u5bb9\u5668</option>
                    </select>
                    <input class="step-input" id="mapPageId" placeholder="pageId (\u5982: bag_page)" style="margin-bottom:4px;">
                    <textarea id="mapMeaning" rows="2" style="width:100%;padding:6px;border:1px solid #ddd;border-radius:4px;margin-bottom:4px;font-family:inherit;font-size:13px;" placeholder="\u8bed\u4e49\u8bf4\u660e (\u5982: \u4f7f\u7528\u9009\u4e2d\u7684\u9053\u5177)"></textarea>
                    <div class="btn-group">
                        <button class="btn btn-primary btn-sm" onclick="saveMapping()">\U0001f4be \u4fdd\u5b58\u6807\u6ce8</button>
                        <button class="btn btn-sm" onclick="clearMapForm()">\u6e05\u7a7a</button>
                        <button class="btn btn-sm" id="mapDeleteBtn" onclick="deleteMapping()" style="display:none;color:#f44336;">\U0001f5d1\ufe0f \u5220\u9664</button>
                    </div>
                    <div id="mapSaveResult" style="font-size:12px;margin-top:4px;"></div>
                </div>
            </div>

            <div class="tab-content" id="map-list">
                <div class="step-list" id="mapList" style="max-height:350px;overflow-y:auto;"></div>
                <button class="btn btn-sm" onclick="loadMapList()" style="margin-top:6px;">\U0001f504 \u5237\u65b0\u5217\u8868</button>
            </div>

            <div class="tab-content" id="map-reverse">
                <p style="font-size:13px;color:#666;margin-bottom:6px;">\u70b9\u51fb\u622a\u56fe\u4f4d\u7f6e\u53cd\u67e5\u547d\u4e2d\u8282\u70b9</p>
                <div id="mapScreenshot" style="background:#f0f0f0;border-radius:6px;padding:20px;text-align:center;margin-bottom:6px;cursor:crosshair;">
                    <span style="color:#999;">\U0001f4f8 \u5148\u622a\u53d6 GameContent</span>
                </div>
                <div class="step-list" id="mapReverseResults" style="max-height:200px;overflow-y:auto;"></div>
            </div>
        </div>
    </div>

    <!-- \u811a\u672c\u90e8\u7f72 -->
    <div class="card">
        <h2>\U0001f4e6 \u811a\u672c\u90e8\u7f72</h2>
        <div class="info-grid" id="deployInfo">
            <span class="label">\u9879\u76ee\u8def\u5f84:</span><span class="value" id="deployPath">-</span>
            <span class="label">\u72b6\u6001:</span><span class="value" id="deployStatus">\u68c0\u67e5\u4e2d...</span>
        </div>
        <div class="step-list" id="deployScripts" style="margin-top:8px;max-height:120px;overflow-y:auto;"></div>
        <div class="btn-group">
            <button class="btn btn-primary btn-sm" onclick="checkDeploy()">\U0001f50d \u68c0\u67e5\u72b6\u6001</button>
            <button class="btn btn-success btn-sm" onclick="deployScripts()">\U0001f4e6 \u90e8\u7f72\u5168\u90e8</button>
        </div>
    </div>

    <!-- \u4e0b\u65b9\u5168\u5bbd\uff1a\u6b65\u9aa4\u6267\u884c -->
    <div class="card full-width">
        <h2>\U0001f4cb \u6b65\u9aa4\u6267\u884c</h2>
        <div class="tabs" id="stepTabs">
            <div class="tab active" onclick="switchTab('manual')">\u624b\u52a8\u8f93\u5165</div>
            <div class="tab" onclick="switchTab('preset')">\u9884\u8bbe\u7528\u4f8b</div>
            <div class="tab" onclick="switchTab('log')">\u6267\u884c\u65e5\u5fd7</div>
        </div>

        <div class="tab-content active" id="tab-manual">
            <input class="step-input" id="stepInput" placeholder="\u8f93\u5165\u6b65\u9aa4\uff0c\u5982: \u70b9\u51fb normalized(0.5,0.95)" 
                   onkeydown="if(event.key==='Enter') executeSteps()">
            <div>
                <button class="btn btn-primary btn-sm" onclick="executeSteps()">\u25b6 \u6267\u884c</button>
                <button class="btn btn-sm" onclick="document.getElementById('stepInput').value='\u7b49\u5f85 2 \u79d2'">\u7b49\u5f85</button>
                <button class="btn btn-sm" onclick="document.getElementById('stepInput').value='\u622a\u56fe'">\u622a\u56fe</button>
                <button class="btn btn-sm" onclick="document.getElementById('stepInput').value='\u70b9\u51fb normalized(0.5,0.5)'">\u70b9\u4e2d\u5fc3</button>
            </div>
            <div class="step-list" id="stepResults"></div>
        </div>

        <div class="tab-content" id="tab-preset">
            <select id="presetSelect" style="width:100%;padding:8px;margin-bottom:8px;border:1px solid #ddd;border-radius:6px;">
                <option value="click_center">\u70b9\u51fb\u753b\u9762\u4e2d\u5fc3 + \u7b49\u5f85 + \u622a\u56fe</option>
                <option value="click_bottom">\u70b9\u51fb\u5e95\u90e8\u5f52\u4e00\u5316(0.5,0.95) + \u622a\u56fe</option>
                <option value="assert_test">\u65ad\u8a00\u5b58\u5728\u4e2d\u5fc3 + \u65ad\u8a00\u4e0d\u5b58\u5728\u65e0\u6548</option>
            </select>
            <button class="btn btn-primary btn-sm" onclick="runPreset()">\u25b6 \u6267\u884c\u9884\u8bbe</button>
            <div class="step-list" id="presetResults"></div>
        </div>

        <div class="tab-content" id="tab-log">
            <div class="log-area" id="logArea">\u7b49\u5f85\u6267\u884c...</div>
            <button class="btn btn-sm" onclick="document.getElementById('logArea').textContent=''" style="margin-top:4px;">\u6e05\u7a7a\u65e5\u5fd7</button>
        </div>
    </div>
</div>
"""

# 重新组装文件
result = before + 'INDEX_HTML = """' + INDEX_HTML + '"""' + after

src.write_text(result, encoding='utf-8')

# 验证编译
try:
    py_compile.compile(str(src), doraise=True)
    print('✅ Syntax OK')
    print(f'File size: {len(result)} bytes')
except py_compile.PyCompileError as e:
    print(f'❌ Error: {str(e)[:200]}')
