function sStep(v){document.getElementById('stepInp').value=v;}
function escHtml(v){var s=String(v==null?'':v);return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\"/g,'&quot;').replace(/'/g,'&#39;');}
function precheckAutoRetryEnabled(){var el=document.getElementById('precheckAutoRetry');return !!(el&&el.checked);}
