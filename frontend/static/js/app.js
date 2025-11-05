// frontend/static/js/app.js
const API_BASE = window.location.origin + '/api';
function el(q){return document.querySelector(q);}

async function postJson(url,data){return fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});}

document.addEventListener('DOMContentLoaded', ()=>{
  const btn = document.getElementById('btn-login');
  if(btn){
    btn.addEventListener('click', async ()=>{
      const user = (document.getElementById('login-user').value || '').trim();
      const pin = (document.getElementById('login-pin').value || '').trim();
      const msg = document.getElementById('login-msg'); msg.textContent = '';
      if(!user || !pin){ msg.textContent = 'Introduce usuario y PIN'; return; }
      try{
        const res = await fetch(API_BASE + '/login', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ username: user, pin }) });
        const j = await res.json();
        if(res.ok && j.ok){
          // guardar usuario en sessionStorage y abrir home
          sessionStorage.setItem('user', j.username);
          window.location.href = '/home.html';
        } else {
          msg.textContent = j.msg || 'Credenciales inválidas';
        }
      }catch(e){
        msg.textContent = 'Error de conexión con el servidor';
        console.error(e);
      }
    });
  }

  // if on home page, build menu
  const welcome = document.getElementById('welcome');
  if(welcome){
    const user = sessionStorage.getItem('user') || 'Usuario';
    welcome.textContent = `Bienvenido, ${user}`;
    buildMenu();
    handleHash();
    window.addEventListener('hashchange', handleHash);
  }
});

function buildMenu(){
  const grid = document.getElementById('main-grid');
  if(!grid) return;
  grid.innerHTML = '';
  const specs = [
    ['📋  Operaciones', '#ops'],
    ['💼  Caja Fuerte', '#caja'],
    ['💱  Conversor', '#conv'],
    ['⚙️  Ajustes', '#ajustes'],
    ['📜  Historial', '#hist']
  ];
  specs.forEach(s=>{
    const b = document.createElement('button');
    b.className = 'big capsule';
    b.textContent = s[0];
    b.onclick = ()=> { window.location.hash = s[1]; handleHash(); }
    grid.appendChild(b);
  });
  const out = document.getElementById('logout');
  if(out) out.addEventListener('click', ()=>{ sessionStorage.removeItem('user'); window.location.href = '/'; });
}

async function handleHash(){
  const h = location.hash || '#ops';
  const main = document.getElementById('main-content');
  if(!main) return;
  if(h.startsWith('#ops')) await loadOperations();
  else if(h.startsWith('#caja')) await loadCaja();
  else if(h.startsWith('#conv')) loadConv();
  else if(h.startsWith('#ajustes')) loadAjustes();
  else if(h.startsWith('#hist')) loadHistorial();
}

async function loadOperations(){
  const r = await fetch(API_BASE + '/operaciones'); const ops = await r.json();
  const container = document.getElementById('main-content');
  let html = '<div style="margin-bottom:12px"><button class="capsule primary" onclick="openNewOp()">➕ Nueva operación</button></div>';
  if(ops.length===0) html += '<div class="muted">No hay operaciones</div>';
  else ops.forEach(op=>{
    html += `<div class="op-item"><div><div style="font-weight:700">${op.id} — ${op.cliente}</div><div class="meta">${op.fecha} · ${op.tipo} · ${op.estado}</div></div><div style="text-align:right"><div style="font-weight:700">${(op.efectivo||0).toLocaleString('es-ES',{minimumFractionDigits:2})} €</div><div style="margin-top:8px"><button class="capsule" onclick="edit_op('${op.id}')">✏️</button> <button class="capsule" onclick="del_op('${op.id}')">🗑️</button></div></div></div>`;
  });
  container.innerHTML = html;
}

