function ml(m,l){var d=document.getElementById('mlog');var c=document.createElement('div');c.className='ml-e ml-'+l;c.textContent='['+new Date().toLocaleTimeString()+'] '+m;d.appendChild(c);d.scrollTop=d.scrollHeight;}
function log(m){ml(m,'i');}
function showMsg(targetId,msg,kind){
  if(!targetId||typeof targetId!=='string') return;
  var el=document.getElementById(targetId);
  if(!el) return;
  if(kind==='error'){el.innerHTML='<span style="color:#f44336;">'+msg+'</span>';}
  else if(kind==='warn'){el.innerHTML='<span style="color:#FF9800;">'+msg+'</span>';}
  else if(kind==='ok'){el.innerHTML='<span style="color:#4CAF50;">'+msg+'</span>';}
  else {el.innerHTML=msg;}
  var sb=document.getElementById('sbErr');
  if(sb){
    sb.textContent=typeof msg==='string'?msg.replace(/<[^>]+>/g,''):String(msg);
    sb.style.color=kind==='ok'?'#4CAF50':(kind==='warn'?'#FF9800':'#f44336');
  }
}
function setBusy(targetId,text){
  if(!targetId||typeof targetId!=='string') return;
  var el=document.getElementById(targetId);
  if(!el) return;
  el.textContent=text||'加载中...';
}
function apiPost(url,payload,cb,errTarget,errLabel){
  fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload||{})})
    .then(function(r){return r.json();})
    .then(function(d){if(cb){cb(d);}else if(d&&d.error){showMsg(errTarget,(errLabel||'请求')+'返回错误: '+d.error,'error');}})
    .catch(function(e){
      var msg=(errLabel||'请求')+'失败: '+e;
      ml(msg,'e');
      showMsg(errTarget,msg,'error');
    });
}
function apiGet(url,cb,errTarget,errLabel){
  fetch(url)
    .then(function(r){return r.json();})
    .then(function(d){if(cb){cb(d);}else if(d&&d.error){showMsg(errTarget,(errLabel||'请求')+'返回错误: '+d.error,'error');}})
    .catch(function(e){
      var msg=(errLabel||'请求')+'失败: '+e;
      ml(msg,'e');
      showMsg(errTarget,msg,'error');
    });
}
var rp='';var runCtx={};var stateDiffBase=null;var precheckState={status:'UNKNOWN',canExecute:true,lastCheckedAt:0};var precheckWarmupDone=false;var precheckPendingRun=null;var precheckBlockerCache=[];
function setRunCtx(batch){if(!batch){runCtx={};return;}runCtx={reportPath:batch.report_path||batch.batchReport||batch.report||'',batchName:batch.batch_name||batch.batchName||'',total:batch.total_cases||batch.total||0,passed:batch.passed_cases||batch.passed||0,failed:batch.failed_cases||batch.failed||0,lastUpdate:new Date().toLocaleTimeString(),runId:batch.run_id||batch.batch_name||''};}
function collectCaseCtx(){var caseFile=document.getElementById('caseFile');var p='';if(caseFile)p=caseFile.value||'';var res=(document.getElementById('cfgRes').value||'1170x2532').split('x');var w=parseInt(res[0],10);var h=parseInt(res[1],10);var o={path:p.trim(),unityProject:(document.getElementById('cfgUnityPath').value||'').trim(),autosmokeRoot:(document.getElementById('cfgRoot').value||'').trim(),pocoPath:(document.getElementById('cfgPoco').value||'').trim(),designWidth:isNaN(w)?1170:w,designHeight:isNaN(h)?2532:h,stepField:'操作步骤',caseIdField:'用例ID'};apiPost('/api/case/context',o,function(){});return o;}

