#!/usr/bin/env python3
"""Step 2: Update frontend HTML/JS"""
from pathlib import Path
FP = Path(__file__).resolve().with_name("debug_panel.py")
BKP = FP.with_name("debug_panel.py.bak.20260616_step1")
# Backup current state (which has new APIs)
if not BKP.exists():
    BKP.write_text(FP.read_text(encoding="utf-8"), encoding="utf-8")

content = FP.read_text(encoding="utf-8")

# First save - ensure backend APIs are preserved
success = True

# ===== Fix 1: Change "用例导入" section to "数据导入" =====
# Search in the HTML
old_node = 'class="sh">\u7528\u4f8b\u5bfc\u5165'
new_node = 'class="sh">\u6570\u636e\u5bfc\u5165'
if old_node in content:
    content = content.replace(old_node, new_node)
    print("Fix 1: Title updated")
else:
    print("Fix 1: Title pattern not found, maybe already updated")

# ===== Fix 2: Replace the import section with simplified version =====
old_import = '''    <div style="display:flex;gap:3px;">
    <input id="caseFile" class="inp" placeholder="\u9009\u62e9\u7528\u4f8b\u6a21\u677f.xlsx" style="flex:1;font-size:10px;">
    <button class="btn btn-sm" onclick="impCase()">\u5bfc\u5165</button>
  </div>
  <div class="flex">
    <button class="btn btn-sm" onclick="loadCases()">\u89e3\u6790</button>
    <button class="btn btn-sm" onclick="vldCase()">\u6821\u9a8c</button>
  </div>
  <div class="sl-list" id="casePreview" style="max-height:80px;font-size:10px;">\u5bfc\u5165\u540e\u663e\u793a\u7528\u4f8b\u9884\u89c8</div>'''

new_import = '''    <div style="display:flex;gap:3px;">
    <input id="importDir" class="inp" placeholder="AutoSmoke/\u5143\u6570\u636e" style="flex:1;font-size:10px;">
    <button class="btn btn-sm" onclick="doImport()">\u626b\u63cf\u5e76\u5bfc\u5165</button>
  </div>
  <div class="flex">
    <button class="btn btn-s btn-sm" onclick="doImport()">\u5bfc\u5165\u751f\u6210\u8349\u7a3f</button>
    <button class="btn btn-sm" onclick="showAdvancedImport()">\u9ad8\u7ea7\u5bfc\u5165</button>
  </div>
  <div id="importSummary" style="font-size:10px;color:#666;margin-top:3px;"></div>'''

if old_import in content:
    content = content.replace(old_import, new_import)
    print("Fix 2: Import section simplified")
else:
    print("Fix 2: Import pattern not found")

# ===== Fix 3: Add import JS functions before envInit =====
old_env = '// ===== \u73af\u5883\u521d\u59cb\u5316 =====\nfunction envInit'
new_js = '''// ===== \u6570\u636e\u5bfc\u5165 =====
function doImport(){
  var dir=document.getElementById('importDir').value;
  if(!dir){ml('\u8bf7\u8f93\u5165\u76ee\u5f55','w');return;}
  ml('\u5bfc\u5165: '+dir);
  fetch('/api/mapping/import',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sourceDir:dir})}).then(function(r){return r.json()}).then(function(d){
    if(d.success){
      var s=d.summary||{};var el=document.getElementById('importSummary');
      var h='\u6570\u636e\u6e90: '+s.dataSource+' | \u8282\u70b9: '+s.totalNodes+' | \u53ef\u70b9\u51fb: '+s.totalClickable+' | \u8349\u7a3f: '+s.totalDrafts+' | \u5f85\u5ba1: '+s.pending;
      el.innerHTML='<span style="color:#4CAF50;">\u2714 \u5bfc\u5165\u6210\u529f: </span>'+h;
      ml('\u5bfc\u5165\u5b8c\u6210: '+s.totalDrafts+'\u8349\u7a3f');
      ldDrafts();
    }else{
      document.getElementById('importSummary').innerHTML='<span style="color:red;">\u2716 '+d.error+'</span>';
    }
  }).catch(function(e){ml('\u5bfc\u5165\u5931\u8d25','e');});
}
function showAdvancedImport(){ml('\u9ad8\u7ea7\u5bfc\u5165 (\u5f85\u5b9e\u73b0)');}

// ===== \u73af\u5883\u521d\u59cb\u5316 =====\nfunction envInit'''
assert old_env in content, "Fix 3: envInit not found"
content = content.replace(old_env, new_js)
print("Fix 3: Import JS added")

