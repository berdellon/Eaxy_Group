const API_BASE = window.location.origin + '/api';

function el(id){return document.getElementById(id);}
function show(screen){document.querySelectorAll('.screen').forEach(s=>s.classList.add('hidden')); document.getElementById(screen).classList.remove('hidden');}
function setThemeByTime(){
  const hour = new Date().getHours();
  if(hour>=20 || hour<7) document.body.classList.add('dark'); else document.body.classList.remove('dark');
}
setThemeByTime();
window.addEventListener('focus', setThemeByTime);

// login
el('btn-login').addEventListener('click', async ()=>{
  const user = el('login-user').value.trim();
  const pin = el('login-pin').value.trim();
  if(!user || !pin){ el('login-msg').textContent='Introduce usuario y PIN'; return; }
  try{
    const res = await fetch(API_BASE + '/login', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({username:user, pin})});
    const j = await res.json();
    if(res.ok && j.ok){ localStorage.setItem('usuario', user); el('welcome').textContent = 'Bienvenido ' + user; show('home-screen'); load_ops_summary(); }
    else { el('login-msg').textContent = j.msg || 'Login fallido'; }
  }catch(e){ el('login-msg').textContent = 'Error servidor'; }
});

// navigation
document.querySelectorAll('.topbar .back').forEach(b=>b.addEventListener('click', ()=> show('home-screen')));
el('back-home').addEventListener('click', ()=> show('login-screen'));

// main menu buttons
el('btn-ops').addEventListener('click', ()=> { load_operations(); show('ops-screen'); });
el('btn-caja').addEventListener('click', ()=> { load_caja(); show('caja-screen'); });
el('btn-conv').addEventListener('click', ()=> { show('conv-screen'); });
el('btn-ajustes').addEventListener('click', ()=> { show('ajustes-screen'); });

// operations
async function load_operations(){
  try{
    const r = await fetch(API_BASE + '/operaciones');
    const ops = await r.json();
    const out = ops.map(op=>`<div class="op-item"><div><div><strong>${op.id}</strong> ${op.cliente}</div><div class="meta">${op.fecha} — ${op.tipo} — ${op.estado}</div></div><div style="text-align:right"><div>${fmtMoney(op.efectivo)}</div><div style="margin-top:6px"><button onclick="edit_op('${op.id}')">✏️</button> <button onclick="del_op('${op.id}')">🗑️</button></div></div></div>`).join('');
    el('ops-list').innerHTML = out || '<div class="muted">No hay operaciones</div>';
  }catch(e){ console.error(e); }
}

function fmtMoney(n){ n = Number(n)||0; return n.toLocaleString('es-ES',{minimumFractionDigits:2, maximumFractionDigits:2}) + ' €'; }

el('op-save').addEventListener('click', async ()=>{
  const tipo = el('op-tipo').value;
  const cliente = el('op-cliente').value.trim();
  const efectivo = parseFloat(el('op-efectivo').value||0);
  const usdt = parseFloat(el('op-usdt').value||0);
  const com = parseFloat(el('op-com').value||0);
  if(!cliente){ alert('Introduce cliente'); return; }
  let estado = 'Finalizada';
  if(tipo==='Envío' || tipo==='Retirada'){ estado = confirm('Marcar como Pendiente? OK=Pendiente, Cancel=Finalizada') ? 'Recogida pendiente' : 'Finalizada'; }
  const payload = { tipo, cliente, efectivo, usdt, comision: com, estado };
  await fetch(API_BASE + '/operaciones', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
  el('op-cliente').value=''; el('op-efectivo').value=''; el('op-usdt').value=''; el('op-com').value='';
  load_operations(); load_caja(); load_ops_summary();
  alert('Guardada');
});

window.edit_op = async function(id){
  const newname = prompt('Nuevo cliente:');
  if(newname===null) return;
  const newef = prompt('Nuevo efectivo (€):','0');
  const newus = prompt('Nuevo USDT:','0');
  const newcom = prompt('Nueva comisión:','0');
  const newtipo = prompt('Tipo:','Cash');
  const newest = prompt('Estado:','Finalizada');
  await fetch(API_BASE + `/operaciones/${id}`, { method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ cliente:newname, efectivo: parseFloat(newef||0), usdt: parseFloat(newus||0), comision: parseFloat(newcom||0), tipo:newtipo, estado:newest })});
  load_operations(); load_caja(); load_ops_summary(); alert('Editado');
};

