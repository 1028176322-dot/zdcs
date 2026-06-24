
var _allDrafts=[];
function renderDrafts(items){
  var list=document.getElementById('rdl');
  if(!items||items.length===0){list.innerHTML='<div style="padding:10px;text-align:center;color:#ccc;">无草稿</div>';return;}
  var h='<table class="st"><tr style="background:#f5f5f5;"><td>状态</td><td>优先级</td><td>类型</td><td>名称</td><td>页面</td><td>匹配</td><td>信度</td><td>风险</td></tr>';
  items.forEach(function(it){
    var sm={'auto_draft':'待审','structure_confirmed':'结构','visual_confirmed':'视觉','click_confirmed':'点击','manual_confirmed':'确认','rejected':'拒绝','ignored':'忽略','runtime_matched':'已匹配'};
    var c=it.source==='manual_confirmed'?'bg-g':it.source==='rejected'?'bg-r':it.source==='structure_confirmed'?'style="background:#8BC34A"':it.reviewStatus==='runtime_matched'?'style="background:#5C6BC0;color:#fff;"':'bg-y';
    var pri=it.priority||'';
    var priC=pri==='P0'?'style="background:#f44336;color:#fff;"':pri==='P1'?'style="background:#FF9800;color:#fff;"':pri==='P2'?'style="background:#2196F3;color:#fff;"':pri==='P3'?'style="background:#9E9E9E;color:#fff;"':'style="background:#eee;color:#999;"';
    var et=it.elementType||'';
    var etC=et==='button'||et==='close_button'?'style="background:#E91E63;color:#fff;"':et==='tab'?'style="background:#795548;color:#fff;"':et==='interactive_icon'?'style="background:#00BCD4;color:#fff;"':et==='item_cell'||et==='reward_item'?'style="background:#607D8B;color:#fff;"':et==='clickable_unknown'?'style="background:#bbb;"':'';
    var risk=(it.risk||[]);var riskStr=risk.length?('<span style="color:#f44336;">'+risk.slice(0,2).join(',')+'</span>'):'<span style="color:#888;">-</span>';
    var pg=it.pageId||'';var pgShort=pg.length>12?pg.slice(0,12)+'..':pg;
    // 匹配状态
    var rm=it.runtimeMatch||{};var rmStr='<span style="color:#888;">-</span>';var rmTitle='';
    if(rm.status==='matched'||it.reviewStatus==='runtime_matched'){rmStr='<span style="color:#5C6BC0;">已匹配</span>';rmTitle='分数:'+(rm.matchScore||'');}
    else if(rm.status==='not_matched'){rmStr='<span style="color:#f44336;">未匹配</span>';rmTitle=(rm.reason||'');}
    else if(it.reviewStatus==='visual_confirmed'){rmStr='<span style="color:#4CAF50;">视觉确认</span>';rmTitle='';}
    else if(it.reviewStatus==='click_confirmed'){rmStr='<span style="color:#f44336;">点击确认</span>';rmTitle='';}
    var cv=it.clickVerification||{};if(cv.status==='passed'){rmStr='<span style="color:#f44336;">已验证</span>';rmTitle='';}
    var rmAttr=rmTitle?' title="'+rmTitle+'"':'';
    // 排除原因列
    var excl=it.excludeReason||'';
    var exclStr=excl?'<span style="color:#ff4444;">'+excl+'</span>':'';
    h+='<tr onclick="shDraft(\''+(it.path||'').replace(/'/g,'')+'\')" style="cursor:pointer;">';
    h+='<td><span class="bdg" '+c+'>'+(sm[it.reviewStatus||it.source]||it.source||'')+'</span></td>';
    h+='<td>'+(pri?'<span class="bdg" '+priC+'>'+pri+'</span>':'<span style="color:#ccc;">-</span>')+'</td>';
    h+='<td>'+(et?'<span class="bdg" '+etC+'>'+et+'</span>':'<span style="color:#ccc;">-</span>')+'</td>';
    h+='<td>'+(it.displayName||it.name||'?')+'</td>';
    h+='<td style="font-size:9px;color:#666;">'+(pgShort||'-')+'</td>';
    h+='<td style="font-size:9px;"'+rmAttr+'>'+rmStr+'</td>';
    h+='<td style="font-size:9px;">'+exclStr+'</td>';
    h+='<td>'+(it.confidence||0)+'</td>';
    h+='<td style="font-size:9px;">'+riskStr+'</td></tr>';
  });h+='</table>';list.innerHTML=h;
  document.getElementById('rStats').textContent=items.length+'条';
}
function quickFilter(t){
  var kw=document.getElementById('rkw').value;
  var st=document.getElementById('rst').value;
  var url='/api/mapping/drafts?limit=1000&keyword='+encodeURIComponent(kw);
  if(st)url+='&status='+encodeURIComponent(st);
  fetch(url).then(function(r){return r.json()}).then(function(d){
    var all=d.drafts||[];
    var items=[];
    if(t==='high'){items=all.filter(function(it){return it.confidence>=85;});}
    else if(t==='matched'){items=all.filter(function(it){return it.reviewStatus==='runtime_matched'||(it.runtimeMatch&&it.runtimeMatch.status==='matched');});}
    else if(t==='page_matched'){items=all.filter(function(it){return (it.runtimeMatch&&it.runtimeMatch.status==='matched')||it.reviewStatus==='runtime_matched';});}
    else if(t==='nodesc'){items=all.filter(function(it){return !it.chineseDescription;});}
    else if(t==='noclick'){items=all.filter(function(it){return it.clickable&&!it.clickTargetNode;});}
    else if(t==='p0'){items=all.filter(function(it){return it.priority==='P0';});}
    else if(t==='p1'){items=all.filter(function(it){return it.priority==='P1';});}
    else if(t==='p2'){items=all.filter(function(it){return it.priority==='P2';});}
    else if(t==='p3'){items=all.filter(function(it){return it.priority==='P3';});}
    else if(t==='btn'){items=all.filter(function(it){return it.elementType==='button'||it.elementType==='close_button';});}
    else if(t==='icon'){items=all.filter(function(it){return it.elementType==='interactive_icon'||it.elementType==='display_icon';});}
    else if(t==='tab'){items=all.filter(function(it){return it.elementType==='tab';});}
    else if(t==='item_cell'){items=all.filter(function(it){return it.elementType==='item_cell'||it.elementType==='reward_item';});}
    else if(t==='debug'){items=all.filter(function(it){var risk=it.risk||[];return risk.indexOf('missing_script')>=0||(it.priority==='LOW');});}
    else if(t==='no_page'){items=all.filter(function(it){return !it.pageId||it.pageId==='unknown';});}
    else if(t==='interactive_icon'){items=all.filter(function(it){return it.elementType==='interactive_icon';});}
    else if(t==='item_cell'){items=all.filter(function(it){return it.elementType==='item_cell'||it.elementType==='reward_cell'||it.elementType==='shop_item_cell';});}
    else if(t==='popup_mask'){items=all.filter(function(it){return it.elementType==='popup_mask'||it.elementType==='blank_close_area';});}
    else if(t==='scroll_area'){items=all.filter(function(it){return it.elementType==='scroll_area';});}
    else if(t==='drag_area'){items=all.filter(function(it){return it.elementType==='drag_area';});}
    else if(t==='debug_ui'){items=all.filter(function(it){return it.excludeReason==='debug_ui'||it.elementType==='debug_ui'||it.allowRuntimeMatch===false;});}
    renderDrafts(items);
  });
}
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
  el.style.display='block';
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
    var manualImportBtn = document.getElementById('metaImportBtn');
    if (manualImportBtn) {
      manualImportBtn.onclick = null;
      manualImportBtn.addEventListener('click', function(ev){
        if (ev) { ev.preventDefault(); }
        importUiByFile();
      });
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
  } else if (t.id === 'metaImportBtn') {
    ev.preventDefault();
    importUiByFile();
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
function _setPrepareStepText(text, kind){
  var target = document.getElementById('prepareSummary');
  if (!target) return;
  var v = (typeof text === 'undefined' || text === null) ? '-' : text;
  target.innerHTML = kind === 'fail'
    ? '<span style="color:#f44336;">' + v + '</span>'
    : kind === 'ok'
    ? '<span style="color:#4CAF50;">' + v + '</span>'
    : kind === 'warn'
    ? '<span style="color:#FF9800;">' + v + '</span>'
    : String(v);
}
function _setPrepareButtonsDisabled(disabled){
  ['prepareInitBtn','prepareSyncProjectBtn','prepareSyncCurrentBtn','prepareReviewBtn','prepareRunAllBtn'].forEach(function(id){
    var el = document.getElementById(id);
    if (el) { el.disabled = !!disabled; }
  });
}
function prepareRefreshSummary(){
  setBusy('prepareSummary', '加载准备状态...');
  apiGet('/api/prepare/summary', function(d){
    if (!d || d.success === false){
      _setPrepareStepText('状态获取失败: ' + ((d && d.error) || '未知错误'), 'fail');
      return;
    }
    var env = d.environment || {};
    var imp = d.import || {};
    var sem = d.uiCodeSemantics || {};
    var st = [
      '项目: ' + (env.unityProject ? '已配置' : '未配置'),
      '配置: ' + (env.autosmokeRoot || '-'),
      '规则: ' + (d.prepared && d.prepared.rules ? '已就绪' : '未检查'),
      '语义索引: ' + (d.prepared && d.prepared.uiCodeSemantics ? '已生成' : '未生成'),
      '索引文件: ' + (sem.path || '未生成')
    ];
    _setPrepareStepText('准备流水线状态：' + st.join(' | '));
    var detail = document.getElementById('prepareDetail');
    if (detail){
      detail.innerHTML =
        'runtime: scene=' + ((d.runtime && d.runtime.scene) || '-') + ' | nodes=' + ((d.runtime && d.runtime.nodeCount) || 0) + '<br>' +
        '语义: nodes=' + ((sem.stats && sem.stats.totalElements) || 0) + '，页面=' + ((sem.stats && sem.stats.totalPages) || 0) + '，生成于=' + (sem.generatedAt || '-') + '<br>' +
        '导入: 成功=' + (imp.success === true ? '是' : '否') + '，总节点=' + (imp.nodeCount || imp.totalNodes || 0) + '，待审=' + (imp.pending || '-');
    }
    if (d.prepared && d.prepared.uiCodeSemantics && d.prepared.rules){
      document.getElementById('prepareBuildBtn') && (document.getElementById('prepareBuildBtn').disabled = false);
      document.getElementById('prepareRunAllBtn') && (document.getElementById('prepareRunAllBtn').disabled = false);
    }
  }, 'prepareSummary', '准备流水线状态');
}
function prepareInitEnvironment(){
  var ctx = collectCaseCtx();
  _setPrepareButtonsDisabled(true);
  _setPrepareStepText('执行中：初始化环境', 'warn');
  apiPost('/api/prepare/init_environment', {projectPath: ctx.unityProject || ''}, function(d){
    if (!d || d.success !== true){
      _setPrepareStepText('初始化环境失败: ' + ((d && d.error) || '未知错误'), 'fail');
      _setPrepareButtonsDisabled(false);
      return;
    }
    _setPrepareStepText('初始化环境完成：pid ' + (d.runtime && d.runtime.pid ? d.runtime.pid : ''), 'ok');
    prepareRefreshSummary();
    _setPrepareButtonsDisabled(false);
  }, 'prepareSummary', '准备环境');
}
function prepareSyncProjectData(){
  var dir = (document.getElementById('metaImportDir') && document.getElementById('metaImportDir').value) ? document.getElementById('metaImportDir').value.trim() : '';
  var ctx = collectCaseCtx();
  _setPrepareButtonsDisabled(true);
  _setPrepareStepText('执行中：同步项目数据', 'warn');
  apiPost('/api/prepare/sync_project_data', {projectPath: ctx.unityProject || '', sourceDir: dir}, function(d){
    if (!d || d.success !== true){
      _setPrepareStepText('同步项目数据失败: ' + ((d && d.error) || '未知错误'), 'fail');
      _setPrepareButtonsDisabled(false);
      return;
    }
    var s = d.summary || {};
    _setPrepareStepText('同步项目数据完成：' + (s.nodeCount || 0) + '节点，' + (s.totalDrafts || 0) + '草稿', 'ok');
    prepareRefreshSummary();
    // 自动触发语义索引构建（后台执行）
    apiPost('/api/prepare/build_code_semantics', {}, function(sd){
      _setPrepareStepText('项目已同步，语义索引已更新', 'ok');
      _setPrepareButtonsDisabled(false);
    }, 'prepareSummary', '同步项目');
  }, 'prepareSummary', '同步项目');
}
function prepareSyncCurrentPageData(){
  _setPrepareButtonsDisabled(true);
  _setPrepareStepText('执行中：同步当前页面', 'warn');
  apiPost('/api/prepare/sync_current_page', {}, function(d){
    if (!d || d.success !== true){
      _setPrepareStepText('同步当前页面失败: ' + ((d && d.error) || '未知错误'), 'fail');
      _setPrepareButtonsDisabled(false);
      return;
    }
    var match = (d.match || {});
    var s = (d.summary || {});
    var ctx = (d.context || {});
    _setPrepareStepText('同步当前页面完成：page=' + (ctx.normalizedPageId || (d.runtime ? (d.runtime.pageId || '-') : '-')) + '，已匹配=' + ((match.runtimeMatched || match.matched || 0) + '/' + (match.totalCandidates || s.totalCandidates || 0)), 'ok');
    ldDrafts();
    prepareRefreshSummary();
    if (d.capture && d.capture.path) {
      document.getElementById('capSrc').textContent = '已采集 (' + (d.capture.mode || 'unity') + ')';
      document.getElementById('capSrcSt').textContent = '已更新';
    }
    _setPrepareButtonsDisabled(false);
  }, 'prepareSummary', '同步当前页');
}
function prepareBuildCodeSemantics(){
  var ctx = collectCaseCtx();
  _setPrepareButtonsDisabled(true);
  _setPrepareStepText('执行中：构建语义索引', 'warn');
  apiPost('/api/prepare/build_code_semantics', {projectRoot: ctx.unityProject || ''}, function(d){
    if (!d || d.success !== true){
      _setPrepareStepText('构建语义索引失败: ' + ((d && d.error) || '未知错误'), 'fail');
      _setPrepareButtonsDisabled(false);
      return;
    }
    _setPrepareStepText('构建语义索引完成：' + (d.path || '已生成'), 'ok');
    if (document.getElementById('prepareDetail')) {
      document.getElementById('prepareDetail').innerHTML += '<br>语义文件: ' + (d.path || '-');
    }
    var sem = (d.summary || {});
    _setPrepareStepText((document.getElementById('prepareSummary').textContent || '') + '<br>总页数=' + (sem.pageCount || 0) + '，控件=' + (sem.elementCount || 0), 'ok');
    prepareRefreshSummary();
    _setPrepareButtonsDisabled(false);
  }, 'prepareSummary', '语义索引');
}
function prepareRunAll(){
  var btn = document.getElementById('prepareRunAllBtn');
  if (btn) { btn.textContent = '执行中...'; btn.disabled = true; }
  _setPrepareStepText('执行中：准备流水线', 'warn');
  var ctx = collectCaseCtx();
  apiPost('/api/prepare/init_environment', {projectPath: ctx.unityProject || ''}, function(d1){
    if(!d1 || d1.success !== true){
      _setPrepareStepText('一键执行失败：初始化环境失败', 'fail');
      if (btn) { btn.textContent='一键执行'; btn.disabled=false; }
      return;
    }
  apiPost('/api/prepare/sync_project_data', {projectPath: ctx.unityProject || ''}, function(d2){
      if(!d2 || d2.success !== true){
        _setPrepareStepText('一键执行失败：同步项目失败', 'fail');
        if (btn) { btn.textContent='一键执行'; btn.disabled=false; }
        return;
      }
      apiPost('/api/prepare/sync_current_page', {}, function(d3){
        if(!d3 || d3.success !== true){
          _setPrepareStepText('一键执行失败：同步当前页失败', 'fail');
          if (btn) { btn.textContent='一键执行'; btn.disabled=false; }
          return;
        }
        apiPost('/api/prepare/build_code_semantics', {projectRoot: ctx.unityProject || ''}, function(d4){
          if(!d4 || d4.success !== true){
            _setPrepareStepText('一键执行失败：语义索引失败', 'fail');
            if (btn) { btn.textContent='一键执行'; btn.disabled=false; }
            return;
          }
          _setPrepareStepText('一键执行完成', 'ok');
          if (btn) { btn.textContent='一键执行'; btn.disabled=false; }
          prepareRefreshSummary();
          ldDrafts();
        }, 'prepareSummary', '一键执行');
      }, 'prepareSummary', '一键执行');
    }, 'prepareSummary', '一键执行');
  }, 'prepareSummary', '一键执行');
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
function cap(){
  var btn=document.querySelector('button[onclick*="cap()"]');
  if(btn){btn.textContent='截图...';btn.disabled=true;}
  return fetch('/api/capture').then(function(r){return r.json()}).then(function(d){
    if(btn){btn.textContent='测试截图';btn.disabled=false;}
    if(d.game_content_path){
      document.getElementById('monitorImg').src='/api/screenshot/'+encodeURIComponent(d.game_content_path)+'?t='+Date.now();
      document.getElementById('monitorImg').style.display='block';
      document.getElementById('noMonitorImg').style.display='none';
      var b=document.getElementById('capBdg');
      if(b){b.textContent=d.capture_mode==='unity'?'Unity':'Python';b.className='bdg '+(d.capture_mode==='unity'?'bg-b':'bg-y');}
      ml('截图完成: '+(d.capture_mode||''));
      return d.game_content_path;
    }else{
      ml('截图失败: 未返回截图路径','e');
      return null;
    }
  }).catch(function(e){
    if(btn){btn.textContent='测试截图';btn.disabled=false;}
    ml('截图请求失败: '+e,'e');
    return null;
  });
}

// ===== 点击/步骤 =====
function tClick(){ml('测试点击...');fetch('/api/click_test',{method:'POST'}).then(function(r){return r.json()}).then(function(d){document.getElementById('clickR').innerHTML='结果: '+(d.result||'?')+' | 差异: '+(d.diff_ratio||0);ml('点击: '+(d.result||'?'));}).catch(function(e){ml('点击失败','e');});}
function exStep(){var t=document.getElementById('stepInp').value.trim();if(!t)return;ml('执行: '+t);fetch('/api/execute',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:t})}).then(function(r){return r.json()}).then(function(d){var r2=d.step_result||d;document.getElementById('stepR').innerHTML=JSON.stringify(r2,null,2).replace(/\n/g,'<br>');ml('结果: '+r2.result);}).catch(function(e){ml('执行失败','e');});}

