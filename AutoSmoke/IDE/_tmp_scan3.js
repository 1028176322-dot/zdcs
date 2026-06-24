const fs = require('fs');
const s = fs.readFileSync('E:/zdcs/AutoSmoke/IDE/_tmp_js_check.js', 'utf8');
let inSingle=false,inDouble=false,inTemplate=false,inLine=false,inBlock=false,esc=false;
let line=1;
const st=[];
function push(ch){st.push({ch, line});}
for(let i=0;i<s.length;i++){
  const ch=s[i], nxt=s[i+1];
  if (ch==='\n') line++;
  if(inLine){ if(ch==='\n') inLine=false; continue; }
  if(inBlock){
    if(ch==='*' && nxt==='/' ){inBlock=false;i++;}
    continue;
  }
  if(inSingle){
    if(esc){esc=false; continue;}
    if(ch==='\\'){esc=true; continue;}
    if(ch==="'") inSingle=false;
    continue;
  }
  if(inDouble){
    if(esc){esc=false; continue;}
    if(ch==='\\'){esc=true; continue;}
    if(ch==='"') inDouble=false;
    continue;
  }
  if(inTemplate){
    if(esc){esc=false; continue;}
    if(ch==='\\'){esc=true; continue;}
    if(ch==='`') inTemplate=false;
    continue;
  }

  if(ch==='/' && nxt==='/' ){ inLine=true; i++; continue; }
  if(ch==='/' && nxt==='*' ){ inBlock=true; i++; continue; }
  if(ch==="'"){ inSingle=true; continue; }
  if(ch==='"'){ inDouble=true; continue; }
  if(ch==='`'){ inTemplate=true; continue; }

  if (ch==='('||ch==='{'||ch==='[') push(ch);
  else if (ch===')'||ch==='}'||ch===']'){
    if(st.length===0){ console.log('extra close', ch, 'at', line); continue; }
    const o=st.pop();
    const pair={')':'(',']':'[','}':'{'}[ch];
    if(o.ch!==pair){ console.log('mismatch', o.ch, 'from', o.line, 'closed by', ch, 'at', line); }
  }
}
const left = st.filter(x=>x.ch==='(').map(x=>x.line);
const leftBr= st.filter(x=>x.ch==='{').map(x=>x.line);
const leftSq= st.filter(x=>x.ch==='[').map(x=>x.line);
console.log('unclosed paren',left);
console.log('unclosed brace',leftBr);
console.log('unclosed bracket',leftSq);
console.log('stack size', st.length, 'line', line);