# ===== Fix 4: Add structure_confirm to review buttons =====
old_btns = '<button class="btn btn-sm" style="background:#4CAF50;color:#fff;" onclick="cfD()">\u786e\u8ba4</button><button class="btn btn-sm" style="background:#2196F3;color:#fff;" onclick="svD()">\u4fdd\u5b58</button><button class="btn btn-sm" style="background:#f44336;color:#fff;" onclick="rjD()">\u62d2\u7edd</button><button class="btn btn-sm" style="background:#9E9E9E;color:#fff;" onclick="igD()">\u5ffd\u7565</button>'
new_btns = '<button class="btn btn-sm" style="background:#8BC34A;color:#fff;" onclick="scD()">\u7ed3\u6784</button><button class="btn btn-sm" style="background:#2196F3;color:#fff;" onclick="svD()">\u4fdd\u5b58</button><button class="btn btn-sm" style="background:#4CAF50;color:#fff;" onclick="cfD()">\u786e\u8ba4</button><button class="btn btn-sm" style="background:#f44336;color:#fff;" onclick="rjD()">\u62d2\u7edd</button><button class="btn btn-sm" style="background:#9E9E9E;color:#fff;" onclick="igD()">\u5ffd\u7565</button>'

if old_btns in content:
    content = content.replace(old_btns, new_btns)
    print("Fix 4: Review buttons updated")
else:
    print("Fix 4: Button pattern not found")

# ===== Fix 5: Add scD JS function =====
old_svD = 'function svD(){var d={};'
new_svD = 'function scD(){fetch(\'/api/mapping/drafts/\'+encodeURIComponent(rp)+\'/structure_confirm\',{method:\'POST\'}).then(function(r){return r.json()}).then(function(d){document.getElementById(\'rr\').innerHTML=d.success?\'\u7ed3\u6784\u786e\u8ba4\':\'\u5931\u8d25\';if(d.success)ldDrafts();});}\nfunction svD(){var d={};'

if old_svD in content:
    content = content.replace(old_svD, new_svD)
    print("Fix 5: scD function added")
else:
    print("Fix 5: svD not found")

# ===== Fix 6: Add quick filters above search bar =====
old_search = '<input id="rkw" class="inp" placeholder="\u641c\u7d22..." style="flex:1;font-size:10px;">'
new_search = '<input id="rkw" class="inp" placeholder="\u641c\u7d22..." style="flex:1;font-size:10px;">\n          <span class="bdg" style="background:#8BC34A;cursor:pointer;" onclick="quickFilter(\'high\')">\u9ad8\u4fe1\u5ea6</span>\n          <span class="bdg" style="background:#FF9800;cursor:pointer;" onclick="quickFilter(\'nodesc\')">\u7f3a\u63cf\u8ff0</span>\n          <span class="bdg" style="background:#f44336;cursor:pointer;" onclick="quickFilter(\'noclick\')">\u7f3a\u70b9\u51fb</span>'

if old_search in content:
    content = content.replace(old_search, new_search)
    print("Fix 6: Quick filters added")
else:
    print("Fix 6: Search pattern not found")