// ===== 部署 =====
function depChk(){fetch('/api/deploy_check').then(function(r){return r.json()}).then(function(d){document.getElementById('hGrid').innerHTML='<span style="color:#4CAF50;">脚本: '+(d.deployed?'已部署':'待部署')+' | '+(d.count||0)+'个</span>';});}
function depRun(){
  var btn=document.querySelector('button[onclick*=\"depRun\"]');
  if(btn){btn.textContent='部署中...';btn.disabled=true;}
  var grid=document.getElementById('hGrid');
  if(grid)grid.innerHTML='<span style=\"color:#FF9800;\">部署中...</span>';
  fetch('/api/deploy_run',{method:'POST'}).then(function(r){return r.json()}).then(function(d){
    if(btn){btn.textContent='部署脚本';btn.disabled=false;}
    if(d.success){
      if(grid)grid.innerHTML='<span style=\"color:#4CAF50;\">✔ 部署成功 | '+(d.count||0)+'个</span>';
      ml('部署成功: '+(d.count||0)+'个脚本');
      depChk();
    }else{
      if(grid)grid.innerHTML='<span style=\"color:#f44336;\">✖ '+(d.message||d.error||'失败')+'</span>';
      ml('部署失败: '+(d.message||d.error||'未知'),'e');
    }
  }).catch(function(e){
    if(btn){btn.textContent='部署脚本';btn.disabled=false;}
    if(grid)grid.innerHTML='<span style=\"color:#f44336;\">请求失败</span>';
    ml('部署请求失败','e');
  });
}