function swt(n){
  try{
    var tabs=['prepare','execute','results'];
    var i=tabs.indexOf(n);
    if(i<0){ ml('主标签参数无效: '+n,'w'); return; }
    var topts=document.querySelectorAll('.toptab');
    var panes=document.querySelectorAll('.tabcontent');
    topts.forEach(function(t){t.classList.remove('active');});
    panes.forEach(function(t){t.classList.remove('active');});
    if(topts[i]){topts[i].classList.add('active');}
    else{ml('主标签按钮不存在: '+n,'w');}
    var p=document.getElementById('tab-'+n);
    if(p){p.classList.add('active');}else{ml('主标签面板不存在: tab-'+n,'w');}
    if(n==='execute'&&!precheckWarmupDone){
      precheckWarmupDone=true;
      setTimeout(function(){preCheck();},300);
    }
  }catch(e){
    ml('主标签切换异常: '+e,'e');
    console.error(e);
  }
}
function showMeta(n){
  try{
    var ok=['mapping','list','accessibility','status','scan'];
    var valid=ok.indexOf(n) >= 0;
    if(!valid){
      ml('元数据页签参数无效: '+n,'w');
      return;
    }
    ok.forEach(function(t){
      var e=document.getElementById('meta-'+t);
      if(e){ e.style.display=t===n ? 'block' : 'none';}
    });
    if(n==='mapping')ldDrafts();
    if(n==='list')ldMaps();
    if(n==='status')ldMetaSt();
  }catch(e){
    ml('元数据页面切换异常: '+e,'e');
    console.error(e);
  }
}
function _bindTabsSafe(){
  try{
    var topTabs = document.querySelectorAll('.toptab[data-tab]');
    topTabs.forEach(function(t){
      t.onclick = null;
      t.addEventListener('click', function(){ swt(t.getAttribute('data-tab')); });
    });
    var metaTabs = document.querySelectorAll('.meta-subtab[data-meta]');
    metaTabs.forEach(function(t){
      t.onclick = null;
      t.addEventListener('click', function(){ showMeta(t.getAttribute('data-meta')); });
    });
    var goScan = document.getElementById('metaGoScan');
    if (goScan) {
      goScan.onclick = null;
      goScan.addEventListener('click', function(){ openMetaScan(); });
    }
  }catch(e){
    console.error('绑定页签事件失败:', e);
  }
}
function _bindTabsSafeCapture(ev){
  var target = ev && ev.target ? ev.target : null;
  if (!target) return;
  var t = target.closest ? target.closest('[data-tab],.meta-subtab[data-meta],#metaGoScan') : null;
  if (!t) return;
  if (t.classList.contains('toptab')) {
    ev.preventDefault();
    swt(t.getAttribute('data-tab'));
  } else if (t.classList.contains('meta-subtab')) {
    ev.preventDefault();
    showMeta(t.getAttribute('data-meta'));
  } else if (t.id === 'metaGoScan') {
    ev.preventDefault();
    openMetaScan();
  }
}
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', _bindTabsSafe);
} else {
  _bindTabsSafe();
}
document.addEventListener('click', _bindTabsSafeCapture, true);
document.addEventListener('touchend', _bindTabsSafeCapture, true);
function openMetaScan(){
  showMeta('scan');
  var input = document.getElementById('metaImportDir');
  if (input && !input.value) {
    input.value = 'E:\\\\zdcs\\\\AutoSmoke\\\\runtime\\\\ui_tree';
  }
  if (input) input.focus();
}
function openMetaPagesImport(){
  openMetaScan();
  setTimeout(function(){importUi('pages');}, 60);
}
function sStep(v){document.getElementById('stepInp').value=v;}
function escHtml(v){var s=String(v==null?'':v);return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\"/g,'&quot;').replace(/'/g,'&#39;');}
function precheckAutoRetryEnabled(){var el=document.getElementById('precheckAutoRetry');return !!(el&&el.checked);}
function _setPrecheckRunPlan(fn){precheckPendingRun=fn?{fn:fn,createdAt:Date.now()}:null;}
function _takePrecheckRunPlan(){var plan=precheckPendingRun;precheckPendingRun=null;return plan&&plan.fn;}
function doPrecheckQuickFix(action){if(!action)return;var act=typeof action==='string'?action:(action&&action.getAttribute?action.getAttribute('data-action'):'');if(!act)return;precheckState.status='RUNNING';switch(act){case 'open_config':swt('prepare');loadCfg();ml('已切换到环境配置');break;case 'refresh_case_ctx':loadCases();collectCaseCtx();ml('已刷新用例上下文');break;case 'run_deploy':depRun();ml('已触发部署脚本');break;case 'rerun_locate':refSt();break;case 'run_capture':cap();ml('已触发截图通道校验');break;case 'refresh_status':chkAll();ml('已刷新基础状态');break;case 'run_relocate':refSt();break;case 'open_case_file':loadCases();swt('prepare');if(document.getElementById('caseFile'))document.getElementById('caseFile').focus();ml('请检查用例文件输入');break;default:ml('未识别修复动作: '+act);break;}setTimeout(function(){preCheck(function(){if(precheckState&&precheckState.canExecute===false){ml('阻塞项仍存在，请继续处理','w');return;}if(!precheckAutoRetryEnabled()){ml('修复已执行，预检通过');return;}var nextRun=_takePrecheckRunPlan();if(!nextRun){ml('修复已执行，未检测到待执行任务');return;}ml('阻塞已处理，自动继续执行');nextRun();});},1200);}

// ===== 健康 =====
function chkAll(){ml('健康检查...');apiGet('/api/status',function(d){var h='<table class="st">';Object.keys(d).slice(0,12).forEach(function(k){var v=d[k];if(typeof v==='object')v=JSON.stringify(v).slice(0,80);h+='<tr><td style="color:#888;">'+k+'</td><td>'+v+'</td></tr>';});h+='</table>';document.getElementById('hGrid').innerHTML=h;document.getElementById('hScore').textContent=d.status==='OK'?'OK':'ERROR';document.getElementById('tsu').textContent=d.status==='OK'?'已连接':'未连接';document.getElementById('tsu').className=d.status==='OK'?'ts-ok':'ts-bad';});}
function chkDeps(){document.getElementById('depsR').innerHTML='<span style="color:#4CAF50;">Python 3.13 | Flask 3.x | Pillow 12 | OpenCV 4.13 | Tesseract 5.4</span>';}

// ===== 配置 =====
function loadCfg(){apiGet('/api/config',function(d){if(!d || d.status==='ERROR'){apiGet('/api/status',function(s){document.getElementById('cfgUnityPath').value=s.unityProject||'';document.getElementById('cfgRoot').value=s.autosmokeRoot||'';document.getElementById('cfgPoco').value=s.pocoPath||'';document.getElementById('cfgRes').value=(s.designWidth||'1170')+'x'+(s.designHeight||'2532');document.getElementById('cfgR').textContent='已加载';collectCaseCtx();});return;}document.getElementById('cfgUnityPath').value=d.unityProject||'';document.getElementById('cfgRoot').value=d.autosmokeRoot||'';document.getElementById('cfgPoco').value=d.pocoPath||'';document.getElementById('cfgRes').value=(d.designWidth||'1170')+'x'+(d.designHeight||'2532');document.getElementById('cfgR').textContent='已加载';collectCaseCtx();});}
function saveCfg(){var r=document.getElementById('cfgRes').value||'';var parts=r.split('x');var payload={unityProject:document.getElementById('cfgUnityPath').value,pocoPath:document.getElementById('cfgPoco').value,designWidth:parseInt(parts[0]||'1170',10)||1170,designHeight:parseInt(parts[1]||'2532',10)||2532,};apiPost('/api/config',payload,function(d){document.getElementById('cfgR').textContent=d.status==='OK'?'已保存':'保存失败';ml('配置保存: '+document.getElementById('cfgR').textContent);collectCaseCtx();});}

// ===== 定位 =====
function refSt(){ml('刷新定位...');fetch('/api/relocate',{method:'POST'}).then(function(r){return r.json()}).then(function(d){document.getElementById('locDet').innerHTML=JSON.stringify(d).slice(0,200);document.getElementById('tsu').textContent=d.status==='OK'?'已连接':'未连接';document.getElementById('tsu').className=d.status==='OK'?'ts-ok':'ts-bad';ml('定位完成');}).catch(function(e){ml('定位失败','e');});}

// ===== 截图 =====
function cap(){fetch('/api/capture').then(function(r){return r.json()}).then(function(d){if(d.game_content_path){document.getElementById('monitorImg').src='/api/screenshot/'+encodeURIComponent(d.game_content_path)+'?t='+Date.now();document.getElementById('monitorImg').style.display='block';document.getElementById('noMonitorImg').style.display='none';var b=document.getElementById('capBdg');b.textContent=d.capture_mode==='unity'?'Unity':'Python';b.className='bdg '+(d.capture_mode==='unity'?'bg-b':'bg-y');ml('截图');}});}

// ===== 点击/步骤 =====
function tClick(){ml('测试点击...');fetch('/api/click_test',{method:'POST'}).then(function(r){return r.json()}).then(function(d){document.getElementById('clickR').innerHTML='结果: '+(d.result||'?')+' | 差异: '+(d.diff_ratio||0);ml('点击: '+(d.result||'?'));}).catch(function(e){ml('点击失败','e');});}
function exStep(){var t=document.getElementById('stepInp').value.trim();if(!t)return;ml('执行: '+t);fetch('/api/execute',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:t})}).then(function(r){return r.json()}).then(function(d){var r2=d.step_result||d;document.getElementById('stepR').innerHTML=JSON.stringify(r2,null,2).replace(/\n/g,'<br>');ml('结果: '+r2.result);}).catch(function(e){ml('执行失败','e');});}

// ===== 部署 =====
function depChk(){fetch('/api/deploy_check').then(function(r){return r.json()}).then(function(d){document.getElementById('hGrid').innerHTML='<span style="color:#4CAF50;">脚本: '+(d.deployed?'已部署':'待部署')+' | '+(d.count||0)+'个</span>';});}
function depRun(){fetch('/api/deploy_run',{method:'POST'}).then(function(r){return r.json()}).then(function(d){ml('部署: '+(d.success?'成功':'失败'));});}

// ===== 阻塞 =====
function detBlk(){fetch('/api/blocker_detect').then(function(r){return r.json()}).then(function(d){document.getElementById('blkR').innerHTML=JSON.stringify(d,null,2).replace(/\n/g,'<br>');ml('阻塞检测完成');});}
function resBlk(){fetch('/api/blocker_resolve',{method:'POST'}).then(function(r){return r.json()}).then(function(d){document.getElementById('blkR').innerHTML=JSON.stringify(d,null,2).replace(/\n/g,'<br>');ml('阻塞处理完成');});}