window.del_op = async function(id){
  if(!confirm('Marcar como eliminada?')) return;
  await fetch(API_BASE + `/operaciones/${id}`, { method:'DELETE' });
  load_operations(); load_caja(); load_ops_summary();
};

// caja
async function load_caja(){
  try{
    const r = await fetch(API_BASE + '/caja');
    const j = await r.json();
    const entradas = j.movimientos.filter(m=>m.importe>0);
    const salidas = j.movimientos.filter(m=>m.importe<0 && m.tipo_mov!=='Reserva');
    const reservas = j.movimientos.filter(m=>m.tipo_mov==='Reserva');
    el('entradas').querySelector('.list').innerHTML = entradas.map(i=>`<div class="item"><div>${i.cliente}</div><div>${fmtMoney(i.importe)}</div></div>`).join('')||'<div class="item">—</div>';
    el('salidas').querySelector('.list').innerHTML = salidas.map(i=>`<div class="item"><div>${i.cliente}</div><div style="color:var(--red)">${fmtMoney(i.importe)}</div></div>`).join('')||'<div class="item">—</div>';
    el('pendientes').querySelector('.list').innerHTML = reservas.map(i=>`<div class="item"><div>${i.cliente}</div><div style="color:var(--orange)">${fmtMoney(i.importe)}</div></div>`).join('')||'<div class="item">—</div>';
    el('caja-total').textContent = fmtMoney(j.saldo);
  }catch(e){ console.error(e); }
}

// converter
let lastRate = null;
el('conv-update').addEventListener('click', async ()=>{
  const base = el('conv-base').value, target = el('conv-target').value;
  try{
    const r = await fetch(API_BASE + `/convert?base=${base}&target=${target}&amount=1`);
    const j = await r.json();
    if(j.ok){ lastRate = j.rate; alert(`Tasa: 1 ${base} = ${j.rate} ${target}`); }
    else alert('Error tasa');
  }catch(e){ alert('Error tasa'); }
});
el('conv-do').addEventListener('click', async ()=>{
  const amount = parseFloat(el('conv-amount').value||1);
  const base = el('conv-base').value, target = el('conv-target').value;
  try{
    const r = await fetch(API_BASE + `/convert?base=${base}&target=${target}&amount=${amount}`);
    const j = await r.json();
    if(j.ok) el('conv-result').textContent = `${amount} ${base} = ${j.result.toFixed(2)} ${target} (tasa ${j.rate.toFixed(4)})`;
    else el('conv-result').textContent = 'Error';
  }catch(e){ el('conv-result').textContent = 'Error conexión'; }
});
el('conv-copy').addEventListener('click', ()=>{ const t = el('conv-result').textContent || ''; navigator.clipboard.writeText(t); alert('Copiado'); });
el('open-xe').addEventListener('click', ()=> window.open('https://www.xe.com/es-es/currencyconverter/','_blank'));

// backups
el('btn-export').addEventListener('click', async ()=>{
  const r = await fetch(API_BASE + '/backup/export'); const j = await r.json();
  const blob = new Blob([JSON.stringify(j,null,2)], {type:'application/json'}); const url = URL.createObjectURL(blob); const a=document.createElement('a'); a.href=url; a.download=`backup_${Date.now()}.json`; a.click(); URL.revokeObjectURL(url);
});
el('btn-import').addEventListener('click', ()=> el('file-import').click());
el('file-import').addEventListener('change', async (ev)=>{ const f=ev.target.files[0]; if(!f) return; const fd=new FormData(); fd.append('file', f); const r=await fetch(API_BASE+'/backup/import',{method:'POST',body:fd}); const j=await r.json(); if(j.ok){ alert('Importado'); load_operations(); load_caja(); } else alert('Error import'); });

// summary load
async function load_ops_summary(){
  await load_operations(); await load_caja();
}

// initial view
if(localStorage.getItem('usuario')){ el('welcome').textContent='Bienvenido ' + localStorage.getItem('usuario'); show('home-screen'); load_ops_summary(); } else { show('login-screen'); }
