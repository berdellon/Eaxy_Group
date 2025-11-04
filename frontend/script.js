const API_BASE = window.location.origin + '/api';
function el(id){return document.getElementById(id);}
function showScreen(id){document.querySelectorAll('.screen, #login-screen, #home-screen').forEach(s=>s.classList.add('hidden')); document.getElementById(id).classList.remove('hidden');}
function setWelcome(user){el('welcome').textContent = 'Bienvenido ' + user;}
el('btn-login').addEventListener('click', async ()=>{
  const user = el('login-user').value.trim();
  const pin = el('login-pin').value.trim();
  if(!user || !pin){ el('login-msg').textContent='Introduce usuario y PIN'; return; }
  try{
    const res = await fetch(API_BASE + '/login', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({username:user, pin})});
    const j = await res.json();
    if(res.ok && j.ok){ localStorage.setItem('usuario', user); setWelcome(user); showScreen('home-screen'); load_ops_summary(); }
    else { el('login-msg').textContent = j.msg || 'Login fallido'; }
  }catch(e){ el('login-msg').textContent = 'Error servidor'; }
});
el('btn-ops').addEventListener('click', ()=> { load_operations(); showScreen('ops-screen'); });
el('btn-caja').addEventListener('click', ()=> { load_caja(); showScreen('caja-screen'); });
el('btn-conv').addEventListener('click', ()=> { showScreen('conv-screen'); });
el('btn-ajustes').addEventListener('click', ()=> { showScreen('ajustes-screen'); });
el('btn-ver-todas').addEventListener('click', ()=> { load_operations(true); showScreen('ops-screen'); });
document.getElementById('ajustes-screen').innerHTML = `<div class="card"><h3>Ajustes</h3><div style="margin-top:8px"><button class="capsule" id="btn-export">Exportar backup</button> <button class="capsule" id="btn-import">Importar backup</button><input id="file-import" type="file" style="display:none"/></div></div>`;
document.getElementById('btn-export').addEventListener('click', async ()=>{ const r=await fetch(API_BASE+'/backup/export'); const j=await r.json(); const blob=new Blob([JSON.stringify(j,null,2)],{type:'application/json'}); const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download='backup.json'; a.click(); });
document.getElementById('btn-import').addEventListener('click', ()=> document.getElementById('file-import').click());
document.getElementById('file-import').addEventListener('change', async (e)=>{ const f=e.target.files[0]; if(!f) return; const fd=new FormData(); fd.append('file', f); const r=await fetch(API_BASE+'/backup/import',{method:'POST',body:fd}); const j=await r.json(); if(j.ok){ alert('Importado'); load_operations(); load_caja(); } else alert('Error import'); });
if(localStorage.getItem('usuario')){ setWelcome(localStorage.getItem('usuario')); showScreen('home-screen'); } else { showScreen('login-screen'); }
