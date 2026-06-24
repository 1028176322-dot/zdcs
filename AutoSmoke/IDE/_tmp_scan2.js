const fs = require('fs');
const s = fs.readFileSync('E:/zdcs/AutoSmoke/IDE/_tmp_js_check.js', 'utf8');
let inSingle=false,inDouble=false,inTemplate=false,inLineComment=false,inBlockComment=false,esc=false;
let line=1;
let par=0,cur=0,bra=0;
const stack=[];
for(let i=0;i<s.length;i++){
  const ch=s[i];
  const nxt=s[i+1];
  if (ch==='\n') line++;
  if (inLineComment){ if(ch==='\n') inLineComment=false; continue; }
  if (inBlockComment){
    if(ch==='*'&&nxt==='/' ){inBlockComment=false;i++;}
    if(ch==='\n'){}
    continue;
  }
  if (inSingle){
    if(esc){esc=false; continue;}
    if(ch==='\\'){esc=true; continue;}
    if(ch==="'") inSingle=false;
    continue;
  }
  if (inDouble){
    if(esc){esc=false; continue;}
    if(ch==='\\'){esc=true; continue;}
    if(ch==='"') inDouble=false;
    continue;
  }
  if (inTemplate){
    if(esc){esc=false; continue;}
    if(ch==='\\'){esc=true; continue;}
    if(ch==='`') inTemplate=false;
    continue;
  }

  if (ch==='/' && nxt==='/' ) { inLineComment=true; i++; continue; }
  if (ch==='/' && nxt==='*' ) { inBlockComment=true; i++; continue; }
  if (ch==="'") {inSingle=true; continue;}
  if (ch==='"') {inDouble=true; continue;}
  if (ch==='`') {inTemplate=true; continue;}

  if (ch==='('){stack.push({t:'(', line}); par++;}
  else if (ch===')'){par--; if(par<0){console.log('extra ) at',line);} }
  else if (ch==='['){stack.push({t:'[', line}); cur++;}
  else if (ch===']'){cur--; if(cur<0){console.log('extra ] at',line);} }
  else if (ch==='{'){stack.push({t:'{', line}); bra++;}
  else if (ch==='}'){
    if (bra<=0) console.log('extra } at',line); else {const o=stack.pop(); if(!o||o.t!=='{') console.log('mismatch at',line,o);}
    bra--;
  }
}
console.log('final', {lineCount: line, par, cur, bra});
if(par>0) console.log('unclosed(', stack.filter(x=>x.t==='(').slice(-3));
if(cur>0) console.log('unclosed[', stack.filter(x=>x.t==='[').slice(-3));
if(bra>0) console.log('unclosed{', stack.filter(x=>x.t==='{').slice(-3));
