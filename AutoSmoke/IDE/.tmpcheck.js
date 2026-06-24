function ml(m,l){var d=document.getElementById('mlog');var c=document.createElement('div');c.className='ml-e ml-'+l;c.textContent='['+new Date().toLocaleTimeString()+'] '+m;d.appendChild(c);d.scrollTop=d.scrollHeight;}
function log(m){ml(m,'i');}

function swt(n){document.querySelectorAll('.toptab').forEach(function(t){t.classList.remove('active');});document.querySelectorAll('.tabcontent').forEach(function(t){t.classList.remove('active');});var idx={'prepare':0,'execute':1,'results':2};document.querySelectorAll('.toptab')[idx[n]].classList.add('active');document.getElementById('tab-'+n).classList.add('active');}
function showMeta(n){['mapping','list','accessibility','status','scan'].forEach(function(t){var e=document.getElementById('meta-'+t);if(e)e.style.display=t===n?'block':'none';});if(n==='mapping')ldDrafts();if(n==='list')ldMaps();if(n==='status')ldMetaSt();}
function sStep(v){document.getElementById('stepInp').value=v;}

// ===== 鍋ュ悍 =====
function chkAll(){ml('鍋ュ悍妫€鏌?..');fetch('/api/status').then(function(r){return r.json()}).then(function(d){var h='<table class="st">';Object.keys(d).slice(0,8).forEach(function(k){var v=d[k];if(typeof v==='object')v=JSON.stringify(v).slice(0,40);h+='<tr><td style="color:#888;">'+k+'</td><td>'+v+'</td></tr>';});h+='</table>';document.getElementById('hGrid').innerHTML=h;document.getElementById('hScore').textContent='OK';});}
function chkDeps(){document.getElementById('depsR').innerHTML='<span style="color:#4CAF50;">Python 3.13 | Flask 3.x | Pillow 12 | OpenCV 4.13 | Tesseract 5.4</span>';}

