#!/usr/bin/env python3
"""Add directory listing API + improve folder import flow"""
from pathlib import Path
FP = Path(__file__).resolve().with_name("debug_panel.py")
content = FP.read_text(encoding="utf-8")

# Add /api/mapping/list_dir before the import API
old_marker = "def api_mapping_import():"
new_api = '''@app.route("/api/mapping/list_dir", methods=["POST"])
def api_mapping_list_dir():
    """列出指定目录中的可用数据文件"""
    try:
        data = request.get_json() or {}
        src_dir = data.get("dir", "")
        if not src_dir:
            src_dir = os.path.join(_CONF_DIR, "元数据")
            if not os.path.exists(src_dir):
                src_dir = os.path.join(os.environ.get("USERPROFILE", "."), ".autosmoke", "metadata")
        if not os.path.exists(src_dir):
            return jsonify({"exists": False, "error": f"\u76ee\u5f55\u4e0d\u5b58\u5728: {src_dir}"})
        files = []
        for f in os.listdir(src_dir):
            fpath = os.path.join(src_dir, f)
            if f.endswith(".json") and os.path.isfile(fpath):
                fsize = os.path.getsize(fpath)
                files.append({"name": f, "size": fsize, "sizeKB": round(fsize / 1024, 1)})
        priority_order = ["enhanced_ui_tree.json", "current_ui_tree.json", "project_ui_inventory.json", "current_ui.json"]
        files.sort(key=lambda x: priority_order.index(x["name"]) if x["name"] in priority_order else 99)
        return jsonify({"exists": True, "dir": src_dir, "files": files})
    except Exception as e:
        return jsonify({"error": str(e)})

def api_mapping_import():'''

assert old_marker in content, "Marker not found"
content = content.replace(old_marker, new_api)
print("list_dir API added")

# Update frontend: replace the import section with folder browser
old_import = '''<div class="sec">
  <div class="sh">\u6570\u636e\u5bfc\u5165 <span style="font-weight:400;font-size:10px;color:#888;">\u5143\u6570\u636e\u2192\u8349\u7a3f\u2192\u5ba1\u6838</span></div>
  <div style="display:flex;gap:3px;">
    <input id="importDir" class="inp" placeholder="AutoSmoke/\u5143\u6570\u636e" style="flex:1;font-size:10px;">
    <button class="btn btn-s btn-sm" onclick="doImport()">\u5bfc\u5165\u5e76\u751f\u6210\u8349\u7a3f</button>
  </div>
  <div id="importSummary" style="font-size:10px;color:#666;margin-top:3px;"></div>
</div>'''

new_import = '''<div class="sec">
  <div class="sh">\u6570\u636e\u5bfc\u5165 <span style="font-weight:400;font-size:10px;color:#888;">\u6587\u4ef6\u5939\u2192\u8349\u7a3f\u2192\u5ba1\u6838</span></div>
  <div style="display:flex;gap:3px;">
    <input id="importDir" class="inp" placeholder="AutoSmoke/\u5143\u6570\u636e" style="flex:1;font-size:10px;">
    <button class="btn btn-sm" onclick="scanDir()">\u6d4f\u89c8</button>
    <button class="btn btn-s btn-sm" onclick="doImport()">\u5bfc\u5165\u5e76\u751f\u6210\u8349\u7a3f</button>
  </div>
  <div id="dirContent" style="font-size:10px;color:#666;margin-top:2px;max-height:60px;overflow:auto;"></div>
  <div id="importSummary" style="font-size:10px;color:#666;margin-top:2px;"></div>
</div>'''

assert old_import in content, "Import section not found"
content = content.replace(old_import, new_import)
print("Import section updated with folder browser")

# Add scanDir JS function
old_doImport = "function doImport(){"
new_doImport = '''function scanDir(){
  var dir=document.getElementById('importDir').value;
  if(!dir){ml('\u8bf7\u8f93\u5165\u76ee\u5f55','w');return;}
  fetch('/api/mapping/list_dir',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({dir:dir})}).then(function(r){return r.json()}).then(function(d){
    var el=document.getElementById('dirContent');
    if(!d.exists){el.innerHTML='<span style="color:red;">'+d.error+'</span>';return;}
    var h='<span style="color:#4CAF50;">\u2714 \u53d1\u73b0 '+d.files.length+'\u4e2a\u6587\u4ef6:</span> ';
    d.files.forEach(function(f){h+=f.name+' ('+f.sizeKB+'KB) ';});
    el.innerHTML=h;ml('\u626b\u63cf\u5b8c\u6210: '+d.files.length+'\u4e2a\u6587\u4ef6');
  }).catch(function(e){ml('\u626b\u63cf\u5931\u8d25','e');});
}
function doImport(){'''

assert old_doImport in content, "doImport not found"
content = content.replace(old_doImport, new_doImport)
print("scanDir function added")

FP.write_text(content, encoding="utf-8")

import py_compile
py_compile.compile(str(FP), doraise=True)
print("Compile OK!")
