const fs = require('fs');
const line = fs.readFileSync('E:/zdcs/AutoSmoke/IDE/_tmp_js_check.js','utf8').split(/\r?\n/)[145];
let inSingle=false,inDouble=false,inTemplate=false,esc=false;
for(let i=0;i<line.length;i++){
  const ch=line[i], nxt=line[i+1];
  if(ch==='/'&&nxt==='/' && !inSingle&&!inDouble&&!inTemplate){console.log('line',i,'line comment start'); break;}
  if(inSingle){
    if(esc){esc=false;} else if(ch==='\\'){esc=true;} else if(ch==="'"){inSingle=false; console.log('close single',i)}
    continue;
  }
  if(inDouble){
    if(esc){esc=false;} else if(ch==='\\'){esc=true;} else if(ch==='"'){inDouble=false; console.log('close double',i)}
    continue;
  }
  if(ch==="'"){inSingle=true; console.log('open single',i);}
  if(ch==='"'){inDouble=true; console.log('open double',i);}
  if(ch==='`'){inTemplate=!inTemplate; console.log('template',i,inTemplate)}
  if(ch==='{'||ch==='}') console.log('brace',ch,i,'state',inSingle,inDouble,inTemplate);
}
console.log('end state',line)
