const fs=require('fs');
const lines=fs.readFileSync('E:/zdcs/AutoSmoke/IDE/_tmp_js_check.js','utf8').split(/\r?\n/);
let inSingle=false,inDouble=false,inTemplate=false,inLine=false,inBlock=false,esc=false;
let cnt=0;
for(let i=0;i<lines.length;i++){
  const s=lines[i];
  const arr=[...s];
  for(let j=0;j<arr.length;j++){
    const ch=arr[j]; const nxt=arr[j+1];
    if(inLine){ if(ch==='\n'){}} 
    if(inLine){ if(ch==='\n'){}} 
    if(inLine) { continue; }
    if(inBlock){ if(ch==='*'&&nxt==='/' ){inBlock=false; j++;} continue; }
    if(inSingle){ if(esc){esc=false; continue;} if(ch==='\\'){esc=true; continue;} if(ch==="'") inSingle=false; continue; }
    if(inDouble){ if(esc){esc=false; continue;} if(ch==='\\'){esc=true; continue;} if(ch==='"') inDouble=false; continue; }
    if(inTemplate){ if(esc){esc=false; continue;} if(ch==='\\'){esc=true; continue;} if(ch==='`') inTemplate=false; continue; }
    if(ch==='/'&&nxt==='/' ){inLine=true; continue; }
    if(ch==='/'&&nxt==='*' ){inBlock=true; j++; continue; }
    if(ch==="'"){ inSingle=true; continue; }
    if(ch==='"'){ inDouble=true; continue; }
    if(ch==='`'){ inTemplate=true; continue; }
    if(ch==='{' ) cnt++;
    if(ch==='}') cnt--;
  }
  console.log(String(i+1).padStart(4), cnt, lines[i]);
}
