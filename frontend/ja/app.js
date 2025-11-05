const API_BASE = window.location.origin + '/api';
function el(q){return document.querySelector(q);}
async function postJson(url,data){return fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});}

document.getElementById('btn-login').addEventListener('click', async ()=>{
  const user=document.getElementById('login-user').value.trim();
  const pin=document.getElementById('login-pin').value.trim();
  if(!user||!pin){ document.getElementById('login-msg').textContent='Introduce usuario y PIN'; return; }
  try{
    const res = await postJson(API_BASE + '/login',{username:user,pin});
    const j = await res.json();
    if(res.ok && j.ok){ localStorage.setItem('usuario', j.username); loadHome(j.username); } else { document.getElementById('login-msg').textContent = j.msg || 'Login fallido'; }
  }catch(e){ document.getElementById('login-msg').textContent = 'Error servidor'; }
});

function loadHome(user){
  document.getElementById('login-screen').classList.add('hidden');
  const root = document.getElementById('app-root'); root.classList.remove('hidden');
  root.innerHTML = `<div class="card"><div class="topbar"><div><strong>Bienvenido, ${user}</strong></div><div><button id="logout" class="capsule">Cerrar sesión</button></div></div><div class="app-grid"><button class="big capsule" id="btn-ops">📋 Operaciones</button><button class="big capsule" id="btn-caja">🔒 Caja Fuerte</button><button class="big capsule" id="btn-conv">💱 Conversor</button><button class="big capsule" id="btn-ajustes">⚙️ Ajustes</button></div><div id="main-content" style="margin-top:12px"></div></div>`;
  document.getElementById('logout').addEventListener('click', ()=>{ localStorage.removeItem('usuario'); location.reload(); });
  document.getElementById('btn-ops').addEventListener('click', ()=> loadOperations(false));
  document.getElementById('btn-caja').addEventListener('click', ()=> loadCaja());
  document.getElementById('btn-conv').addEventListener('click', ()=> loadConv());
  document.getElementById('btn-ajustes').addEventListener('click', ()=> loadAjustes());
  loadOperations(false);
}

async function loadOperations(showAll){
  const r = await fetch(API_BASE + '/operaciones'); const ops = await r.json();
  const container = document.getElementById('main-content'); const items = ops.filter(o=> showAll || o.estado !== 'Eliminada');
  let html = '<div style="margin-bottom:12px"><button class="capsule primary" onclick="openNewOp()">➕ Nueva operación</button></div>';
  if(items.length===0) html += '<div class="muted">No hay operaciones</div>';
  else items.forEach(op=>{ html += `<div class="op-item"><div><div style="font-weight:700">${op.id} — ${op.cliente}</div><div class="meta">${op.fecha} · ${op.tipo} · ${op.estado}</div></div><div style="text-align:right"><div style="font-weight:700">${(op.efectivo||0).toLocaleString('es-ES',{minimumFractionDigits:2})} €</div><div style="margin-top:8px"><button class="capsule" onclick="edit_op('${op.id}')">✏️</button> <button class="capsule" onclick="del_op('${op.id}')">🗑️</button></div></div></div>`; });
  container.innerHTML = html;
}

window.openNewOp = function(){ const html = `<div class="form"><h3>Nueva operación</h3><select id="op-tipo"><option>Cash</option><option>Envío</option><option>Depósito</option><option>Retirada</option></select><input id="op-cliente" placeholder="Cliente"/><input id="op-efectivo" placeholder="Efectivo €" type="number"/><input id="op-usdt" placeholder="USDT (si aplica)" type="number"/><input id="op-com" placeholder="Comisión" type="number"/><div style="margin-top:8px"><button class="capsule primary" id="op-save">Guardar</button> <button class="capsule" onclick="loadOperations(false)">Cancelar</button></div></div>`; document.getElementById('main-content').insertAdjacentHTML('beforeend', html); document.getElementById('op-save').addEventListener('click', saveOp); };

async function saveOp(){ const tipo = document.getElementById('op-tipo').value; const cliente = document.getElementById('op-cliente').value.trim(); const efectivo = parseFloat(document.getElementById('op-efectivo').value||0); const usdt = parseFloat(document.getElementById('op-usdt').value||0); const com = parseFloat(document.getElementById('op-com').value||0); if(!cliente){ alert('Introduce cliente'); return; } let estado = 'Finalizada'; if(tipo==='Envío' || tipo==='Retirada'){ estado = confirm('¿Marcar como Recogida pendiente? OK = Pendiente, Cancel = Finalizada') ? 'Recogida pendiente' : 'Finalizada'; } const payload = { tipo, cliente, efectivo, usdt, comision: com, estado }; await fetch(API_BASE + '/operaciones', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) }); loadOperations(false); loadCaja(); alert('Guardada'); }