// ===== 阻塞 =====
function detBlk(){fetch('/api/blocker_detect').then(function(r){return r.json()}).then(function(d){document.getElementById('blkR').innerHTML=JSON.stringify(d,null,2).replace(/\n/g,'<br>');ml('阻塞检测完成');});}
function resBlk(){fetch('/api/blocker_resolve',{method:'POST'}).then(function(r){return r.json()}).then(function(d){document.getElementById('blkR').innerHTML=JSON.stringify(d,null,2).replace(/\n/g,'<br>');ml('阻塞处理完成');});}

// ===== 元数据 =====
function ldMetaSt(){fetch('/api/metadata').then(function(r){return r.json()}).then(function(d){document.getElementById('metaSt').innerHTML=JSON.stringify(d,null,2).replace(/\n/g,'<br>');});}
function scAcc(){fetch('/api/accessibility/scan').then(function(r){return r.json()}).then(function(d){document.getElementById('accR').innerHTML=JSON.stringify(d,null,2).replace(/\n/g,'<br>');ml('可测性扫描完成');});}
function ldMaps(){fetch('/api/mapping/list?summary=1&limit=50').then(function(r){return r.json()}).then(function(d){var items=d.mappings||[];var h='<table class="st"><tr style="background:#f5f5f5;"><td>名</td><td>testId</td><td>角色</td></tr>';items.forEach(function(m){h+='<tr><td>'+(m.displayName||m.name||'')+'</td><td>'+(m.testId||'')+'</td><td>'+(m.role||'')+'</td></tr>';});h+='</table>';document.getElementById('mapL').innerHTML=h;document.getElementById('mapStats').textContent=(d.total||items.length)+'条';});}

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
  var url = '/api/mapping/drafts?limit=300&keyword='+encodeURIComponent(kw);
  if(stt)url+='&status='+encodeURIComponent(stt);
  fetch(url).then(function(r){return r.json()}).then(function(d){
    var list = document.getElementById('rdl');
    var total=d.total||0;
    var shown=(d.drafts||[]).length;
    document.getElementById('rStats').textContent=(shown<total?('展示 '+shown+'/'+total+' 条'):(total+'条'));
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
    // 字段配置（全局，供 shDraft 和 svD 共用）
    var FIELD_DEFS=[
      {key:'path',label:'节点路径',group:'基础信息',editable:false,help:'当前元素在候选库中的唯一标识',example:'MainPanel/Canvas/btn_use'},
      {key:'displayName',label:'显示名称',group:'基础信息',editable:true,required:true,help:'给测试人员看的中文名称，审核列表和报告中优先显示',example:'背包-使用按钮'},
      {key:'chineseDescription',label:'中文描述',group:'基础信息',editable:true,help:'解释元素在游戏中的作用',example:'背包界面底部的使用按钮'},
      {key:'text',label:'显示文本',group:'基础信息',editable:false,help:'Unity 节点上真实显示的文字',example:'使用、确定'},
      {key:'nodeName',label:'节点名',group:'基础信息',editable:false,help:'Unity GameObject 名称',example:'btn_use'},
      {key:'components',label:'组件',group:'基础信息',editable:false,help:'Unity 节点挂载的组件列表',example:'Button, Image, Text'},
    {key:'testId',label:'用例ID',group:'语义标识',editable:true,help:'用例步骤可直接引用的稳定 ID',example:'bag.btn_use'},
    {key:'suggestedTestId',label:'推荐用例ID',group:'语义标识',editable:false,help:'IDE 自动根据页面、节点名、文本生成的建议值'},
    {key:'semanticId',label:'语义ID',group:'语义标识',editable:true,help:'偏向业务语义的标识',example:'bag.use'},
    {key:'suggestedSemanticId',label:'推荐语义ID',group:'语义标识',editable:false,help:'IDE 自动生成的语义 ID 建议'},
    {key:'codeHandler',label:'绑定函数',group:'语义标识',editable:false,help:'代码事件回调函数名',example:'OnClickUse'},
    {key:'actionType',label:'功能动作',group:'语义标识',editable:false,help:'方案中定义的动作语义',example:'use_item'},
    {key:'businessAction',label:'业务动作',group:'语义标识',editable:false,help:'动作语义细节描述',example:'use_selected_bag_item'},
    {key:'expectedResult',label:'预期结果',group:'语义标识',editable:false,help:'点击后系统预期响应',example:'打开使用确认弹窗'},
    {key:'requiresState',label:'前置条件',group:'语义标识',editable:false,help:'触发动作前需满足条件',example:'selectedBagItem'},
    {key:'pageId',label:'所属页面',group:'页面与类型',editable:true,required:true,help:'元素所在页面，决定当前页匹配是否能找到它',example:'BagPanel'},
      {key:'elementType',label:'元素类型',group:'页面与类型',editable:true,required:true,help:'元素分类：按钮/图标/格子/场景对象等',example:'button'},
      {key:'interactionType',label:'交互方式',group:'页面与类型',editable:true,required:true,help:'自动化怎么操作：click/drag/scroll/blank_close',example:'click'},
      {key:'role',label:'角色',group:'页面与类型',editable:true,help:'业务角色',example:'use_action'},
      {key:'priority',label:'优先级',group:'页面与类型',editable:true,help:'审核优先级：P0/P1/P2/LOW',example:'P0'},
      {key:'clickTargetNode',label:'点击目标',group:'点击定位',editable:true,required:true,help:'真正接收点击事件的节点。自动点击优先点此，错了会点错',example:'BagPanel/List/Item_001'},
      {key:'visualNode',label:'视觉节点',group:'点击定位',editable:true,help:'用户在界面上看到的节点。错了高亮会框错',example:'BagPanel/List/Item_001/Icon'},
      {key:'runtimePath',label:'运行态路径',group:'点击定位',editable:false,help:'Unity 当前运行时真实路径（从运行态匹配获得）'},
      {key:'prefabPath',label:'Prefab路径',group:'点击定位',editable:false,help:'prefab 文件路径'},
      {key:'prefabNodePath',label:'Prefab节点路径',group:'点击定位',editable:false,help:'prefab 内部节点路径'},
      {key:'screenRect',label:'屏幕区域',group:'点击定位',editable:false,help:'元素在截图上的区域'},
      {key:'reviewHint',label:'审核提示',group:'风险与建议',editable:true,help:'IDE 给审核人员的建议'},
      {key:'risk',label:'风险列表',group:'风险与建议',editable:false,help:'IDE 自动识别出的风险'},
      {key:'clickableReason',label:'可点击原因',group:'风险与建议',editable:false,help:'为什么认为该元素可点击'},
      {key:'effectiveClickable',label:'当前有效',group:'风险与建议',editable:false,help:'当前是否真正可交互'},
      {key:'dataSource',label:'数据源',group:'原始来源',editable:false,help:'元素来源：enhanced/project/runtime'},
      {key:'spriteName',label:'Sprite命名',group:'原始来源',editable:false,help:'Unity 图片资源名称'},
      {key:'atlasName',label:'图集',group:'原始来源',editable:false,help:'Unity 图集名称'},
    ];

function shDraft(p){
  rp=p;if(!p){document.getElementById('rDet').innerHTML='<span style=\"color:#ccc;\">选择草稿</span>';return;}
  fetch('/api/mapping/get?path='+encodeURIComponent(p)).then(function(r){return r.json()}).then(function(d){
    var data=d.mapping||{};
    var cs=data.codeSemantic||{};
    data.codeHandler = data.codeHandler || cs.handler || '';
    data.actionType = data.actionType || cs.actionType || '';
    data.businessAction = data.businessAction || cs.businessAction || '';
    data.expectedResult = data.expectedResult || cs.expectedResult || [];
    data.requiresState = data.requiresState || cs.requiresState || [];
    data.confidence = data.confidence || cs.confidence || 0;
    var st=data.reviewStatus||data.source||'pending';
    var c=_draftStatusClass(st);var badge=_draftStatusText(st);
    var rm=data.runtimeMatch||{};var cv=data.clickVerification||{};
    var hasRuntimeMatch=rm.status==='matched'||data.reviewStatus==='runtime_matched';
    // 判断是否有可显示的矩形区域
    function _hasRect(rect){if(!rect)return false;if(Array.isArray(rect))return rect.length>=4;if(typeof rect==='object')return (rect.width>0&&rect.height>0);return false;}
    var hasRuntimeRect=_hasRect(rm.screenRect)||_hasRect(data.screenRect);
    var hasScreenshot=!!((data.screenshotRef&&String(data.screenshotRef).trim())||data.hasScreenshot||data.highlightImage);
    var canHighlight=hasRuntimeMatch&&hasRuntimeRect;
    var canVisualConfirm=canHighlight&&hasScreenshot;
    // 确定显示模式
    var mode='structure';var modeMsg='';
    if(!hasRuntimeMatch){mode='structure';modeMsg='该元素尚未匹配到 Unity 当前实时界面<br>请先“刷新运行态UI树”并执行“匹配当前页”';}
    else if(hasRuntimeMatch&&!hasRuntimeRect){mode='runtime_no_rect';modeMsg='运行态已匹配，但缺少 screenRect<br>可先测试点击，或重新导出运行态 UI 树';}
    else if(hasRuntimeMatch&&hasRuntimeRect&&!hasScreenshot){mode='runtime_need_screenshot';modeMsg='运行态已匹配，已有 screenRect<br>请刷新截图或点击生成高亮';}
    else if(hasRuntimeMatch&&hasRuntimeRect){mode='visual';modeMsg='运行态已匹配，截图高亮可查看<br>请确认红框是否框住正确目标';}
    if(cv.status==='passed'){mode='clicked';modeMsg='点击已确认<br>该元素可进入正式自动点击';}
    var csLine='';
    if(cs.status||cs.handler||cs.actionType||cs.businessAction){
      csLine='<div style="margin:2px 0;padding:3px;background:#E8F5E9;border-radius:3px;font-size:10px;"><b>代码语义</b>：'+(cs.handler||'-')+' / '+(cs.actionType||'unknown')+' / '+(cs.businessAction||'unknown')+'<br>'+'可见置信度:'+((typeof cs.confidence!=='undefined' && cs.confidence!==null)?cs.confidence:0)+'</div>';
    }
    // 构建详情
    var ds=data.dataSource||'';var pri=data.priority||'';var et=data.elementType||'';
    var h='<div style=\"margin-bottom:3px;\"><span class=\"bdg '+c+'\">'+badge+'</span>'+(pri?' <span class=\"bdg\" style=\"background:'+(pri==='P0'?'#f44336':pri==='P1'?'#FF9800':pri==='P2'?'#2196F3':'#9E9E9E')+';color:#fff;\">'+pri+'</span>':'')+(et?' <span class=\"bdg\" style=\"background:#00BCD4;color:#fff;\">'+et+'</span>':'')+(ds?' <span style=\"font-size:9px;color:#888;\">'+ds+'</span>':'')+'</div>' + csLine;
    // 审核状态 + 下一步建议
    var nextStep='';
    var statusDescs={'pending':'自动生成的候选，尚未经过人工确认','auto_draft':'待审核','structure_confirmed':'仅路径/名称判断，未实时匹配','runtime_matched':'已在 Unity 实时 UI 树中匹配到','visual_confirmed':'截图高亮已人工确认正确','click_confirmed':'Unity 注入点击验证通过','modified':'人工修改过字段，需重新确认','rejected':'已确认该草稿错误','ignored':'确认不参与自动化'};
    var nextSteps={'pending':'进行结构确认或运行态匹配','auto_draft':'进行结构确认或运行态匹配','structure_confirmed':'刷新运行态UI树进行匹配','runtime_matched':'生成高亮图并进行视觉确认','visual_confirmed':'进行点击确认测试','click_confirmed':'可加入正式自动点击','modified':'重新确认修改后的字段','rejected':'无','ignored':'无'};
    h+='<div style=\"margin:2px 0;padding:3px;background:#F5F5F5;border-radius:3px;font-size:9px;\"><b>审核状态</b>: <span class=\"bdg '+c+'\">'+badge+'</span><br><span style=\"color:#666;\">'+(statusDescs[st]||'')+'</span><br><b>下一步:</b> '+(nextSteps[st]||'')+'</div>';
    // 分组字段渲染（使用全局 FIELD_DEFS）
    var groups={};FIELD_DEFS.forEach(function(f){if(!groups[f.group])groups[f.group]=[];groups[f.group].push(f);});
    var groupOrder=['基础信息','语义标识','页面与类型','点击定位','风险与建议','原始来源'];
    var defaultExpanded={'基础信息':true,'语义标识':false,'页面与类型':true,'点击定位':true,'风险与建议':true,'原始来源':false};
    groupOrder.forEach(function(grp){
      if(!groups[grp])return;
      var isOpen=defaultExpanded[grp];
      h+='<div style=\"margin:4px 0 0 0;\"><div onclick=\"$(this).next().toggle()\" style=\"cursor:pointer;font-size:9px;font-weight:600;color:#555;padding:1px 2px;background:#f0f0f0;border-radius:2px;\">'+(isOpen?'▼':'▶')+' '+grp+'</div><div style=\"'+(isOpen?'':'display:none;')+'padding-left:2px;\">';
      groups[grp].forEach(function(f){
        var v=data[f.key];if(v===undefined||v===null)v='';if(Array.isArray(v))v=v.join(', ');if(typeof v==='object'){try{v=JSON.stringify(v)}catch(e){v='';}}
        var ro=f.editable?'':'readonly';
        var reqMark=f.required?' <span style=\"color:#f44336;font-size:8px;\">必填</span>':'';
        h+='<div style=\"margin:1px 0;position:relative;\">';
        h+='<label style=\"font-size:9px;color:#555;\">'+f.label+reqMark+' <span style=\"color:#aaa;font-size:8px;cursor:help;\" title=\"'+(f.help||'')+'\">ⓘ</span></label>';
        h+='<input id=\"e-'+f.key+'\" value=\"'+String(v).replace(/\"/g,'&quot;').replace(/\n/g,' ')+'\" style=\"width:100%;padding:1px;font-size:10px;border:1px solid #ddd;\" '+ro+'>';
        if(f.help)h+='<div style=\"font-size:7px;color:#999;line-height:1.2;\">'+f.help+'</div>';
        h+='</div>';
      });
      h+='</div></div>';
    });
    // 运行时匹配信息
    if(hasRuntimeMatch){h+='<div style=\"margin:2px 0;padding:2px;background:#E8EAF6;border-radius:3px;font-size:10px;\"><b>运行态匹配</b>: 分数='+(rm.matchScore||'')+' 级别='+(rm.matchLevel||'')+' 路径='+(rm.runtimePath||'')+' 可见='+(rm.visible?'是':'否')+' 可交互='+(rm.interactable?'是':'否')+'</div>';}
    // 匹配冲突信息
    if(rm.conflicts&&rm.conflicts.length>0){h+='<div style=\"margin:2px 0;padding:2px;background:#FFF3CD;border-radius:3px;font-size:10px;\"><b>匹配冲突</b>: '+(rm.conflicts||[]).length+'个候选<br>';for(var ci=0;ci<rm.conflicts.length;ci++){var cf=rm.conflicts[ci];h+='&nbsp;&nbsp;• '+(cf.runtimePath||'')+' (分数:'+cf.matchScore+')<br>';}h+='</div>';}
    // 未匹配原因
    if(rm.status==='not_matched'){h+='<div style=\"margin:2px 0;padding:2px;background:#FCE4EC;border-radius:3px;font-size:10px;color:#C62828;\"><b>未匹配原因</b>: '+(rm.reason||'')+'</div>';}
    // 运行时匹配无坐标时
    if(mode==='runtime_no_rect'){h+='<div style=\"margin:2px 0;padding:3px;background:#E8EAF6;color:#5C6BC0;font-size:10px;border-radius:3px;\">'+modeMsg+'</div>';}
    // 结构审核模式
    if(mode==='structure'){h+='<div style=\"margin:2px 0;padding:3px;background:#FFF3CD;color:#9C6500;font-size:10px;border-radius:3px;\"><b>当前为结构审核模式</b><br>'+modeMsg+'</div>';}
    // 需要截图
    if(mode==='runtime_need_screenshot'){h+='<div style=\"margin:2px 0;padding:3px;background:#E3F2FD;color:#1565C0;font-size:10px;border-radius:3px;\"><b>需要截图</b><br>运行态已匹配，已有 screenRect<br><button class=\"btn btn-sm\" style=\"background:#03A9F4;color:#fff;margin-top:2px;\" onclick=\"takeAndRefreshHighlight()\">刷新截图并生成高亮</button></div>';}
    // 可视觉确认
    if(mode==='visual'){h+='<div style=\"margin:2px 0;padding:3px;background:#E8F5E9;color:#2E7D32;font-size:10px;border-radius:3px;\"><b>可视觉确认</b><br>'+modeMsg+'</div>';}
    // 点击已确认
    if(mode==='clicked'){h+='<div style=\"margin:2px 0;padding:3px;background:#FCE4EC;color:#C62828;font-size:10px;border-radius:3px;\"><b>点击已确认</b><br>'+modeMsg+'</div>';}
    // 按钮
    h+='<div style=\"margin-top:4px;display:flex;gap:2px;flex-wrap:wrap;\"><button class=\"btn btn-sm\" style=\"background:#2196F3;color:#fff;\" onclick=\"cfD(\'structure\')\">结构确认</button><button class=\"btn btn-sm\" style=\"background:#4CAF50;color:#fff;\" onclick=\"cfD(\'visual\')\" '+(canVisualConfirm?'':'disabled')+'>视觉确认</button><button class=\"btn btn-sm\" style=\"background:#7B1FA2;color:#fff;\" onclick=\"cfD(\'click\')\">点击确认</button><button class=\"btn btn-sm\" style=\"background:#5C6BC0;color:#fff;\" onclick=\"testClickDraft()\">测试点击</button><button class=\"btn btn-sm\" style=\"background:#03A9F4;color:#fff;\" onclick=\"svD()\">保存</button><button class=\"btn btn-sm\" style=\"background:#f44336;color:#fff;\" onclick=\"rjD()\">拒绝</button><button class=\"btn btn-sm\" style=\"background:#9E9E9E;color:#fff;\" onclick=\"igD()\">忽略</button></div><div id=\"rr\" style=\"margin-top:3px;font-size:10px;\"></div>';
    document.getElementById('rDet').innerHTML=h;
    // 更新预览区域
    var pre=document.getElementById('rPreview');
    if(pre){
      if(canHighlight&&hasScreenshot){
        (function(path){
          fetch('/api/mapping/highlight',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({draftPath:path})})
          .then(function(r){return r.json()}).then(function(hl){
            if(hl.success&&hl.highlightImage){
              var img=document.getElementById('rPreviewImg');
              if(img){img.src='/api/screenshot/'+encodeURIComponent(hl.highlightImage)+'?t='+Date.now();img.style.display='block';}
              var txt=document.getElementById('rPreviewText');
              if(txt)txt.style.display='none';
            }else if(hl.error==='invalid_rect'){
              var txt=document.getElementById('rPreviewText');
              if(txt)txt.innerHTML='无法生成高亮：'+(hl.reason||'坐标无效')+'<br>screenRect='+JSON.stringify(hl.screenRect)+'<br>该元素可能被误匹配，请重新匹配或忽略。';
            }else if(hl.error==='截图不存在'){
              var txt=document.getElementById('rPreviewText');
              if(txt)txt.innerHTML='无法生成高亮：截图不存在<br>请先刷新截图。';
            }else if(hl.error){
              var txt=document.getElementById('rPreviewText');
              if(txt)txt.innerHTML='无法生成高亮：'+(hl.reason||hl.error);
            }
          });
        })(p);
      }else{
        var txt=document.getElementById('rPreviewText');
        if(txt){
          var msg='选择草稿后显示详情';
          if(mode==='structure')msg=modeMsg;
          else if(mode==='runtime_no_rect')msg=modeMsg;
          else if(mode==='runtime_need_screenshot')msg='<button class=\"btn btn-sm\" style=\"background:#03A9F4;color:#fff;\" onclick=\"takeAndRefreshHighlight()\">刷新截图并生成高亮</button>';
          else if(mode==='clicked')msg='点击已确认，可查看测试截图';
          txt.innerHTML=msg;
          txt.style.display='block';
        }
        var img=document.getElementById('rPreviewImg');
        if(img)img.style.display='none';
      }
    }
    document.getElementById('rHi').textContent=(data.displayName||data.name||'')+(pri?' ['+pri+']':'')+' - 详情';
  });
}
function scD(){fetch('/api/mapping/drafts/'+encodeURIComponent(rp)+'/structure_confirm',{method:'POST'}).then(function(r){return r.json()}).then(function(d){document.getElementById('rr').innerHTML=d.success?'结构确认':'失败';if(d.success)ldDrafts();});}
function svD(){
  // 必填校验
  var required=[{k:'displayName',l:'显示名称'},{k:'pageId',l:'所属页面'},{k:'elementType',l:'元素类型'},{k:'interactionType',l:'交互方式'},{k:'clickTargetNode',l:'点击目标'}];
  var errs=[];
  required.forEach(function(f){
    var el=document.getElementById('e-'+f.k);
    if(!el||!el.value.trim())errs.push('请填写「'+f.l+'」');
  });
  if(errs.length>0){document.getElementById('rr').innerHTML='<span style=\"color:#f44336;\">'+errs.join('<br>')+'</span>';return;}
  // 保存所有可编辑字段
  var d={};['displayName','chineseDescription','testId','role','pageId','elementType','interactionType','priority','clickTargetNode','visualNode','reviewHint','semanticId'].forEach(function(k){
    var el=document.getElementById('e-'+k);if(el)d[k]=el.value;
  });
  fetch('/api/mapping/drafts/'+encodeURIComponent(rp)+'/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)})
    .then(function(r){return r.json()}).then(function(d){
      document.getElementById('rr').innerHTML=d.success?'<span style=\"color:#4CAF50;\">✅ 已保存</span>':'<span style=\"color:#f44336;\">失败</span>';
      if(d.success)ldDrafts();
    });
}
function cfD(level){var levelName=(level||'structure').toLowerCase();var p='click_confirmed';if(levelName==='structure')p='structure_confirmed';else if(levelName==='visual')p='visual_confirmed';fetch('/api/mapping/drafts/'+encodeURIComponent(rp)+'/confirm/'+p,{method:'POST'}).then(function(r){if(!r.ok){return r.json().then(function(j){throw new Error(j&&j.error?j.error:'请求失败');});}return r.json();}).then(function(d){document.getElementById('rr').innerHTML=d.success?'已标记为 '+_draftStatusText(p):'失败';if(d.success)ldDrafts();});}
function rjD(){fetch('/api/mapping/drafts/'+encodeURIComponent(rp)+'/reject',{method:'POST'}).then(function(r){return r.json()}).then(function(d){document.getElementById('rr').innerHTML=d.success?'已拒绝':'失败';if(d.success)ldDrafts();});}
function igD(){fetch('/api/mapping/drafts/'+encodeURIComponent(rp)+'/ignore',{method:'POST'}).then(function(r){return r.json()}).then(function(d){document.getElementById('rr').innerHTML=d.success?'已忽略':'失败';if(d.success)ldDrafts();});}
function takeAndRefreshHighlight(){
  if(!rp){ml('请先选择草稿','w');return;}
  cap().then(function(path){
    if(!path){ml('截图失败，无法生成高亮','e');return;}
    setTimeout(function(){
      fetch('/api/mapping/highlight',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({draftPath:rp})})
      .then(function(r){return r.json()}).then(function(hl){
        if(hl.success&&hl.highlightImage){
          var img=document.getElementById('rPreviewImg');
          if(img){img.src='/api/screenshot/'+encodeURIComponent(hl.highlightImage)+'?t='+Date.now();img.style.display='block';}
          var txt=document.getElementById('rPreviewText');
          if(txt)txt.style.display='none';
          ml('高亮已更新');
          shDraft(rp);
        }else{
          ml('高亮失败: '+(hl.error||''),'e');
        }
      });
    },500);
  });
}
function testClickDraft(){
  if(!rp){ml('请先选择草稿','w');return;}
  var rr=document.getElementById('rr');rr.innerHTML='测试点击中...';
  fetch('/api/mapping/drafts/'+encodeURIComponent(rp)+'/test_click',{method:'POST'}).then(function(r){return r.json()}).then(function(d){
    if(d.success){
      rr.innerHTML='<span style=\"color:#4CAF50;\">✔ 点击通过: '+(d.clickMethod||'')+'</span>';
      ml('测试点击通过');
      ldDrafts();
    }else{
      rr.innerHTML='<span style=\"color:red;\">✖ 点击失败: '+(d.error||(d.detail&&d.detail.clickResult)||'')+'</span>';
      ml('测试点击失败','e');
    }
  }).catch(function(e){rr.innerHTML='<span style=\"color:red;\">请求失败</span>';});
}

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
  var input = document.getElementById('metaImportFile');
  var file = (input && input.value) ? input.value.trim() : '';
  var info = document.getElementById('uiImportInfo');
  if(!file){
    if(info){
      info.style.color = '#FF9800';
      info.textContent = '请先填写手工导入路径';
      info.title = '';
    }
    setBusy('meta-status','准备中...');
    ml('请先填写手工导入路径','w');
    return;
  }
  if(info){
    info.style.color = '#2196F3';
    info.textContent = '开始手工导入: ' + file;
    info.title = file;
  }
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
    var status = document.getElementById('meta-status');
    if(status){
      status.style.display='block';
      status.innerHTML = JSON.stringify(d, null, 2).replace(/\\n/g, '<br>');
    }
    ldDrafts();
    ldMaps();
    scanUiTree();
    ml('手工导入: ' + (d && d.success ? '完成' : '失败'));
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
  var text=JSON.stringify(precheckState,null,2);var blob=new Blob([text],{type:'application/json;charset=utf-8;'});var url=URL.createObjectURL(blob);var a=document.createElement('a');a.href=url;a.download='precheck_'+new Date().toISOString().replace(/[-:T.]/g,'').slice(0,14)+'.json';document.body.appendChild(a);a.click();document.body.removeChild(a);URL.revokeObjectURL(url);  ml('预检结果JSON已导出');
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

// ===== 数据导入 =====
function scanDir(){
  var dir=document.getElementById("importDir").value;
  if(!dir)return;
  fetch("/api/mapping/list_dir",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({dir:dir})}).then(function(r){return r.json()}).then(function(d){
    var el=document.getElementById("dirContent");
    if(!d.exists){el.innerHTML="<span style=\"color:red;\">"+d.error+"</span>";return;}
    var h="<span style=\"color:#4CAF50;\">✔ 发现 "+d.files.length+" 个文件:</span> ";
    d.files.forEach(function(f){h+=f.name+" ("+f.sizeKB+"KB) ";});
    el.innerHTML=h;ml("扫描完成: "+d.files.length+" 个文件");
  }).catch(function(e){ml("扫描失败","e");});
}
var _browseDir = "";
function browseFolder(dir){
  try{
  var area=document.getElementById('browserArea');
  if(!area){alert('browserArea not found!');return;}
  if(!dir){
    if(area.style.display!='none'){area.style.display='none';return;}
    dir='E:/zdcs/AutoSmoke';
  }
  area.style.display='block';
  area.innerHTML='<div style="padding:8px;text-align:center;color:#888;">\u52a0\u8f7d\u4e2d...</div>';
  fetch('/api/mapping/list_dir',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({dir:dir})}).then(function(r){return r.json()}).then(function(d){
    if(!d.exists){area.innerHTML='<div style="padding:8px;color:red;">'+d.error+'</div>';return;}
    var html='';
    if(d.parent){html+='<div class="browse-item" onclick="browseFolder(\''+d.parent+'\')" style="padding:4px 6px;color:#888;">.. /</div>';}
    (d.dirs||[]).forEach(function(sd){html+='<div class="browse-item" onclick="browseFolder(\''+dir+'/'+sd.name+'\')" style="padding:4px 6px;">'+sd.name+'/</div>';});
    (d.files||[]).forEach(function(f){html+='<div class="browse-item" onclick="selectFile(\''+dir+'\',\''+f.name+'\')" style="padding:4px 6px;padding-left:16px;font-size:10px;color:#555;">'+f.name+' ('+f.sizeKB+'KB)</div>';});
    area.innerHTML=html;
  });
  }catch(e){console.error(e);}
}
function selectFile(dir,file){
  _browseDir=dir;
  document.getElementById("browsePath").textContent=dir+"/"+file;
  document.getElementById("browsePath").style.color="#333";
  document.getElementById("importBtn").disabled=false;
  document.getElementById("browserArea").style.display="none";
  ml("已选择: "+dir+"/"+file);
}
function doImport(){
  var dir=_browseDir||document.getElementById("browsePath").textContent;
  if(!dir||dir=="点击选择目录..."){ml("请先选择数据文件","w");return;}
  ml("导入: "+dir);
  fetch("/api/mapping/import",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({sourceDir:dir})}).then(function(r){return r.json()}).then(function(d){
    if(d.success){
      var s=d.summary||{};var el=document.getElementById("importSummary");
      el.innerHTML="<span style=\"color:#4CAF50;\">✔ 导入成功: </span>数据源:"+s.dataSource+" | 节点:"+s.totalNodes+" | 可点击:"+s.totalClickable+" | 草稿:"+s.totalDrafts+" | 待审:"+s.pending;
      ml("导入完成: "+s.totalDrafts+"草稿");
      ldDrafts();
    }else{
      document.getElementById("importSummary").innerHTML="<span style=\"color:red;\">✖ "+d.error+"</span>";
    }
  }).catch(function(e){ml("导入失败","e");});
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

