const fs = require('fs');
const s = fs.readFileSync('E:/zdcs/AutoSmoke/IDE/_tmp_js_check.js', 'utf8');
let inSingle = false, inDouble = false, inTemplate = false, esc = false;
let line = 1;
let par = 0, bra = 0, cur = 0;
const opens = [];
for (let i = 0; i < s.length; i++) {
  const ch = s[i];
  const nxt = s[i + 1];
  if (ch === '\n') line++;
  if (inSingle) {
    if (esc) {
      esc = false;
    } else if (ch === '\\') {
      esc = true;
    } else if (ch === "'") {
      inSingle = false;
    }
    continue;
  }
  if (inDouble) {
    if (esc) {
      esc = false;
    } else if (ch === '\\') {
      esc = true;
    } else if (ch === '"') {
      inDouble = false;
    }
    continue;
  }
  if (inTemplate) {
    if (esc) {
      esc = false;
    } else if (ch === '\\') {
      esc = true;
    } else if (ch === '`') {
      inTemplate = false;
    }
    continue;
  }

  if (ch === '/' && nxt === '/') {
    i++;
    while (i < s.length && s[i + 1] !== '\n') {
      i++;
    }
    continue;
  }
  if (ch === '/' && nxt === '*') {
    i++;
    while (i + 1 < s.length) {
      if (s[i] === '*' && s[i + 1] === '/') {
        i++;
        break;
      }
      if (s[i] === '\n') line++;
      i++;
    }
    continue;
  }

  if (ch === "'") { inSingle = true; continue; }
  if (ch === '"') { inDouble = true; continue; }
  if (ch === '`') { inTemplate = true; continue; }

  if (ch === '(') { par++; opens.push(['(', line]); }
  else if (ch === ')') { if (par <= 0) opens.push(['extra)', line]); par--; }
  else if (ch === '{') { bra++; opens.push(['{', line]); }
  else if (ch === '}') { if (bra <= 0) opens.push(['extra}', line]); bra--; }
  else if (ch === '[') { cur++; opens.push(['[', line]); }
  else if (ch === ']') { if (cur <= 0) opens.push(['extra]', line]); cur--; }
}
console.log('par', par, 'bra', bra, 'cur', cur);
console.log('last open (line):', opens.filter(x=>x[0]==='{').slice(-1)[0]);
console.log('last paren:', opens.filter(x=>x[0]==='(').slice(-1)[0]);
console.log('last bracket:', opens.filter(x=>x[0]==='[').slice(-1)[0]);
console.log('openCount', opens.length);