window.edit_op = async function(id){ const newname = prompt('Nuevo cliente:'); if(newname===null) return; const newef = prompt('Nuevo efectivo (€):','0'); if(newef===null) return; const newus = prompt('Nuevo USDT:','0'); if(newus===null) return; const newcom = prompt('Nueva comisión:','0'); if(newcom===null) return; const newtipo = prompt('Tipo:','Cash'); if(newtipo===null) return; const newest = prompt('Estado:','Finalizada'); if(newest===null) return; await fetch(API_BASE + `/operaciones/${id}`, { method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ cliente:newname, efectivo: parseFloat(newef||0), usdt: parseFloat(newus||0), comision: parseFloat(newcom||0), tipo:newtipo, estado:newest })}); loadOperations(false); loadCaja(); alert('Editado'); };

window.del_op = async function(id){ if(!confirm('Marcar como eliminada?')) return; await fetch(API_BASE + `/operaciones/${id}`, { method:'DELETE' }); loadOperations(false); loadCaja(); };

async function loadCaja(){ const r = await fetch(API_BASE + '/caja'); const j = await r.json(); const entradas = j.movimientos.filter(m=>m.importe>0); const salidas = j.movimientos.filter(m=>m.importe<0 && m.tipo_mov!=='Reserva'); const reservas = j.movimientos.filter(m=>m.tipo_mov==='Reserva'); const root = document.getElementById('main-content'); root.innerHTML = `<div class="big-total">${(j.saldo||0).toLocaleString('es-ES',{minimumFractionDigits:2})} €</div><div class="caja-sections"><div id="entradas" class="caja-section"><h4>Entradas</h4><div class="list">${entradas.map(i=>`<div class="item"><div>${i.cliente}</div><div>${(i.importe||0).toLocaleString('es-ES',{minimumFractionDigits:2})} €</div></div>`).join('')||'—'}</div></div><div id="salidas" class="caja-section"><h4>Salidas</h4><div class="list">${salidas.map(i=>`<div class="item"><div>${i.cliente}</div><div style="color:var(--red)">${(i.importe||0).toLocaleString('es-ES',{minimumFractionDigits:2})} €</div></div>`).join('')||'—'}</div></div><div id="pendientes" class="caja-section"><h4>Pendientes</h4><div class="list">${reservas.map(i=>`<div class="item"><div>${i.cliente}</div><div style="color:var(--orange)">${(i.importe||0).toLocaleString('es-ES',{minimumFractionDigits:2})} €</div></div>`).join('')||'—'}</div></div></div>`; }

function loadConv(){ document.getElementById('main-content').innerHTML = `<div><h3>Conversor € ↔ $ (USDT)</h3><input id="conv-amount" placeholder="Cantidad" type="number"/><div style="margin-top:8px"><button class="capsule primary" id="conv-do">Convertir</button> <button class="capsule" id="open-xe">Abrir XE</button></div><div id="conv-result" style="margin-top:12px;font-weight:700"></div></div>`; document.getElementById('conv-do').addEventListener('click', async ()=>{ const amount = parseFloat(document.getElementById('conv-amount').value||1); try{ const r = await fetch(API_BASE + `/convert?base=EUR&target=USD&amount=${amount}`); const j = await r.json(); if(j.ok) document.getElementById('conv-result').textContent = `${amount} EUR = ${j.result.toFixed(2)} USD (tasa ${j.rate.toFixed(4)})`; else document.getElementById('conv-result').textContent = 'Error tasa'; }catch(e){ document.getElementById('conv-result').textContent = 'Error conexión'; } }); document.getElementById('open-xe').addEventListener('click', ()=> window.open('https://www.xe.com/es-es/currencyconverter/','_blank')); }

function loadAjustes(){ document.getElementById('main-content').innerHTML = `<div><h3>Ajustes</h3><div style="margin-top:8px"><button class="capsule" id="btn-export">Exportar backup</button> <button class="capsule" id="btn-import">Importar backup</button><input id="file-import" type="file" style="display:none"/></div></div>`; document.getElementById('btn-export').addEventListener('click', async ()=>{ const r=await fetch(API_BASE+'/backup/export'); const j=await r.json(); const blob=new Blob([JSON.stringify(j,null,2)],{type:'application/json'}); const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download='backup.json'; a.click(); }); document.getElementById('btn-import').addEventListener('click', ()=> document.getElementById('file-import').click()); document.getElementById('file-import').addEventListener('change', async (e)=>{ const f=e.target.files[0]; if(!f) return; const fd=new FormData(); fd.append('file', f); const r=await fetch(API_BASE+'/backup/import',{method:'POST',body:fd}); const j=await r.json(); if(j.ok){ alert('Importado'); loadOperations(false); loadCaja(); } else alert('Error import'); }); }