// ===== 元数据 =====
function ldMetaSt(){fetch('/api/metadata').then(function(r){return r.json()}).then(function(d){document.getElementById('metaSt').innerHTML=JSON.stringify(d,null,2).replace(/\n/g,'<br>');});}
function scAcc(){fetch('/api/accessibility/scan').then(function(r){return r.json()}).then(function(d){document.getElementById('accR').innerHTML=JSON.stringify(d,null,2).replace(/\n/g,'<br>');ml('可测性扫描完成');});}
function ldMaps(){fetch('/api/mapping/list').then(function(r){return r.json()}).then(function(d){var items=d.mappings||[];var h='<table class="st"><tr style="background:#f5f5f5;"><td>名</td><td>testId</td><td>角色</td></tr>';items.forEach(function(m){h+='<tr><td>'+(m.displayName||m.name||'')+'</td><td>'+(m.testId||'')+'</td><td>'+(m.role||'')+'</td></tr>';});h+='</table>';document.getElementById('mapL').innerHTML=h;document.getElementById('mapStats').textContent=items.length+'条';});}

// ===== 审核 =====
 var rp='';
function _normDraftStatus(v){
  var s=(v||'').toLowerCase();
  if(s==='manual_confirmed'){return 'click_confirmed';}
  if(s==='auto_draft'){return 'pending';}
  return s || 'pending';
}
function _draftStatusText(v){
  var s=_normDraftStatus(v);
  var map={
    'pending':'待审核',
    'structure_confirmed':'结构确认',
    'visual_confirmed':'视觉确认',
    'click_confirmed':'点击确认',
    'modified':'人工修改',
    'ignored':'已忽略',
    'rejected':'已拒绝',
  };
  return map[s]||s||'待审核';
}
function _draftStatusClass(v){
  var s=_normDraftStatus(v);
  if(s==='pending'||s==='auto_draft') return 'bg-y';
  if(s==='structure_confirmed') return 'bg-b';
  if(s==='visual_confirmed') return 'bg-g';
  if(s==='click_confirmed') return 'bg-r';
  if(s==='modified') return 'bg-b';
  if(s==='rejected') return 'bg-r';
  return 'bg-y';
}
function ldDrafts(){
  var kw = document.getElementById('rkw').value;
  var stt = document.getElementById('rst').value;
  var url = '/api/mapping/drafts?keyword='+encodeURIComponent(kw);
  if(stt)url+='&status='+encodeURIComponent(stt);
  fetch(url).then(function(r){return r.json()}).then(function(d){
    var list = document.getElementById('rdl');
    var total=d.total||0;
    document.getElementById('rStats').textContent=total+'条';
    if(!d.drafts||d.drafts.length===0){
      list.innerHTML='<div style="padding:10px;text-align:center;color:#ccc;">无草稿</div>';
      return;
    }
    var h='<table class="st"><tr style="background:#f5f5f5;"><td>状态</td><td>名称</td><td>信度</td></tr>';
    d.drafts.forEach(function(it){
      var st=it.reviewStatus||it.source||'pending';
      var c=_draftStatusClass(st);
      var path=it.path||'';
      var p=encodeURIComponent(path);
      h += '<tr class="draft-row" data-path="'+p+'" style="cursor:pointer;"><td><span class="bdg '+c+'">'+_draftStatusText(st)+'</span></td><td>'+(it.displayName||it.name||'?')+'</td><td>'+(it.confidence||0).toFixed(2)+'</td></tr>';
    });
    h+='</table>';
    list.innerHTML=h;
    Array.from(list.querySelectorAll('tr.draft-row')).forEach(function(tr){
      tr.addEventListener('click', function(){shDraft(decodeURIComponent(tr.getAttribute('data-path')||''));});
    });
  });
}
function shDraft(p){rp=p;if(!p){document.getElementById('rDet').innerHTML='<span style=\"color:#ccc;\">选择草稿</span>';return;}fetch('/api/mapping/get?path='+encodeURIComponent(p)).then(function(r){return r.json()}).then(function(d){var data=d.mapping||{};var st=data.reviewStatus||data.source||'pending';var c=_draftStatusClass(st);var badge=_draftStatusText(st);var hasImg=!!((data.screenshotRef&&String(data.screenshotRef).trim())||data.hasScreenshot);var h='<div><span class=\"bdg '+c+'\">'+badge+'</span></div>';[['path','节点路径',1],['displayName','显示名称',1],['chineseDescription','中文描述',1],['text','显示文本',0],['role','角色',1],['pageId','页面',1],['testId','testId',1],['runtimePath','runtimePath',0],['prefabPath','prefabPath',0],['spriteName','spriteName',0],['nodeName','nodeName',0],['components','组件',0],['suggestedTestId','推荐testId',0],['suggestedSemanticId','推荐semanticId',0],['reviewHint','建议',0]].forEach(function(f){var v=data[f[1]];if(v===undefined||v===null)v='';if(Array.isArray(v))v=v.join(',');if(typeof v==='object'){v=JSON.stringify(v);}h+='<div style=\"margin:2px 0;\"><label style=\"font-size:9px;color:#888;\">'+f[0]+'</label><input id=\"e-'+f[1]+'\" value=\"'+String(v).replace(/\"/g,'&quot;')+'\" style=\"width:100%;padding:1px;font-size:10px;border:1px solid #ddd;\" '+(f[2]? '':'readonly')+'></div>';});if(!hasImg){h+='<div style=\"margin:2px 0;padding:2px;background:#FFF3CD;color:#9C6500;\">'+(data.reviewWarnings&&data.reviewWarnings.length?data.reviewWarnings[0]:'缺少页面截图，仅可结构确认')+'</div>';}h+='<div style=\"margin-top:4px;display:flex;gap:2px;flex-wrap:wrap;\"><button class=\"btn btn-sm\" style=\"background:#2196F3;color:#fff;\" onclick=\"cfD(\'structure\')\">结构确认</button><button class=\"btn btn-sm\" style=\"background:#4CAF50;color:#fff;\" onclick=\"cfD(\'visual\')\" '+(hasImg?'':'disabled')+'>视觉确认</button><button class=\"btn btn-sm\" style=\"background:#7B1FA2;color:#fff;\" onclick=\"cfD(\'click\')\">点击确认</button><button class=\"btn btn-sm\" style=\"background:#03A9F4;color:#fff;\" onclick=\"svD()\">保存</button><button class=\"btn btn-sm\" style=\"background:#f44336;color:#fff;\" onclick=\"rjD()\">拒绝</button><button class=\"btn btn-sm\" style=\"background:#9E9E9E;color:#fff;\" onclick=\"igD()\">忽略</button></div><div id=\"rr\" style=\"margin-top:3px;font-size:10px;\"></div>';document.getElementById('rDet').innerHTML=h;document.getElementById('rHi').textContent=(data.displayName||data.name||'')+' - 高亮';});}
function svD(){var d={};['displayName','chineseDescription','testId','role'].forEach(function(k){var el=document.getElementById('e-'+k);if(el)d[k]=el.value;});fetch('/api/mapping/drafts/'+encodeURIComponent(rp)+'/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)}).then(function(r){return r.json()}).then(function(d){document.getElementById('rr').innerHTML=d.success?'已保存':'失败';if(d.success)ldDrafts();});}
function cfD(level){var levelName=(level||'structure').toLowerCase();var p='click_confirmed';if(levelName==='structure')p='structure_confirmed';else if(levelName==='visual')p='visual_confirmed';fetch('/api/mapping/drafts/'+encodeURIComponent(rp)+'/confirm/'+p,{method:'POST'}).then(function(r){if(!r.ok){return r.json().then(function(j){throw new Error(j&&j.error?j.error:'请求失败');});}return r.json();}).then(function(d){document.getElementById('rr').innerHTML=d.success?'已标记为 '+_draftStatusText(p):'失败';if(d.success)ldDrafts();});}
function rjD(){fetch('/api/mapping/drafts/'+encodeURIComponent(rp)+'/reject',{method:'POST'}).then(function(r){return r.json()}).then(function(d){document.getElementById('rr').innerHTML=d.success?'已拒绝':'失败';if(d.success)ldDrafts();});}
function igD(){fetch('/api/mapping/drafts/'+encodeURIComponent(rp)+'/ignore',{method:'POST'}).then(function(r){return r.json()}).then(function(d){document.getElementById('rr').innerHTML=d.success?'已忽略':'失败';if(d.success)ldDrafts();});}

// ===== before/after =====
var bp='',aap='';
function cpB(){fetch('/api/capture').then(function(r){return r.json()}).then(function(d){if(d.game_content_path){bp=d.game_content_path;['bi','bi2'].forEach(function(id){var el=document.getElementById(id);if(el){el.src='/api/screenshot/'+encodeURIComponent(d.game_content_path)+'?t='+Date.now();el.style.display='block';}});['noBi','noBi2'].forEach(function(id){var el=document.getElementById(id);if(el)el.style.display='none';});}});}
function cpA(){fetch('/api/capture').then(function(r){return r.json()}).then(function(d){if(d.game_content_path){aap=d.game_content_path;['ai','ai2'].forEach(function(id){var el=document.getElementById(id);if(el){el.src='/api/screenshot/'+encodeURIComponent(d.game_content_path)+'?t='+Date.now();el.style.display='block';}});['noAi','noAi2'].forEach(function(id){var el=document.getElementById(id);if(el)el.style.display='none';});}});}
function cpC(){if(!bp||!aap){ml('请先拍摄 before/after','w');return;}fetch('/api/compare',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({before:bp,after:aap})}).then(function(r){return r.json()}).then(function(d){['cmpR','cmpR2'].forEach(function(id){var el=document.getElementById(id);if(el)el.innerHTML='差异: '+(d.diff||d.diff_ratio||'?');});if(d.highlight_path){['diffC','diffC2'].forEach(function(id){var el=document.getElementById(id);if(el)el.innerHTML='<img src="/api/screenshot/'+encodeURIComponent(d.highlight_path)+'" style="max-width:100%;max-height:100px;border-radius:4px;">';});}ml('对比: '+(d.diff||d.diff_ratio||'?'));});}
function importUi(mode){
  var dir = (document.getElementById('metaImportDir') && document.getElementById('metaImportDir').value) ? document.getElementById('metaImportDir').value : '';
  setBusy('meta-status','导入中...');
  apiPost('/api/ui/import', {mode: mode, sourceDir: dir}, function(d){
    var info = document.getElementById('uiImportInfo');
    if(info){
      if(!d || !d.success){
        info.style.color = '#f44336';
        info.textContent = '导入失败: ' + ((d && d.error) || '未知错误');
      }else{
        info.style.color = '#4CAF50';
        var stat = d.validation && d.validation.stats ? d.validation.stats : {};
        var p = (d.validation && d.validation.ok !== undefined) ? (d.validation.ok ? '通过' : '警告') : '未知';
        info.textContent = '导入成功: ' + d.file + '；校验' + p + '；节点' + (stat.nodeCount || 0) + '；草稿' + (d.drafts && d.drafts.count || 0);
        info.title = JSON.stringify(d.validation || {}, null, 2);
      }
    }
    document.getElementById('meta-status').innerHTML = JSON.stringify(d, null, 2).replace(/\\n/g, '<br>');
    ml('UI导入: ' + (d.success ? '完成' : '失败'));
    ldDrafts();
    ldMaps();
    scanUiTree();
  }, 'meta-status', 'UI导入');
}
function importUiByFile(){
  var file = (document.getElementById('metaImportFile') && document.getElementById('metaImportFile').value) ? document.getElementById('metaImportFile').value : '';
  if(!file){ml('请先填写手工导入路径','w');return;}
  setBusy('meta-status','导入中...');
  apiPost('/api/ui/import', {mode:'current', sourceFile: file}, function(d){
    var info = document.getElementById('uiImportInfo');
    if(info){
      if(!d || !d.success){
        info.style.color = '#f44336';
        info.textContent = '导入失败: ' + ((d && d.error) || '未知错误');
      }else{
        info.style.color = '#4CAF50';
        var stat = d.validation && d.validation.stats ? d.validation.stats : {};
        info.textContent = '手工导入成功: ' + d.file + '；节点' + (stat.nodeCount || 0) + '；草稿' + (d.drafts && d.drafts.count || 0);
        info.title = JSON.stringify(d.validation || {}, null, 2);
      }
    }
    document.getElementById('meta-status').innerHTML = JSON.stringify(d, null, 2).replace(/\\n/g, '<br>');
    ldDrafts();
    ldMaps();
    scanUiTree();
    ml('UI导入: ' + (d.success ? '完成' : '失败'));
  }, 'meta-status', 'UI导入');
}
function importUiReport(){
  apiGet('/api/ui/import/report',function(d){
    var info = document.getElementById('uiImportInfo');
    if(info){
      if(!d || !d.success){
        info.style.color = '#f44336';
        info.textContent = '读取导入报告失败: ' + ((d && d.error) || '未知错误');
      }else{
        var rpt = d.report || {};
        var lines = [];
        lines.push('报告路径: ' + (rpt.source || '-'));
        if(rpt.sourceDir){ lines.push('目录: ' + rpt.sourceDir);}
        if(rpt.stats){ lines.push('命中节点: ' + (rpt.stats.nodeCount || 0));}
        if(rpt.stats){ lines.push('错误: ' + (rpt.stats.errorCount || 0) + '，警告: ' + (rpt.stats.warningCount || 0));}
        if(rpt.generatedAt){ lines.push('生成: ' + rpt.generatedAt);}
        info.style.color = '#4CAF50';
        info.innerHTML = '导入报告: ' + lines.join('；') + '<br/><span style=\"color:#999;\">' + JSON.stringify(rpt, null, 2) + '</span>';
      }
      document.getElementById('meta-status').innerHTML = JSON.stringify(d, null, 2).replace(/\\n/g,'<br>');
      ml('读取导入报告: ' + (d.success ? '完成' : '失败'));
    }
  });
}
function scanUiTree(){setBusy('meta-status','扫描中...');apiGet('/api/ui_scan?kind=current',function(d){document.getElementById('meta-status').innerHTML=JSON.stringify(d,null,2).replace(/\\n/g,'<br>');ml('UI树扫描: '+(d.success?'完成':'失败'));var info=document.getElementById('metaScanInfo');if(d&&d.stats){var file=d.stats.file||'';if(info){info.style.color='#888';info.textContent='当前UI树: '+(d.stats.nodeCount||0)+'节点；导入文件: '+(file||'未命中');info.title=file||'';var candidates=(d.candidates||[]).slice(0,3).filter(function(p){return p;}).join('；');if(candidates)info.textContent+='；候选1: '+candidates;}}},'meta-status','UI树扫描');}
function scanPrefab(){setBusy('meta-status','扫描中...');apiGet('/api/ui_scan?kind=prefab',function(d){document.getElementById('meta-status').innerHTML=JSON.stringify(d,null,2).replace(/\\n/g,'<br>');ml('Prefab扫描: '+(d.success?'完成':'失败'));var info=document.getElementById('metaScanInfo');if(d&&d.stats){var file=d.stats.file||'';if(info){info.style.color='#888';info.textContent='工程态: '+(file||'未命中')+' ('+(d.stats.nodeCount||0)+'节点)';info.title=file||'';var candidates=(d.candidates||[]).slice(0,3).filter(function(p){return p;}).join('；');if(candidates)info.textContent+='；候选1: '+candidates;}}},'meta-status','Prefab扫描');}
function startExplore(){
  var body={startPage:document.getElementById('pgStart').value||'MainCity',maxDepth:parseInt(document.getElementById('pgDepth').value||'3',10)||3,maxClicks:parseInt(document.getElementById('pgClicks').value||'50',10)||50,dangerWords:(document.getElementById('pgDanger').value||'').split(',').map(function(i){return i.trim();}).filter(function(i){return i;})};
  setBusy('pgR','自动探索中...');
  apiPost('/api/explore/run',body,function(d){
    if(!d){document.getElementById('pgR').innerHTML='探索接口无返回';return;}
    var h='';
    if(d.success){
      var pages=(d.stats&& (d.stats.pages!=null?d.stats.pages:d.stats.pageList?d.stats.pageList.length:null))||0;
      var edges=(d.stats&&d.stats.edges!=null)?d.stats.edges:0;
      h+='页面: '+pages+'，边: '+edges;
      if(d.stats&&d.stats.maxDepth!=null)h+='，深度: '+d.stats.maxDepth;
      if(d.report&&d.report.page_graph_exists)h+='<br>图谱文件: '+d.report.page_graph;
      if(d.report&&d.report.page_graph_exists&&d.stats&&d.stats.generated!=null)h+=' | 已持久化: '+d.stats.generated+'页';
      if(d.message)h+='<br>'+d.message;
    }else{
      h='探索失败：'+(d.message||'未知错误');
    }
    document.getElementById('pgR').innerHTML=h;
    loadPageGraphInfo();
    ml('自动探索: '+(d.success?'完成':'失败'));
  },'pgR','自动探索');
}
function checkLogin(){apiGet('/api/login/check',function(d){var el=document.getElementById('envGuide');if(!el)return;el.textContent=d.logged_in?'已登录':'未登录';el.style.color=d.logged_in?'#4CAF50':'#f44336';ml('登录检查: '+(d.logged_in?'通过':'未通过'));});}
function resetStateDiff(){
  document.getElementById('stateDiff').textContent='正在重置状态基准...';
  apiPost('/api/state/diff',{reset:true},function(d){
    if(!d){document.getElementById('stateDiff').innerHTML='重置失败';return;}
    if(!d.success){
      document.getElementById('stateDiff').innerHTML='重置失败：'+(d.error||'未知错误');
      return;
    }
    document.getElementById('stateDiff').innerHTML=(d.message||'基准已重置')+'（建议执行一次刷新）';
    loadStateDiff();
  });
}
function _renderStateDiff(d){
  if(!d){document.getElementById('stateDiff').innerHTML='无法获取状态';return;}
  if(d.success===false){document.getElementById('stateDiff').innerHTML='状态获取失败：'+(d.error||'未知错误');return;}
  var changed=Array.isArray(d.changed)?d.changed:[];
  var before=d.before||{};
  var after=d.after||{};
  var totalBefore=typeof before==='object'&&before?Object.keys(before).length:0;
  var totalAfter=typeof after==='object'&&after?Object.keys(after).length:0;
  var h='状态基线: '+totalBefore+'项，当前: '+totalAfter+'项';
  if(d.message) h+='<br>'+d.message;
  if(!changed.length){
    h+='<br>无变化项';
  }else{
    h+='<br>差异项('+changed.length+'):';
    changed.forEach(function(i){
      h+='<div>'+i.key+': '+(i.before===undefined?'':String(i.before))+' -> '+(i.after===undefined?'':String(i.after))+'</div>';
    });
  }
  document.getElementById('stateDiff').innerHTML=h;
}
function loadStateDiff(){setBusy('stateDiff','正在刷新...');apiGet('/api/state/diff',function(d){_renderStateDiff(d);},'stateDiff','状态Diff刷新');}
function loadPageGraphInfo(){
  setBusy('pgR','读取图谱状态...');
  apiGet('/api/page_graph/info',function(d){
    if(!d){document.getElementById('pgR').innerHTML='图谱状态读取失败';return;}
    if(d.success===false){
      document.getElementById('pgR').innerHTML='图谱状态读取失败：'+(d.error||'未知错误');
      return;
    }
    var pages=(d.stats&&d.stats.pages!=null)?d.stats.pages:0;
    var edges=(d.stats&&d.stats.edges!=null)?d.stats.edges:0;
    var h='页面: '+pages+'，边: '+edges;
    h+=' | 页面图: '+(d.pageGraphExists?'已生成':'未生成');
    if(d.pageGraphPath)h+='<br>JSON: '+d.pageGraphPath;
    if(d.htmlPath)h+='<br>HTML: '+d.htmlPath;
    if(d.updatedAt)h+='<br>更新时间: '+d.updatedAt;
    document.getElementById('pgR').innerHTML=h;
  },'pgR','图谱状态读取');
}

function _setRunResult(batch){if(!batch)return;setRunCtx(batch);var total=batch.total_cases||batch.total||0;var passed=batch.passed_cases||batch.passed||0;var failed=(batch.failed_cases!=null?batch.failed_cases:(total-passed));var h='本次执行: '+total+'例，PASS '+passed+'，FAIL '+failed;document.getElementById('lastR').textContent=h;document.getElementById('caseR').innerHTML=h;document.getElementById('failCnt').textContent=failed;var failList=[];(batch.case_results||[]).forEach(function(c){if((c.result||'').toUpperCase()!=='PASS'){failList.push((c.case_id||'未知')+'：'+(c.result||'FAIL'));}});document.getElementById('failR').innerHTML=failList.length?failList.join('<br>'):'无失败记录';document.getElementById('sbSt').textContent='完成';document.getElementById('sbSt').className='bdg bg-g';document.getElementById('sbCase').textContent=batch.batch_name||batch.batchName||'完成';loadStateDiff();}

// ===== 异常 =====
function chkAno(){fetch('/api/anomaly/check').then(function(r){return r.json()}).then(function(d){var h='崩溃:'+(d.crash?d.crash.detail:'正常')+' | 卡死:'+(d.hang?d.hang.detail:'正常');document.getElementById('anoR').innerHTML=h+' | 日志:'+d.log.total_entries+'条';document.getElementById('anoDet').innerHTML=h;ml('异常检测');});}
function vLog(){fetch('/api/anomaly/log').then(function(r){return r.json()}).then(function(d){var h='<table class="st"><tr style="background:#f5f5f5;"><td>级别</td><td>消息</td></tr>';(d.entries||[]).slice(0,15).forEach(function(e){h+='<tr><td>'+(e.level||'')+'</td><td>'+(e.message||'').slice(0,60)+'</td></tr>';});h+='</table>';document.getElementById('anoDet').innerHTML=h;document.getElementById('logPreview').innerHTML=h;ml('日志已加载');});}
function clrAno(){document.getElementById('anoDet').innerHTML='';ml('异常已清空');}

// ===== 用例 =====
function ensurePrecheckAndRun(next){
  var now=Date.now();
  if(precheckState&&precheckState.lastCheckedAt&&(now-precheckState.lastCheckedAt)<=60000){
    if(precheckState&&precheckState.canExecute===false){
      _setPrecheckRunPlan(typeof next==='function'?next:null);
      ml('存在阻塞项，建议先执行预检并修复'+(precheckAutoRetryEnabled()?'，修复后将自动重试':''));
      return;
    }
    if(next){next();}return;
  }
  _setPrecheckRunPlan(typeof next==='function'?next:null);
  ml('执行前预检中...');
    preCheck(function(){
    if(precheckState&&precheckState.canExecute===false){ml('存在阻塞项，建议先执行预检并修复'+(precheckAutoRetryEnabled()?'，修复后将自动重试':''));return;}
    var nextRun=_takePrecheckRunPlan();
    if(nextRun){nextRun();}
  });
}
function runCase(){ensurePrecheckAndRun(function(){var caseId=document.getElementById('caseSel').value;if(!caseId){ml('请先选择用例','w');return;}var payload=collectCaseCtx();payload.caseId=caseId;document.getElementById('sbCase').textContent='运行中';document.getElementById('sbSt').textContent='运行中';document.getElementById('sbSt').className='bdg bg-y';apiPost('/api/case/run',payload,function(d){if(!d.success){document.getElementById('caseR').innerHTML='失败: '+d.error;document.getElementById('sbSt').textContent='失败';document.getElementById('sbSt').className='bg-r';ml('用例执行失败: '+d.error,'e');return;}_setRunResult(d.batch||d);});});}
function batchRun(){ensurePrecheckAndRun(function(){var payload=collectCaseCtx();document.getElementById('sbCase').textContent='批量执行中';document.getElementById('sbSt').textContent='运行中';document.getElementById('sbSt').className='bdg bg-y';apiPost('/api/case/run_batch',payload,function(d){if(!d.success){document.getElementById('sbSt').textContent='失败';document.getElementById('sbSt').className='bg-r';document.getElementById('caseR').innerHTML='失败: '+d.error;ml('批量执行失败: '+d.error,'e');return;}_setRunResult(d.batch||d);});});}

// ===== 结果 =====
function ldHist(){fetch('/api/report/list').then(function(r){return r.json()}).then(function(d){var items=d.reports||[];var totalFail=0;var h='<table class="st"><tr style="background:#f5f5f5;"><td>时间</td><td>通过率</td><td>失败</td></tr>';items.slice(0,10).forEach(function(r){var fail=Math.max(0,(r.total||0)-(r.passed||0));totalFail+=fail;h+='<tr><td>'+r.time+'</td><td>'+r.passed+'/'+r.total+'</td><td>'+fail+'</td></tr>';});h+='</table>';document.getElementById('histR').innerHTML=h;document.getElementById('histCnt').textContent=items.length;document.getElementById('failCnt').textContent=totalFail;ml('历史: '+items.length+'条');}).catch(function(e){document.getElementById('histR').innerHTML='暂无报告';});}
function expRpt(){if(!runCtx.reportPath){ml('请先执行一批用例','w');return;}apiPost('/api/report/export/html',{batch_report:runCtx.reportPath},function(d){if(d&&d.success){document.getElementById('expR').innerHTML='<a style="color:#4CAF50;" href="'+(d.download||'')+'" target="_blank">下载HTML</a>';ml('HTML导出完成');}else{document.getElementById('expR').textContent='导出失败: '+(d&&d.error);}});}
function expJSON(){if(!runCtx.reportPath){ml('请先执行一批用例','w');return;}apiPost('/api/report/export/json',{batch_report:runCtx.reportPath},function(d){if(d&&d.success){document.getElementById('expR').innerHTML='<a style="color:#4CAF50;" href="'+(d.download||'')+'" target="_blank">下载JSON</a>';ml('JSON导出完成');}else{document.getElementById('expR').textContent='导出失败: '+(d&&d.error);}});}
function expFail(){if(!runCtx.reportPath){ml('请先执行一批用例','w');return;}apiPost('/api/report/export/fail_package',{batch_report:runCtx.reportPath},function(d){if(d&&d.success){document.getElementById('expR').innerHTML='<a style="color:#4CAF50;" href="'+(d.download||'')+'" target="_blank">下载失败包</a>';ml('失败包导出完成');}else{document.getElementById('expR').textContent='导出失败: '+(d&&d.error);}});}

// ===== API调试 =====
function callAPI(){var sel=document.getElementById('apiSel').value;var urls={'status':'/api/status','capture':'/api/capture','metadata':'/api/metadata','drafts':'/api/mapping/drafts','ui_import_report':'/api/ui/import/report','ui_scan':'/api/ui_scan?kind=current'};var url=urls[sel]||'/api/status';fetch(url).then(function(r){return r.json()}).then(function(d){document.getElementById('apiR').innerHTML=JSON.stringify(d,null,2).replace(/\n/g,'<br>').slice(0,2000);ml('API: '+url);});}

// ===== 预检 =====
function syncPrecheckBlockersToPanel(checks){
  var list=(checks||[]).filter(function(c){return c&&c.blocker;});
  var blkEl=document.getElementById('blkR');
  var infoEl=document.getElementById('blkInfo');
  if(!blkEl||!infoEl)return;
  precheckBlockerCache=list.slice(0);
  if(!list.length){
    blkEl.innerHTML='无阻塞项';
    infoEl.textContent='无阻塞';
    infoEl.style.color='#4CAF50';
    return;
  }
  var h='<table class="st"><tr style="background:#f5f5f5;"><td>检查项</td><td>状态</td><td>详情</td><td>建议动作</td><td>复制</td></tr>';
  list.forEach(function(c){
    var i=list.indexOf(c);
    var d='';
    if(typeof c.detail==='string'){d=c.detail;}
    else if(c.detail&&typeof c.detail==='object'){for(var k in c.detail){if(!Object.prototype.hasOwnProperty.call(c.detail,k)||c.detail[k]===undefined||c.detail[k]===null)continue;if(typeof c.detail[k]==='string'&&c.detail[k].length>0)d+=(d?'; ':'')+k+': '+c.detail[k];}}
    if(!d)d='-';
    var acts='-';
    if(Array.isArray(c.quickFix)&&c.quickFix.length){
      acts=c.quickFix.map(function(a){return a&&a.label?a.label:'-';}).join('；');
    }
    h+='<tr><td>'+(c.name||'')+'</td><td style="color:#f44336;">阻塞</td><td style="max-width:180px;word-break:break-all;">'+d+'</td><td style="max-width:160px;word-break:break-all;">'+acts+'</td><td><button class="btn btn-sm" style="background:#2196F3;color:#fff;" onclick="copyPrecheckBlockerDetail('+i+')">复制</button></td></tr>';
  });
  h+='</table>';
  blkEl.innerHTML=h;
  infoEl.textContent='阻塞 '+list.length+' 项';
  infoEl.style.color='#f44336';
  ml('阻塞处理页签已同步'+list.length+'个阻塞项');
}
function copyPrecheckBlockerDetail(idx){
  var item=precheckBlockerCache[idx];
  if(!item){ml('未找到对应阻塞项','w');return;}
  var msg=(item.detail&&typeof item.detail==='string')?item.detail:JSON.stringify(item.detail||{},null,2);
  if(navigator.clipboard&&navigator.clipboard.writeText){
    navigator.clipboard.writeText(msg).then(function(){ml('阻塞项详情已复制');}).catch(function(){ml('复制失败，请手动截图','e');});
    return;
  }
  var textarea=document.createElement('textarea');
  textarea.value=msg;
  textarea.style.position='fixed';
  textarea.style.opacity='0';
  document.body.appendChild(textarea);
  textarea.select();
  try{document.execCommand('copy');ml('阻塞项详情已复制');}catch(e){ml('复制失败，请手动记录','e');}
  document.body.removeChild(textarea);
}
function rerunPrecheckBlocks(){preCheck(function(){var c=(precheckState&&precheckState.checks)||[];var list=(c||[]).filter(function(x){return x&&x.blocker;});if(!list.length){ml('当前无阻塞项','i');return;}ml('阻塞重检完成: '+list.length+'项仍阻塞');});}
function preCheck(cb){apiGet('/api/precheck',function(d){precheckState=d||{};precheckState.lastCheckedAt=Date.now();var checks=precheckState.checks||[];var h='<table class="st"><tr style="background:#f5f5f5;"><td>检查项</td><td>状态</td><td>类型</td><td>详情</td></tr>';var blockers=[];var actions='';var captureOk=false;var scene='';var bridgeOk=false;checks.forEach(function(c){var st=c.ok?'通过':'失败';var t=c.blocker?'阻塞':'普通';var dt='';if(c.name==='截图通道'){captureOk=!!c.ok;if(c.detail&&c.detail.scene){scene=c.detail.scene;}}if(c.name==='日志/服务可达性'){bridgeOk=!!c.ok;if(c.detail&&(c.detail.scene||c.detail.current_scene||c.detail.currentScene)){scene=String(c.detail.scene||c.detail.current_scene||c.detail.currentScene||'');}}if(c.detail){if(typeof c.detail==='string'){dt=c.detail;}else if(c.detail.error){dt=c.detail.error;}else if(typeof c.detail==='object'){for(var k in c.detail){if(!Object.prototype.hasOwnProperty.call(c.detail,k)||c.detail[k]===undefined||c.detail[k]===null)continue;if(typeof c.detail[k]==='string'&&c.detail[k].length>0)dt+=(dt?'; ':'')+k+': '+c.detail[k];else if(typeof c.detail[k]!=='object'&&typeof c.detail[k]!=='function')dt+=(dt?'; ':'')+k+': '+String(c.detail[k]);}}}if(!dt)dt='-';h+='<tr><td style="color:#888;">'+(c.name||'')+'</td><td style="'+(c.ok?'color:#4CAF50':'color:#f44336')+'">'+st+'</td><td>'+t+'</td><td style="max-width:260px;word-break:break-all;">'+dt+'</td></tr>';if(!c.ok&&c.blocker){blockers.push((c.name||'检查项')+(c.detail&&c.detail.error?('：'+c.detail.error):''));if(Array.isArray(c.quickFix)&&c.quickFix.length){actions+='<div style="margin-bottom:3px;"><div style="font-weight:600;color:#f44336;">'+(c.name||'检查项')+'阻塞</div>';c.quickFix.forEach(function(a){if(!a||!a.action||!a.label)return;actions+='<button class="btn btn-sm" style="background:#FF9800;color:#fff;" data-action="'+escHtml(String(a.action))+'" onclick="doPrecheckQuickFix(this)">'+escHtml(a.label)+'</button> ';});actions+='</div>';}}});if(!checks.length){h='<div>无可执行检查项</div>';actions='';}document.getElementById('preChkR').innerHTML=h;document.getElementById('preChkHint').innerHTML=actions||'<span style="color:#888;">无阻塞项</span>';document.getElementById('preChkSt').textContent=precheckState.status||'未检测';document.getElementById('preChkSt').style.color=precheckState.canExecute===false?'#f44336':(checks.length?'#4CAF50':'#FF9800');var tsc=document.getElementById('tsc');if(tsc){tsc.textContent=captureOk?'可用':'待检测';tsc.className=captureOk?'ts-ok':'ts-bad';}if(scene){var tss=document.getElementById('tss');if(tss)tss.textContent=scene;}if(bridgeOk&&document.getElementById('tsu')){document.getElementById('tsu').textContent='已连接';document.getElementById('tsu').className='ts-ok';}if(blockers.length){ml('阻塞项: '+blockers.join('；'),'w');}syncPrecheckBlockersToPanel(checks);ml('预检' + (checks.length?'完成':'未检测'));if(cb){cb(precheckState);}});

function copyPrecheckResult(){
  if(!precheckState||!precheckState.checks){ml('预检结果为空','w');return;}
  var text=JSON.stringify(precheckState,null,2);
  if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(text).then(function(){ml('预检结果已复制到剪贴板');}).catch(function(){ml('复制失败，请点击下载后读取','e');});}
  else{ml('当前环境不支持剪贴板功能，请使用下载JSON','e');}
}
function downloadPrecheckResult(){
  if(!precheckState||!precheckState.checks){ml('预检结果为空','w');return;}
  var text=JSON.stringify(precheckState,null,2);var blob=new Blob([text],{type:'application/json;charset=utf-8;'});var url=URL.createObjectURL(blob);var a=document.createElement('a');a.href=url;a.download='precheck_'+new Date().toISOString().replace(/[-:T.]/g,'').slice(0,14)+'.json';document.body.appendChild(a);a.click();document.body.removeChild(a);URL.revokeObjectURL(url);ml('预检结果JSON已导出');
}

// ===== 页面关系图 =====
function viewPageGraph(){window.open('/api/page_graph/html','_blank');}
function expPageGraph(){
  fetch('/api/page_graph/html')
    .then(function(r){return r.text();})
    .then(function(html){
      var blob = new Blob([html], {type:'text/html;charset=utf-8'});
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url;
      a.download = 'page_graph_' + new Date().toISOString().replace(/[-:T.]/g,'').slice(0,14) + '.html';
      a.style.display = 'none';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      ml('页面关系图导出完成');
    })
    .catch(function(){ml('页面关系图导出失败','e');});
}

// ===== 异常历史 =====
function anoHist(){fetch('/api/anomaly/log').then(function(r){return r.json()}).then(function(d){var h='<table class="st"><tr style="background:#f5f5f5;"><td>级别</td><td>类型</td></tr>';(d.entries||[]).slice(0,10).forEach(function(e){var tp=e.level==='error'?'错误':'警告';h+='<tr><td><span class="bdg '+(e.level==='error'?'bg-r':'bg-y')+'">'+tp+'</span></td><td>'+(e.message||'').slice(0,30)+'</td></tr>';});h+='</table>';document.getElementById('anoHist').innerHTML=h;document.getElementById('anoHistCnt').textContent=(d.entries||[]).length+'条';});}

// ===== 模块验收 =====
function ldVerify(){var modules=[{n:'坐标映射',s:'✅'},{n:'Unity截图',s:'✅'},{n:'点击注入',s:'✅'},{n:'UI树导出',s:'✅'},{n:'元素映射',s:'✅'},{n:'崩溃检测',s:'✅'},{n:'阻塞处理',s:'✅'}];var h='<table class="st"><tr style="background:#f5f5f5;"><td>模块</td><td>状态</td></tr>';modules.forEach(function(m){h+='<tr><td>'+m.n+'</td><td>'+m.s+'</td></tr>';});h+='</table>';document.getElementById('verifyR').innerHTML=h;ml('验收状态已加载');}

// ===== 迁移 =====
function statusItemText(v){return v&&v.ok?'通过':'需检查';}
function statusItemColor(v){return v&&v.ok?'#4CAF50':'#FF9800';}
function statusItemDetail(v){
  if(!v||!v.detail){return '';}
  if(typeof v.detail === 'string'){return v.detail;}
  if(v.detail.error){return v.detail.error;}
  if(v.detail.response_status){return 'response_status='+v.detail.response_status;}
  if(v.detail.design_width){return 'design='+v.detail.design_width+'x'+v.detail.design_height;}
  return '';
}
function ldMigrate(){
  var out=document.getElementById('migrateR');
  if(!out){return;}
  setBusy('migrateR','检测中...');
  apiGet('/api/precheck',function(d){
    var checks=d&&d.checks?d.checks:[];
    var map={};
    checks.forEach(function(c){if(c&&c.name)map[c.name]=c;});
    var rows=[
      ['Python依赖', map['应用配置']],
      ['Unity脚本', map['Unity脚本部署']],
      ['Bridge', map['日志/服务可达性']],
      ['截图', map['截图通道']],
      ['点击', map['用例执行前置']],
    ];
    var h='<table class="st"><tr style="background:#f5f5f5;"><td>项</td><td>状态</td><td>备注</td></tr>';
    rows.forEach(function(r){
      var c=r[1];
      var text=statusItemText(c);
      var dt=statusItemDetail(c);
      h+='<tr><td>'+r[0]+'</td><td style="color:'+statusItemColor(c)+';">'+text+'</td><td style="max-width:240px;word-break:break-all;color:#777;">'+(dt||'-')+'</td></tr>';
    });
    h+='</table>';
    if(!checks.length){h='<div>预检未返回数据，已回退展示基础状态</div>';out.innerHTML=h;ml('迁移检查：预检无数据','w');}
    else {out.innerHTML=h;ml('迁移检查完成');}
  },'migrateR','迁移检查');
}

// ===== 环境初始化 =====
function envInit(){
  var el=document.getElementById('envGuide');
  if(!el){return;}
  el.textContent='初始化中...';
  el.style.color='#FF9800';
  ml('环境初始化...');
  collectCaseCtx();
  preCheck(function(d){
    var sceneFromLogin = '';
    var checks=d&&d.checks?d.checks:[];
    var blockers=[];
    (checks||[]).forEach(function(c){if(c&&c.blocker&&!c.ok){blockers.push(c.name||'检查项');}});
    if(blockers.length){
      el.textContent='初始化失败';
      el.style.color='#f44336';
      ml('环境初始化阻塞: '+blockers.join('、'),'w');
      return;
    }
    apiGet('/api/login/check',function(lg){
      if(!lg||!lg.success){el.textContent='登录状态未知';el.style.color='#FF9800';ml('登录检查异常: '+(lg&&lg.error||'未知'),'w');return;}
      sceneFromLogin = lg.scene || lg.pageId || '';
      el.textContent=lg.logged_in?'已完成':'未登录';
      el.style.color=lg.logged_in?'#4CAF50':'#f44336';
      ml('登录检查: '+(lg.logged_in?'通过':'未通过'));
    });
    apiGet('/api/status',function(s){
      if(!s){return;}
      if(!sceneFromLogin){
        sceneFromLogin = s.scene || s.pageId || '';
      }
      if(sceneFromLogin&&document.getElementById('tss')){document.getElementById('tss').textContent=sceneFromLogin;}
    });
    if(!(checks||[]).length){ml('环境初始化：未返回预检数据','w');}
  });
}

// ===== 导入用例 =====
function impCase(){var path=document.getElementById('caseFile').value;if(!path){ml('请填写Excel路径','w');return;}var ctx=collectCaseCtx();ctx.path=path;apiPost('/api/case/import',ctx,function(d){if(!d||!d.success){document.getElementById('casePreview').innerHTML='导入失败: '+(d.error||'未知');ml('导入失败','e');return;}loadCases();document.getElementById('casePreview').innerHTML='已导入: '+(d.path||path)+' | 用例数: '+(d.summary&&d.summary.total_cases||0);ml('用例导入完成');});}
function loadCases(){apiGet('/api/case/list',function(d){if(!d||!d.success){document.getElementById('casePreview').innerHTML='未导入或读取失败';document.getElementById('caseSel').innerHTML='<option value=\"\">选择用例...</option>';return;}var cases=d.cases||[];var sel=document.getElementById('caseSel');sel.innerHTML='<option value=\"\">选择用例...</option>';var arr=[];cases.forEach(function(c){sel.innerHTML+='<option value=\"'+(c.case_id||'')+'\">'+(c.case_id||'')+'（'+(c.step_count||0)+'步）</option>';arr.push((c.case_id||'')+'('+ (c.step_count||0)+'步)');});document.getElementById('casePreview').innerHTML=arr.length?'用例列表: <br>'+arr.join('<br>'):'导入后无用例';});}
function vldCase(){apiPost('/api/case/validate',collectCaseCtx(),function(d){if(!d||!d.success){document.getElementById('casePreview').innerHTML='校验失败: '+(d&&d.error||'未知');return;}document.getElementById('casePreview').innerHTML='校验结果: 合法 '+(d.summary&&d.summary.valid_count||0)+' 条，异常 '+(d.summary&&d.summary.invalid_count||0);});}

// ===== 初始化 =====
chkAll();depChk();refSt();ldDrafts();ldMaps();ldMetaSt();chkAno();
ldHist();ldVerify();anoHist();loadCases();checkLogin();loadStateDiff();loadPageGraphInfo();
document.getElementById('sbTime').textContent=new Date().toLocaleString();
setInterval(function(){document.getElementById('sbTime').textContent=new Date().toLocaleString();},60000);
})