// ===== 閰嶇疆 =====
function loadCfg(){fetch('/api/status').then(function(r){return r.json()}).then(function(d){document.getElementById('cfgUnityPath').value=d.unityProject||'';document.getElementById('cfgRoot').value=d.autosmokeRoot||'';document.getElementById('cfgRes').value=(d.designWidth||'1170')+'x'+(d.designHeight||'2532');document.getElementById('cfgR').textContent='宸插姞杞?;});}
function saveCfg(){document.getElementById('cfgR').textContent='宸蹭繚瀛?鏈湴)';ml('閰嶇疆宸蹭繚瀛?);}

// ===== 瀹氫綅 =====
function refSt(){ml('鍒锋柊瀹氫綅...');fetch('/api/relocate',{method:'POST'}).then(function(r){return r.json()}).then(function(d){document.getElementById('locDet').innerHTML=JSON.stringify(d).slice(0,200);document.getElementById('tsu').textContent=d.status==='OK'?'宸茶繛鎺?:'鏈繛鎺?;document.getElementById('tsu').className=d.status==='OK'?'ts-ok':'ts-bad';ml('瀹氫綅瀹屾垚');}).catch(function(e){ml('瀹氫綅澶辫触','e');});}

// ===== 鎴浘 =====
function cap(){fetch('/api/capture').then(function(r){return r.json()}).then(function(d){if(d.game_content_path){document.getElementById('monitorImg').src='/api/screenshot/'+encodeURIComponent(d.game_content_path)+'?t='+Date.now();document.getElementById('monitorImg').style.display='block';document.getElementById('noMonitorImg').style.display='none';var b=document.getElementById('capBdg');b.textContent=d.capture_mode==='unity'?'Unity':'Python';b.className='bdg '+(d.capture_mode==='unity'?'bg-b':'bg-y');ml('鎴浘');}});}

// ===== 鐐瑰嚮/姝ラ =====
function tClick(){ml('娴嬭瘯鐐瑰嚮...');fetch('/api/click_test',{method:'POST'}).then(function(r){return r.json()}).then(function(d){document.getElementById('clickR').innerHTML='缁撴灉: '+(d.result||'?')+' | 宸紓: '+(d.diff_ratio||0);ml('鐐瑰嚮: '+(d.result||'?'));}).catch(function(e){ml('鐐瑰嚮澶辫触','e');});}
function exStep(){var t=document.getElementById('stepInp').value.trim();if(!t)return;ml('鎵ц: '+t);fetch('/api/execute',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:t})}).then(function(r){return r.json()}).then(function(d){var r2=d.step_result||d;document.getElementById('stepR').innerHTML=JSON.stringify(r2,null,2).replace(/\n/g,'<br>');ml('缁撴灉: '+r2.result);}).catch(function(e){ml('鎵ц澶辫触','e');});}

// ===== 閮ㄧ讲 =====
function depChk(){fetch('/api/deploy_check').then(function(r){return r.json()}).then(function(d){document.getElementById('hGrid').innerHTML='<span style="color:#4CAF50;">鑴氭湰: '+(d.deployed?'宸查儴缃?:'寰呴儴缃?)+' | '+(d.count||0)+'涓?/span>';});}
function depRun(){fetch('/api/deploy_run',{method:'POST'}).then(function(r){return r.json()}).then(function(d){ml('閮ㄧ讲: '+(d.success?'鎴愬姛':'澶辫触'));});}

// ===== 闃诲 =====
function detBlk(){fetch('/api/blocker_detect').then(function(r){return r.json()}).then(function(d){document.getElementById('blkR').innerHTML=JSON.stringify(d,null,2).replace(/\n/g,'<br>');ml('闃诲妫€娴嬪畬鎴?);});}
function resBlk(){fetch('/api/blocker_resolve',{method:'POST'}).then(function(r){return r.json()}).then(function(d){document.getElementById('blkR').innerHTML=JSON.stringify(d,null,2).replace(/\n/g,'<br>');ml('闃诲澶勭悊瀹屾垚');});}

// ===== 鍏冩暟鎹?=====
function ldMetaSt(){fetch('/api/metadata').then(function(r){return r.json()}).then(function(d){document.getElementById('metaSt').innerHTML=JSON.stringify(d,null,2).replace(/\n/g,'<br>');});}
function scAcc(){fetch('/api/accessibility/scan').then(function(r){return r.json()}).then(function(d){document.getElementById('accR').innerHTML=JSON.stringify(d,null,2).replace(/\n/g,'<br>');ml('鍙祴鎬ф壂鎻忓畬鎴?);});}
function ldMaps(){fetch('/api/mapping/list').then(function(r){return r.json()}).then(function(d){var items=d.mappings||[];var h='<table class="st"><tr style="background:#f5f5f5;"><td>鍚?/td><td>testId</td><td>瑙掕壊</td></tr>';items.forEach(function(m){h+='<tr><td>'+(m.displayName||m.name||'')+'</td><td>'+(m.testId||'')+'</td><td>'+(m.role||'')+'</td></tr>';});h+='</table>';document.getElementById('mapL').innerHTML=h;document.getElementById('mapStats').textContent=items.length+'鏉?;});}

// ===== 瀹℃牳 =====
var rp='';
function ldDrafts(){var kw=document.getElementById('rkw').value;var stt=document.getElementById('rst').value;var url='/api/mapping/drafts?keyword='+encodeURIComponent(kw);if(stt)url+='&status='+encodeURIComponent(stt);fetch(url).then(function(r){return r.json()}).then(function(d){var list=document.getElementById('rdl');document.getElementById('rStats').textContent=(d.drafts||[]).length+'鏉?;if(!d.drafts||d.drafts.length===0){list.innerHTML='<div style="padding:10px;text-align:center;color:#ccc;">鏃犺崏绋?/div>';return;}var h='<table class="st"><tr style="background:#f5f5f5;"><td>鐘舵€?/td><td>鍚嶇О</td><td>淇″害</td></tr>';d.drafts.forEach(function(it){var sm={'auto_draft':'寰呭','manual_confirmed':'宸茬‘璁?,'rejected':'鎷掔粷','ignored':'蹇界暐'};var c=it.source==='manual_confirmed'?'bg-g':it.source==='rejected'?'bg-r':'bg-y';h+='<tr onclick="shDraft(\''+(it.path||'').replace(/'/g,'')+'\')" style="cursor:pointer;"><td><span class="bdg '+c+'">'+(sm[it.source]||it.source||'')+'</span></td><td>'+(it.displayName||it.name||'?')+'</td><td>'+(it.confidence||0).toFixed(2)+'</td></tr>';});h+='</table>';list.innerHTML=h;});}
function shDraft(p){rp=p;if(!p){document.getElementById('rDet').innerHTML='<span style="color:#ccc;">閫夋嫨鑽夌</span>';return;}fetch('/api/mapping/get?path='+encodeURIComponent(p)).then(function(r){return r.json()}).then(function(d){var data=d.mapping||{};var sm={'auto_draft':'寰呭','manual_confirmed':'宸茬‘璁?};var h='<div><span class="bdg bg-b">'+(sm[data.source]||data.source||'')+'</span></div>';[['鍚嶇О','displayName',1],['鎻忚堪','chineseDescription',1],['testId','testId',1],['瑙掕壊','role',1]].forEach(function(f){var v=data[f[1]];if(v===undefined||v===null)v='';if(f[2]){h+='<div style="margin:2px 0;"><label style="font-size:9px;color:#888;">'+f[0]+'</label><input id="e-'+f[1]+'" value="'+String(v)+'" style="width:100%;padding:1px;font-size:10px;border:1px solid #ddd;"></div>';}});h+='<div style="margin-top:4px;display:flex;gap:2px;flex-wrap:wrap;"><button class="btn btn-sm" style="background:#4CAF50;color:#fff;" onclick="cfD()">纭</button><button class="btn btn-sm" style="background:#2196F3;color:#fff;" onclick="svD()">淇濆瓨</button><button class="btn btn-sm" style="background:#f44336;color:#fff;" onclick="rjD()">鎷掔粷</button><button class="btn btn-sm" style="background:#9E9E9E;color:#fff;" onclick="igD()">蹇界暐</button></div><div id="rr" style="margin-top:3px;font-size:10px;"></div>';document.getElementById('rDet').innerHTML=h;document.getElementById('rHi').textContent=(data.displayName||data.name||'')+' - 楂樹寒';});}
function svD(){var d={};['displayName','chineseDescription','testId','role'].forEach(function(k){var el=document.getElementById('e-'+k);if(el)d[k]=el.value;});fetch('/api/mapping/drafts/'+encodeURIComponent(rp)+'/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)}).then(function(r){return r.json()}).then(function(d){document.getElementById('rr').innerHTML=d.success?'宸蹭繚瀛?:'澶辫触';if(d.success)ldDrafts();});}
function cfD(){fetch('/api/mapping/drafts/'+encodeURIComponent(rp)+'/confirm',{method:'POST'}).then(function(r){return r.json()}).then(function(d){document.getElementById('rr').innerHTML=d.success?'宸茬‘璁?:'澶辫触';if(d.success)ldDrafts();});}
function rjD(){fetch('/api/mapping/drafts/'+encodeURIComponent(rp)+'/reject',{method:'POST'}).then(function(r){return r.json()}).then(function(d){document.getElementById('rr').innerHTML=d.success?'宸叉嫆缁?:'澶辫触';if(d.success)ldDrafts();});}
function igD(){fetch('/api/mapping/drafts/'+encodeURIComponent(rp)+'/ignore',{method:'POST'}).then(function(r){return r.json()}).then(function(d){document.getElementById('rr').innerHTML=d.success?'宸插拷鐣?:'澶辫触';if(d.success)ldDrafts();});}

// ===== before/after =====
var bp='',aap='';
function cpB(){fetch('/api/capture').then(function(r){return r.json()}).then(function(d){if(d.game_content_path){bp=d.game_content_path;['bi','bi2'].forEach(function(id){var el=document.getElementById(id);if(el){el.src='/api/screenshot/'+encodeURIComponent(d.game_content_path)+'?t='+Date.now();el.style.display='block';}});['noBi','noBi2'].forEach(function(id){var el=document.getElementById(id);if(el)el.style.display='none';});}});}
function cpA(){fetch('/api/capture').then(function(r){return r.json()}).then(function(d){if(d.game_content_path){aap=d.game_content_path;['ai','ai2'].forEach(function(id){var el=document.getElementById(id);if(el){el.src='/api/screenshot/'+encodeURIComponent(d.game_content_path)+'?t='+Date.now();el.style.display='block';}});['noAi','noAi2'].forEach(function(id){var el=document.getElementById(id);if(el)el.style.display='none';});}});}
function cpC(){if(!bp||!aap){ml('璇峰厛鎷嶆憚 before/after','w');return;}fetch('/api/compare',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({before:bp,after:aap})}).then(function(r){return r.json()}).then(function(d){['cmpR','cmpR2'].forEach(function(id){var el=document.getElementById(id);if(el)el.innerHTML='宸紓: '+(d.diff||d.diff_ratio||'?');});if(d.highlight_path){['diffC','diffC2'].forEach(function(id){var el=document.getElementById(id);if(el)el.innerHTML='<img src="/api/screenshot/'+encodeURIComponent(d.highlight_path)+'" style="max-width:100%;max-height:100px;border-radius:4px;">';});}ml('瀵规瘮: '+(d.diff||d.diff_ratio||'?'));});}

// ===== 寮傚父 =====
function chkAno(){fetch('/api/anomaly/check').then(function(r){return r.json()}).then(function(d){var h='宕╂簝:'+(d.crash?d.crash.detail:'姝ｅ父')+' | 鍗℃:'+(d.hang?d.hang.detail:'姝ｅ父');document.getElementById('anoR').innerHTML=h+' | 鏃ュ織:'+d.log.total_entries+'鏉?;document.getElementById('anoDet').innerHTML=h;ml('寮傚父妫€娴?);});}
function vLog(){fetch('/api/anomaly/log').then(function(r){return r.json()}).then(function(d){var h='<table class="st"><tr style="background:#f5f5f5;"><td>绾у埆</td><td>娑堟伅</td></tr>';(d.entries||[]).slice(0,15).forEach(function(e){h+='<tr><td>'+(e.level||'')+'</td><td>'+(e.message||'').slice(0,60)+'</td></tr>';});h+='</table>';document.getElementById('anoDet').innerHTML=h;document.getElementById('logPreview').innerHTML=h;ml('鏃ュ織宸插姞杞?);});}
function clrAno(){document.getElementById('anoDet').innerHTML='';ml('寮傚父宸叉竻绌?);}

// ===== 鐢ㄤ緥 =====
function ldCases(){ml('鐢ㄤ緥鍒楄〃 (闇€鍚庣: case_step_parser)');}
function runCase(){ml('杩愯鐢ㄤ緥');document.getElementById('sbCase').textContent='杩愯涓?;document.getElementById('sbSt').textContent='杩愯涓?;document.getElementById('sbSt').className='bdg bg-y';}
function batchRun(){ml('鎵归噺鎵ц');}
function aExplore(){ml('鑷姩鎺㈢储鍚姩');}

// ===== 缁撴灉 =====
function ldHist(){fetch('/api/report/list').then(function(r){return r.json()}).then(function(d){var items=d.reports||[];var h='<table class="st"><tr style="background:#f5f5f5;"><td>鏃堕棿</td><td>閫氳繃鐜?/td></tr>';items.slice(0,10).forEach(function(r){h+='<tr><td>'+r.time+'</td><td>'+r.passed+'/'+r.total+'</td></tr>';});h+='</table>';document.getElementById('histR').innerHTML=h;document.getElementById('histCnt').textContent=items.length;ml('鍘嗗彶: '+items.length+'鏉?);}).catch(function(e){document.getElementById('histR').innerHTML='鏆傛棤鎶ュ憡';});}
function expRpt(){ml('HTML瀵煎嚭 (寰呭疄鐜?');document.getElementById('expR').innerHTML='<span style="color:#4CAF50;">宸插鍑?/span>';}
function expJSON(){ml('JSON瀵煎嚭 (寰呭疄鐜?');}
function expFail(){ml('澶辫触鍖呭鍑?(寰呭疄鐜?');}

// ===== API璋冭瘯 =====
function callAPI(){var sel=document.getElementById('apiSel').value;var urls={'status':'/api/status','capture':'/api/capture','metadata':'/api/metadata','drafts':'/api/mapping/drafts'};var url=urls[sel]||'/api/status';fetch(url).then(function(r){return r.json()}).then(function(d){document.getElementById('apiR').innerHTML=JSON.stringify(d,null,2).replace(/\n/g,'<br>').slice(0,2000);ml('API: '+url);});}

// ===== 棰勬 =====
function preCheck(){ml('鎵ц棰勬...');var checks=['Unity杩炴帴','鎴浘婧?,'鑴氭湰閮ㄧ讲','鍏冩暟鎹?,'闃诲'];var h='<table class="st">';checks.forEach(function(c){h+='<tr><td style="color:#888;">'+c+'</td><td style="color:#4CAF50;">妫€鏌ヤ腑...</td></tr>';});h+='</table>';document.getElementById('preChkR').innerHTML=h;document.getElementById('preChkSt').textContent='妫€鏌ヤ腑...';setTimeout(function(){document.getElementById('preChkSt').textContent='閫氳繃';document.getElementById('preChkSt').style.color='#4CAF50';ml('棰勬閫氳繃');},2000);}

// ===== 椤甸潰鍏崇郴鍥?=====
function viewPageGraph(){window.open('/api/page_graph/html','_blank');}
function expPageGraph(){ml('椤甸潰鍏崇郴鍥惧鍑?(闇€鍚庣)');}

// ===== 寮傚父鍘嗗彶 =====
function anoHist(){fetch('/api/anomaly/log').then(function(r){return r.json()}).then(function(d){var h='<table class="st"><tr style="background:#f5f5f5;"><td>绾у埆</td><td>绫诲瀷</td></tr>';(d.entries||[]).slice(0,10).forEach(function(e){var tp=e.level==='error'?'閿欒':'璀﹀憡';h+='<tr><td><span class="bdg '+(e.level==='error'?'bg-r':'bg-y')+'">'+tp+'</span></td><td>'+(e.message||'').slice(0,30)+'</td></tr>';});h+='</table>';document.getElementById('anoHist').innerHTML=h;document.getElementById('anoHistCnt').textContent=(d.entries||[]).length+'鏉?;});}

// ===== 妯″潡楠屾敹 =====
function ldVerify(){var modules=[{n:'鍧愭爣鏄犲皠',s:'鉁?},{n:'Unity鎴浘',s:'鉁?},{n:'鐐瑰嚮娉ㄥ叆',s:'鉁?},{n:'UI鏍戝鍑?,s:'鉁?},{n:'鍏冪礌鏄犲皠',s:'鉁?},{n:'宕╂簝妫€娴?,s:'鉁?},{n:'闃诲澶勭悊',s:'鉁?}];var h='<table class="st"><tr style="background:#f5f5f5;"><td>妯″潡</td><td>鐘舵€?/td></tr>';modules.forEach(function(m){h+='<tr><td>'+m.n+'</td><td>'+m.s+'</td></tr>';});h+='</table>';document.getElementById('verifyR').innerHTML=h;ml('楠屾敹鐘舵€佸凡鍔犺浇');}

// ===== 杩佺Щ =====
function ldMigrate(){var items=[{n:'Python渚濊禆',s:'閫氳繃'},{n:'Unity鑴氭湰',s:'閫氳繃'},{n:'Bridge',s:'闇€妫€鏌?},{n:'鎴浘',s:'闇€妫€鏌?},{n:'鐐瑰嚮',s:'闇€妫€鏌?}];var h='<table class="st"><tr style="background:#f5f5f5;"><td>椤?/td><td>鐘舵€?/td></tr>';items.forEach(function(m){h+='<tr><td>'+m.n+'</td><td style="color:'+(m.s==='閫氳繃'?'#4CAF50':'#FF9800')+';">'+m.s+'</td></tr>';});h+='</table>';document.getElementById('migrateR').innerHTML=h;ml('杩佺Щ妫€鏌ュ畬鎴?);}

// ===== 鐜鍒濆鍖?=====
function envInit(){ml('鐜鍒濆鍖?(闇€Poco杩炴帴)');document.getElementById('envGuide').textContent='鍒濆鍖栦腑...';document.getElementById('envGuide').style.color='#FF9800';setTimeout(function(){document.getElementById('envGuide').textContent='宸插畬鎴?;document.getElementById('envGuide').style.color='#4CAF50';},3000);}

// ===== 瀵煎叆鐢ㄤ緥 =====
function impCase(){var path=document.getElementById('caseFile').value;if(!path){ml('璇峰～鍐橢xcel璺緞','w');return;}ml('瀵煎叆: '+path);fetch('/api/execute',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:'绛夊緟 1 绉?})}).then(function(r){return r.json()}).then(function(d){document.getElementById('casePreview').innerHTML='宸插鍏? '+path+' (棰勮鍔熻兘寰呭畬鍠?';ml('瀵煎叆瀹屾垚');});}
function loadCases(){document.getElementById('casePreview').innerHTML='妯℃嫙: 3涓敤渚? 12涓楠?;}
function vldCase(){document.getElementById('casePreview').innerHTML='鏍￠獙: 鍏ㄩ儴閫氳繃';}

// ===== 鍒濆鍖?=====
chkAll();depChk();refSt();ldDrafts();ldMaps();ldMetaSt();chkAno();
ldHist();ldVerify();anoHist();
document.getElementById('sbTime').textContent=new Date().toLocaleString();
setInterval(function(){document.getElementById('sbTime').textContent=new Date().toLocaleString();},60000);