# ===== Fix 7: Add quickFilter JS function =====
old_ldDrafts = 'function ldDrafts(){var kw=document.getElementById(\'rkw\').value;var stt=document.getElementById(\'rst\').value;var url=\'/api/mapping/drafts?keyword=\'+encodeURIComponent(kw);if(stt)url+=\'&status=\'+encodeURIComponent(stt);fetch(url).then(function(r){return r.json()}).then(function(d){var list=document.getElementById(\'rdl\');'
assert old_ldDrafts in content, "Fix 7: ldDrafts not found"
new_ldDrafts = 'var _allDrafts=[];\nfunction ldDrafts(){var kw=document.getElementById(\'rkw\').value;var stt=document.getElementById(\'rst\').value;var url=\'/api/mapping/drafts?keyword=\'+encodeURIComponent(kw);if(stt)url+=\'&status=\'+encodeURIComponent(stt);fetch(url).then(function(r){return r.json()}).then(function(d){_allDrafts=d.drafts||[];var list=document.getElementById(\'rdl\');'
content = content.replace(old_ldDrafts, new_ldDrafts)
print("Fix 7: ldDrafts updated with cache")

# ===== Fix 8: Add renderDrafts and quickFilter =====
old_render_stop = 'function ml(m,l){'
new_render = '''function renderDrafts(items){
  var list=document.getElementById('rdl');
  if(!items||items.length===0){list.innerHTML='<div style="padding:10px;text-align:center;color:#ccc;">\u65e0\u8349\u7a3f</div>';return;}
  var h='<table class="st"><tr style="background:#f5f5f5;"><td>\u72b6\u6001</td><td>\u540d\u79f0</td><td>\u4fe1\u5ea6</td></tr>';
  items.forEach(function(it){
    var sm={'auto_draft':'\u5f85\u5ba1','structure_confirmed':'\u7ed3\u6784','manual_confirmed':'\u786e\u8ba4','rejected':'\u62d2\u7edd','ignored':'\u5ffd\u7565'};
    var c=it.source==='manual_confirmed'?'bg-g':it.source==='rejected'?'bg-r':it.source==='structure_confirmed'?'" style="background:#8BC34A;color:#fff;"':it.source==='visual_confirmed'?'" style="background:#03A9F4;color:#fff;"':it.source==='click_confirmed'?'" style="background:#673AB7;color:#fff;"':'bg-y"';
    var cls=c.startsWith('"')?c:'"'+c.slice(0,-1)+'"';
    h+='<tr onclick="shDraft(\\''+(it.path||'').replace(/'/g,'')+'\\')" style="cursor:pointer;">';
    h+='<td><span class="bdg" style="background'+(c.startsWith('"')?c.split('"')[1]:'')+';color:#fff;padding:1px 5px;border-radius:3px;font-size:9px;">'+(sm[it.source]||it.source||'')+'</span></td>';
    h+='<td>'+(it.displayName||it.name||'?')+'</td><td>'+(it.confidence||0)+'</td></tr>';
  });h+='</table>';list.innerHTML=h;
  document.getElementById('rStats').textContent=items.length+'\u6761';
}
function quickFilter(t){
  if(!_allDrafts||_allDrafts.length===0){ldDrafts();return;}
  var items=[];
  if(t==='high'){items=_allDrafts.filter(function(it){return it.confidence>=85;});}
  else if(t==='nodesc'){items=_allDrafts.filter(function(it){return !it.chineseDescription;});}
  else if(t==='noclick'){items=_allDrafts.filter(function(it){return it.clickable&&!it.clickTargetNode;});}
  renderDrafts(items);
}
function ml(m,l){'''
if old_render_stop in content:
    content = content.replace(old_render_stop, new_render)
    print("Fix 8: renderDrafts and quickFilter added")
else:
    print("Fix 8: ml not found")

# Save
FP.write_text(content, encoding="utf-8")

# Verify
import py_compile
py_compile.compile(str(FP), doraise=True)
print("Compile OK! All changes saved")