window.openNewOp = function(){
  const html = `<div class="form"><h3>Nueva operación</h3><select id="op-tipo"><option>Cash</option><option>Envío</option><option>Depósito</option><option>Retirada</option></select><input id="op-cliente" placeholder="Cliente"/><input id="op-efectivo" placeholder="Efectivo €" type="number"/><input id="op-usdt" placeholder="USDT (si aplica)" type="number"/><input id="op-com" placeholder="Comisión" type="number"/><div style="margin-top:8px"><button class="capsule primary" id="op-save">Guardar</button> <button class="capsule" onclick="loadOperations()">Cancelar</button></div></div>`;
  document.getElementById('main-content').insertAdjacentHTML('beforeend', html);
  document.getElementById('op-save').addEventListener('click', saveOp);
};

async function saveOp(){
  const tipo = document.getElementById('op-tipo').value;
  const cliente = document.getElementById('op-cliente').value.trim();
  const efectivo = parseFloat(document.getElementById('op-efectivo').value||0);
  const usdt = parseFloat(document.getElementById('op-usdt').value||0);
  const com = parseFloat(document.getElementById('op-com').value||0);
  if(!cliente){ alert('Introduce cliente'); return; }
  let estado = 'Finalizada';
  if(tipo==='Envío' || tipo==='Retirada'){
    estado = confirm('OK = Pendiente, Cancel = Finalizada') ? 'Recogida pendiente' : 'Finalizada';
  }
  const payload = { tipo, cliente, efectivo, usdt, comision: com, estado };
  await fetch(API_BASE + '/operaciones', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
  loadOperations();
  loadCaja();
  alert('Guardada');
}

window.edit_op = async function(id){
  const newname = prompt('Nuevo cliente:');
  if(newname===null) return;
  const newef = prompt('Nuevo efectivo (€):','0'); if(newef===null) return;
  const newus = prompt('Nuevo USDT:','0'); if(newus===null) return;
  const newcom = prompt('Nueva comisión:','0'); if(newcom===null) return;
  const newtipo = prompt('Tipo:','Cash'); if(newtipo===null) return;
  const newest = prompt('Estado:','Finalizada'); if(newest===null) return;
  await fetch(API_BASE + `/operaciones/${id}`, { method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ cliente:newname, efectivo: parseFloat(newef||0), usdt: parseFloat(newus||0), comision: parseFloat(newcom||0), tipo:newtipo, estado:newest })});
  loadOperations(); loadCaja(); alert('Editado');
};

window.del_op = async function(id){
  if(!confirm('Marcar como eliminada?')) return;
  await fetch(API_BASE + `/operaciones/${id}`, { method:'DELETE' });
  loadOperations(); loadCaja();
};

async function loadCaja(){
  const r = await fetch(API_BASE + '/caja'); const j = await r.json();
  const entradas = j.movimientos.filter(m=>m.importe>0);
  const salidas = j.movimientos.filter(m=>m.importe<0 && m.tipo_mov!=='Reserva');
  const reservas = j.movimientos.filter(m=>m.tipo_mov==='Reserva');
  const root = document.getElementById('main-content');
  root.innerHTML = `<div class="big-total">${(j.saldo||0).toLocaleString('es-ES',{minimumFractionDigits:2})} €</div><div class="caja-sections"><div><h4>Entradas</h4><div>${entradas.map(i=>`<div class="item"> ${i.cliente} — ${(i.importe||0).toLocaleString('es-ES',{minimumFractionDigits:2})} € </div>`).join('')||'—'}</div></div><div><h4>Salidas</h4><div>${salidas.map(i=>`<div class="item"> ${i.cliente} — ${(i.importe||0).toLocaleString('es-ES',{minimumFractionDigits:2})} € </div>`).join('')||'—'}</div></div><div><h4>Pendientes</h4><div>${reservas.map(i=>`<div class="item"> ${i.cliente} — ${(i.importe||0).toLocaleString('es-ES',{minimumFractionDigits:2})} € </div>`).join('')||'—'}</div></div></div>`;
}

