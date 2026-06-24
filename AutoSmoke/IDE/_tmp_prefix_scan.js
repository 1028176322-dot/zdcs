const fs=require('fs');
const lines=fs.readFileSync('E:/zdcs/AutoSmoke/IDE/_tmp_js_check.js','utf8').split(/\r?\n/);
let firstFail=-1;
for(let n=1;n<=lines.length;n++){
  const code=lines.slice(0,n).join('\n');
  try{new Function(code);}
  catch(e){
    if(firstFail===-1) firstFail=n;
    break;
  }
}
if(firstFail===-1){
  console.log('all-ok', lines.length);
  return;
}
console.log('firstFailLine', firstFail);
for(let start=Math.max(1, firstFail-40);start<=Math.min(lines.length, firstFail+40);start++){
  const code=lines.slice(0,start).join('\n');
  try{new Function(code);}
  catch(e){console.log('failAt',start,'->',e.message);}
}
