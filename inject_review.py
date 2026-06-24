#!/usr/bin/env python3
"""Inject review panel JS into debug_panel.py"""
with open('E:/zdcs/AutoSmoke/IDE/debug_panel.py', 'r', encoding='utf-8') as f:
    content = f.read()

marker = '// ===== \u963b\u585e\u68c0\u6d4b\u4e0e\u5904\u7406 ====='
pos = content.find(marker)
if pos < 0:
    pos = content.find('function captureContent')

review_js = '''
// ===== \u5ba1\u6838\u9762\u677f JS =====
var _reviewSelectedPath = '';

function switchMapTab(name){
  ['annotate','list','reverse','review'].forEach(function(t){
    var el = document.getElementById('map-'+t);
    if(el) el.style.display = t === name ? 'block' : 'none';
  });
  if(name === 'review') loadReviewDrafts();
}

function loadReviewDrafts(){
  var kw = document.getElementById('reviewKeyword').value;
  var st = document.getElementById('reviewStatusFilter').value;
  var url = '/api/mapping/drafts?keyword='+encodeURIComponent(kw);
  if(st) url += '&status='+encodeURIComponent(st);
  fetch(url).then(r=>r.json()).then(function(d){
    var list = document.getElementById('reviewDraftList');
    var stats = document.getElementById('reviewStats');
    var items = d.drafts || [];
    stats.textContent = '\u5171 '+items.length+' \u6761\u8349\u7a3f';
    if(items.length === 0){
      list.innerHTML = '<div style="padding:20px;text-align:center;color:#ccc;">\u65e0\u8349\u7a3f</div>';
      return;
    }
    var html = '<table style="width:100%;border-collapse:collapse;font-size:11px;">';
    html += '<tr style="background:#f5f5f5;"><td>\u72b6\u6001</td><td>\u540d\u79f0</td><td>\u9875\u9762</td><td>\u7c7b\u578b</td><td>\u4fe1\u5ea6</td></tr>';
    items.forEach(function(item){
      var st = item.source || 'pending';
      var sm = {'auto_draft':'\u5f85\u5ba1\u6838','manual_confirmed':'\u5df2\u786e\u8ba4','modified':'\u5df2\u4fee\u6539','rejected':'\u5df2\u62d2\u7edd','ignored':'\u5df2\u5ffd\u7565'};
      var sc = st === 'manual_confirmed' ? '#4CAF50' : st === 'rejected' ? '#f44336' : '#FF9800';
      var pth = (item.path || '').replace(/'/g,"\\\\'");
      html += '<tr onclick="showReviewDetail(\\''+pth+'\\')" style="cursor:pointer;border-bottom:1px solid #eee;">';
      html += '<td><span style="background:'+sc+';color:#fff;padding:1px 4px;border-radius:3px;">'+(sm[st]||st)+'</span></td>';
      html += '<td>'+(item.displayName||item.name||'?')+'</td>';
      html += '<td>'+(item.pageId||'')+'</td>';
      html += '<td>'+(item.role||'')+'</td>';
      html += '<td>'+(item.confidence||0).toFixed(2)+'</td></tr>';
    });
    html += '</table>';
    list.innerHTML = html;
  }).catch(function(e){
    document.getElementById('reviewDraftList').innerHTML = '<div style="padding:20px;color:red;">\u52a0\u8f7d\u5931\u8d25: '+e.message+'</div>';
  });
}

function showReviewDetail(path){
  _reviewSelectedPath = path;
  if(!path){ document.getElementById('reviewDetail').innerHTML = '<span style="color:#ccc;">\u9009\u62e9\u8349\u7a3f</span>'; return; }
  fetch('/api/mapping/get?path='+encodeURIComponent(path)).then(function(r){return r.json()}).then(function(d){
    var data = d.mapping || {};
    var sm = {'auto_draft':'\u5f85\u5ba1\u6838','manual_confirmed':'\u5df2\u786e\u8ba4','modified':'\u5df2\u4fee\u6539','rejected':'\u5df2\u62d2\u7edd','ignored':'\u5df2\u5ffd\u7565'};
    var html = '<div style="margin-bottom:6px;"><span style="background:#2196F3;color:#fff;padding:2px 6px;border-radius:3px;font-size:11px;">'+(sm[data.source]||data.source||'pending')+'</span></div>';
    var editFields = ['displayName','testId','semanticId','role','chineseDescription'];
    var allFields = [
      ['\u4e2d\u6587\u540d\u79f0','displayName',true],['\u4e2d\u6587\u63cf\u8ff0','chineseDescription',true],
      ['testId','testId',true],['semanticId','semanticId',true],['\u9875\u9762','pageId',true],
      ['\u89d2\u8272','role',true],['\u8def\u5f84','path',false],['\u7c7b\u578b','type',false],
      ['\u6587\u672c','text',false],['\u4fe1\u5ea6','confidence',false]
    ];
    allFields.forEach(function(f){
      var val = data[f[1]];
      if(val === undefined || val === null) val = '';
      if(typeof val === 'number') val = val.toFixed(2);
      if(f[2]){
        html += '<div style="margin-bottom:4px;"><label style="font-size:10px;color:#888;">'+f[0]+'</label>';
        html += '<input id="edit-'+f[1]+'" value="'+String(val).replace(/"/g,'&quot;')+'" style="width:100%;padding:2px;border:1px solid #ddd;border-radius:3px;font-size:11px;"></div>';
      } else {
        html += '<div style="margin-bottom:2px;"><span style="font-size:10px;color:#888;">'+f[0]+':</span> <span style="font-size:11px;">'+val+'</span></div>';
      }
    });
    html += '<div style="margin-top:8px;display:flex;gap:3px;flex-wrap:wrap;">';
    html += '<button class="btn btn-sm" style="background:#4CAF50;color:#fff;font-size:10px;" onclick="confirmReviewDraft()">\u2714 \u786e\u8ba4</button>';
    html += '<button class="btn btn-sm" style="background:#2196F3;color:#fff;font-size:10px;" onclick="saveReviewDraft()">\ud83d\udcbe \u4fdd\u5b58</button>';
    html += '<button class="btn btn-sm" style="background:#f44336;color:#fff;font-size:10px;" onclick="rejectReviewDraft()">\u2716 \u62d2\u7edd</button>';
    html += '<button class="btn btn-sm" style="background:#9E9E9E;color:#fff;font-size:10px;" onclick="ignoreReviewDraft()">\u23f3 \u5ffd\u7565</button>';
    html += '<button class="btn btn-sm" style="background:#FF9800;color:#fff;font-size:10px;" onclick="testClickReviewDraft()">\ud83d\udfe1 \u6d4b\u8bd5</button>';
    html += '</div><div id="reviewTestResult" style="margin-top:4px;font-size:11px;"></div>';
    document.getElementById('reviewDetail').innerHTML = html;
    document.getElementById('reviewHighlightInfo').textContent = (data.displayName||data.name||'') + ' - \u9ad8\u4eae';
  }).catch(function(e){
    document.getElementById('reviewDetail').innerHTML = '<div style="color:red;">\u52a0\u8f7d\u5931\u8d25: '+e.message+'</div>';
  });
}

function saveReviewDraft(){
  var data = {};
  ['displayName','chineseDescription','testId','semanticId','role'].forEach(function(k){
    var el = document.getElementById('edit-'+k);
    if(el) data[k] = el.value;
  });
  fetch('/api/mapping/drafts/'+encodeURIComponent(_reviewSelectedPath)+'/save', {
    method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)
  }).then(function(r){return r.json()}).then(function(d){
    document.getElementById('reviewTestResult').innerHTML = d.success ? '\u2714 \u5df2\u4fdd\u5b58' : '\u2716 '+d.error;
    if(d.success) loadReviewDrafts();
  });
}

function confirmReviewDraft(){
  fetch('/api/mapping/drafts/'+encodeURIComponent(_reviewSelectedPath)+'/confirm', {method:'POST'})
  .then(function(r){return r.json()}).then(function(d){
    document.getElementById('reviewTestResult').innerHTML = d.success ? '\u2714 \u5df2\u786e\u8ba4\uff0c\u5df2\u5bfc\u51fa\u6b63\u5f0f\u6620\u5c04' : '\u2716 '+d.error;
    if(d.success) loadReviewDrafts();
  });
}

function rejectReviewDraft(){
  fetch('/api/mapping/drafts/'+encodeURIComponent(_reviewSelectedPath)+'/reject', {method:'POST'})
  .then(function(r){return r.json()}).then(function(d){
    document.getElementById('reviewTestResult').innerHTML = d.success ? '\u2714 \u5df2\u62d2\u7edd' : '\u2716 '+d.error;
    if(d.success) loadReviewDrafts();
  });
}

function ignoreReviewDraft(){
  fetch('/api/mapping/drafts/'+encodeURIComponent(_reviewSelectedPath)+'/ignore', {method:'POST'})
  .then(function(r){return r.json()}).then(function(d){
    document.getElementById('reviewTestResult').innerHTML = d.success ? '\u2714 \u5df2\u5ffd\u7565' : '\u2716 '+d.error;
    if(d.success) loadReviewDrafts();
  });
}

function testClickReviewDraft(){
  document.getElementById('reviewTestResult').innerHTML = '\u6b63\u5728\u6d4b\u8bd5...';
  fetch('/api/mapping/drafts/'+encodeURIComponent(_reviewSelectedPath)+'/test_click', {method:'POST'})
  .then(function(r){return r.json()}).then(function(d){
    document.getElementById('reviewTestResult').innerHTML = d.success ? '\u2714 \u70b9\u51fb\u6210\u529f' : '\u2716 \u70b9\u51fb\u5931\u8d25: '+(d.detail||d.error);
  });
}
'''

content = content[:pos] + review_js + content[pos:]
with open('E:/zdcs/AutoSmoke/IDE/debug_panel.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done')