// ===== enhanced_ui_tree 流程 =====
function enhanceStatus(){
  fetch('/api/ui/enhance/status').then(function(r){return r.json()}).then(function(d){
    var ok=d.success;
    var esP=document.getElementById('esProject');
    var esE=document.getElementById('esEnhanced');
    var esR=document.getElementById('esRuntime');
    var esSc=document.getElementById('esScreenshot');
    if(!ok){esP.textContent='获取失败';return;}
    esP.innerHTML=d.sourceFiles&&d.sourceFiles.project_ui_inventory?'<span style=\"color:#4CAF50;\">已发现</span>':'<span style=\"color:#FF9800;\">未发现</span>';
    if(d.exists){
      esE.innerHTML='<span style=\"color:#4CAF50;\">已生成</span> ('+(d.summary?d.summary.enhancedNodes:0)+'节点)';
      document.getElementById('enhImportBtn').disabled=false;
      document.getElementById('enhReviewBtn').disabled=false;
    }else{
      esE.innerHTML='<span style=\"color:#FF9800;\">未生成</span>';
      document.getElementById('enhImportBtn').disabled=true;
      document.getElementById('enhReviewBtn').disabled=true;
    }
    esR.innerHTML=d.sourceFiles&&d.sourceFiles.current_ui_tree?'<span style=\"color:#4CAF50;\">已发现</span>':'<span style=\"color:#888;\">缺失</span>';
    var sc=d.sourceFiles&&d.sourceFiles.pages||0;
    esSc.innerHTML=sc>0?'<span style=\"color:#4CAF50;\">'+sc+'张</span>':'<span style=\"color:#888;\">缺失</span>';
    ml('增强状态已加载');
  }).catch(function(e){ml('增强状态加载失败','e');});
}
function runEnhance(){
  var btn=document.getElementById('enhGenBtn');
  btn.disabled=true;btn.textContent='生成中...';
  var dir=document.getElementById('metaImportDir').value||'';
  fetch('/api/ui/enhance',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sourceDir:dir,mode:'project_only',overwrite:true})}).then(function(r){return r.json()}).then(function(d){
    btn.disabled=false;btn.textContent='生成增强UI树';
    var el=document.getElementById('enhanceResult');
    if(d.success){
      var s=d.summary||{};
      el.innerHTML='<span style=\"color:#4CAF50;\">✔ 增强完成: </span>'+
        '原始节点 '+s.projectNodes+' | '+
        '增强候选 <b>'+s.enhancedNodes+'</b> | '+
        'P0 <b style=\"color:#f44336;\">'+s.p0+'</b> | '+
        'P1 <b>'+s.p1+'</b> | '+
        'P2 '+s.p2+' | '+
        'P3 '+s.p3;
      document.getElementById('enhImportBtn').disabled=false;
      ml('增强完成: '+s.enhancedNodes+'节点');
      enhanceStatus();
    }else{
      el.innerHTML='<span style=\"color:red;\">✖ 增强失败: '+(d.error||'')+'</span>';
      ml('增强失败','e');
    }
  }).catch(function(e){btn.disabled=false;btn.textContent='生成增强UI树';ml('增强请求失败','e');});
}
function importFromEnhanced(){
  var btn=document.getElementById('enhImportBtn');
  btn.disabled=true;btn.textContent='生成中...';
  var dir=document.getElementById('metaImportDir').value||'';
  fetch('/api/mapping/import',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sourceDir:dir,autoEnhance:false})}).then(function(r){return r.json()}).then(function(d){
    btn.disabled=false;btn.textContent='从增强UI树生成草稿';
    var el=document.getElementById('enhanceResult');
    if(d.success){
      var s=d.summary||{};
      el.innerHTML='<span style=\"color:#4CAF50;\">✔ 草稿生成完成: </span>'+
        '待审 <b>'+s.pending+'</b> | '+
        '总数 '+s.totalDrafts+' | '+
        '高信度 <span style=\"color:#4CAF50;\">'+(s.highConfidence||'?')+'</span> | '+
        '缺描述 '+s.missingDescription;
      document.getElementById('enhReviewBtn').disabled=false;
      ml('草稿完成: '+s.pending+'待审');
    }else{
      el.innerHTML='<span style=\"color:red;\">✖ 草稿生成失败: '+(d.error||'')+'</span>';
      ml('草稿生成失败','e');
    }
  }).catch(function(e){btn.disabled=false;btn.textContent='从增强UI树生成草稿';ml('草稿生成请求失败','e');});
}
function switchMetaTab(tab){
  // 切换到元数据页签
  var tabs=document.querySelectorAll('.meta-subtab');
  tabs.forEach(function(t){t.classList.remove('active');});
  showMeta(tab);
}