function loadConv(){
  document.getElementById('main-content').innerHTML = `<div><h3>Conversor € ↔ $ (USDT)</h3><input id="conv-amount" placeholder="Cantidad" type="number"/><div style="margin-top:8px"><button class="capsule primary" id="conv-do">Convertir</button> <button class="capsule" id="open-xe">Abrir XE</button></div><div id="conv-result" style="margin-top:12px;font-weight:700"></div></div>`;
  document.getElementById('conv-do').addEventListener('click', async ()=>{
    const amount = parseFloat(document.getElementById('conv-amount').value||1);
    try{
      const r = await fetch(API_BASE + `/convert?base=EUR&target=USD&amount=${amount}`);
      const j = await r.json();
      if(j.ok) document.getElementById('conv-result').textContent = `${amount} EUR = ${j.result.toFixed(2)} USD (tasa ${j.rate.toFixed(4)})`;
      else document.getElementById('conv-result').textContent = 'Error tasa';
    }catch(e){
      document.getElementById('conv-result').textContent = 'Error conexión';
    }
  });
  document.getElementById('open-xe').addEventListener('click', ()=> window.open('https://www.xe.com/es-es/currencyconverter/','_blank'));
}

function loadAjustes(){
  document.getElementById('main-content').innerHTML = `<div><h3>Ajustes</h3><div style="margin-top:8px"><button class="capsule" id="btn-export">Exportar backup</button> <button class="capsule" id="btn-import">Importar backup</button></div></div>`;
  document.getElementById('btn-export').addEventListener('click', async ()=>{ const r=await fetch(API_BASE+'/backup/export'); const j=await r.json(); const blob=new Blob([JSON.stringify(j,null,2)],{type:'application/json'}); const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download='backup.json'; a.click(); });
  document.getElementById('btn-import').addEventListener('click', ()=>{ const input = document.createElement('input'); input.type='file'; input.onchange = async (e)=>{ const f=e.target.files[0]; const fd = new FormData(); fd.append('file', f); const r = await fetch(API_BASE + '/backup/import', { method:'POST', body: fd }); const j = await r.json(); alert(j.ok ? 'Importado' : 'Error: '+(j.msg||'')); loadOperations(); loadCaja(); }; input.click(); });
}

async function loadHistorial(){
  const r = await fetch(API_BASE + '/operaciones'); const ops = await r.json();
  const container = document.getElementById('main-content');
  let html = '<h3>Historial completo</h3>';
  if(ops.length===0) html += '<div class="muted">No hay operaciones</div>';
  else ops.forEach(op=>{
    html += `<div class="op-item"><div><div style="font-weight:700">${op.id} — ${op.cliente}</div><div class="meta">${op.fecha} · ${op.tipo} · ${op.estado}</div></div><div><button class="capsule" onclick="restore_op('${op.id}')">Restaurar</button> <button class="capsule" onclick="delete_forever('${op.id}')">Eliminar def.</button></div></div>`;
  });
  container.innerHTML = html;
}

async function restore_op(id){
  // marcar como Finalizada y volver a añadir a caja si procede
  await fetch(API_BASE + `/operaciones/${id}`, { method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ estado: 'Finalizada' })});
  loadHistorial(); loadCaja(); loadOperations();
  alert('Restaurada');
}

async function delete_forever(id){
  if(!confirm('Peligro!! Este registro se eliminará definitivamente')) return;
  // backend no ofrece delete definitivo actualmente -> simulamos eliminándolo del array via import/export or API extension.
  // Aquí llamamos DELETE para marcar eliminada y luego limpiamos del listado de operaciones (cliente lo hará por backup/import).
  await fetch(API_BASE + `/operaciones/${id}`, { method:'DELETE' });
  // y ahora además eliminamos definitivamente del frontend pidiendo al backend que lo borre (si añadimos endpoint)
  // para ahora solo refrescamos
  loadHistorial(); loadCaja(); loadOperations();
  alert('Marcada como eliminada (puedes limpiar con import/export si hace falta)');
}
