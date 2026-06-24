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