// ===== 初始化 =====
chkAll();depChk();refSt();ldDrafts();ldMaps();ldMetaSt();chkAno();
ldHist();ldVerify();anoHist();loadCases();checkLogin();loadStateDiff();loadPageGraphInfo();
setTimeout(enhanceStatus,500);
setTimeout(prepareRefreshSummary,700);
document.getElementById('sbTime').textContent=new Date().toLocaleString();
setInterval(function(){document.getElementById('sbTime').textContent=new Date().toLocaleString();},60000);

// ===== 阶段2-5 前端函数 =====
function refreshBridge(){
  fetch('/api/unity/bridge/status').then(function(r){return r.json()}).then(function(d){
    var st=d.success?d:{};
    var conn=st.connected?'<span style=\"color:#4CAF50;\">已连接</span>':'<span style=\"color:#f44336;\">未连接</span>';
    document.getElementById('bridgeSt').innerHTML=conn;
    document.getElementById('playSt').innerHTML=st.playMode?'<span style=\"color:#4CAF50;\">运行</span>':'<span style=\"color:#888;\">停止</span>';
    document.getElementById('sceneVal').textContent=st.sceneId||'-';
    document.getElementById('resVal').textContent=(st.nodeCount||0)+'节点';
    document.getElementById('rnComp').textContent=st.componentClickableCount||'-';
    document.getElementById('rnIcon').textContent=st.interactiveIconCount||'-';
    document.getElementById('rnCell').textContent=st.interactiveCellCount||'-';
    document.getElementById('rnEff').textContent=st.effectiveClickableCount||'-';
    if(st.connected){
      document.getElementById('runtimeMatchBar').style.display='flex';
      document.getElementById('rmStatus').innerHTML='<span style=\"color:#5C6BC0;\">已连接</span>';
    }
    ml('Bridge状态已刷新');
  }).catch(function(e){ml('Bridge刷新失败','e');});
}
function refreshRuntimeUI(){
  var btn=document.getElementById('refreshRuntimeBtn');
  btn.disabled=true;btn.textContent='刷新中...';
  document.getElementById('runtimeUiStatus').textContent='请求运行态UI树...';
  fetch('/api/runtime_ui/refresh',{method:'POST'}).then(function(r){return r.json()}).then(function(d){
    btn.disabled=false;btn.textContent='刷新运行态UI树';
    if(d.success){
      document.getElementById('runtimeUiStatus').innerHTML='<span style=\"color:#4CAF50;\">✔ '+d.nodeCount+'节点 | 组件'+d.componentClickableCount+' 图标'+d.interactiveIconCount+' 格子'+d.interactiveCellCount+' 场景'+(d.sceneObjectCount||0)+' 有效'+d.effectiveClickableCount+'</span>';
      ml('运行态UI树已刷新: '+d.pageId+' ('+d.nodeCount+'节点)');
    }else{
      document.getElementById('runtimeUiStatus').innerHTML='<span style=\"color:red;\">✖ '+(d.error||'失败')+'</span>';
      ml('运行态UI树刷新失败','e');
    }
  }).catch(function(e){btn.disabled=false;btn.textContent='刷新运行态UI树';ml('请求失败','e');});
}
function runRuntimeMatch(){
  var bar=document.getElementById('rmResult');
  bar.innerHTML='匹配中...';
  fetch('/api/mapping/runtime_match',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'}).then(function(r){return r.json()}).then(function(d){
    if(d.success){
      bar.innerHTML='<span style=\"color:#4CAF50;\">匹配完成: '+d.matched+'/'+d.totalCandidates+' 已匹配'+(d.conflicts?', '+d.conflicts+'冲突':'')+'</span>';
      ml('运行态匹配: '+d.matched+'/'+d.totalCandidates);
      ldDrafts();
    }else{
      bar.innerHTML='<span style=\"color:red;\">✖ '+(d.error||'失败')+'</span>';
    }
  }).catch(function(e){bar.innerHTML='<span style=\"color:red;\">请求失败</span>';});
}
// 初始化时自动检查Bridge
setTimeout(refreshBridge,1000);
  // IDE 状态刷新
  function refreshIdeStatus(){
    fetch('/api/ide/status').then(function(r){return r.json()}).then(function(d){
      var pid=d.pid||'?';var ver=d.version||'?';var sec=d.uptimeSec||0;
      var m=Math.floor(sec/60);var s=Math.floor(sec%60);
      document.getElementById('ideStatus').textContent=ver+' PID:'+pid+' '+m+'m'+s+'s';
    });
  }
  refreshIdeStatus();setInterval(refreshIdeStatus,15000);


}}}
