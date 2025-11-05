# backend/app.py
import os, json, time, pathlib, requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

BASE_DIR = pathlib.Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / "data"
FRONT_DIR = BASE_DIR.parent / "frontend"

DATA_DIR.mkdir(parents=True, exist_ok=True)

USERS_FILE = DATA_DIR / "users.json"
OPS_FILE = DATA_DIR / "operaciones.json"
CAJA_FILE = DATA_DIR / "caja.json"

# Inicializar archivos si no existen
if not USERS_FILE.exists():
    users_init = [
        {"username": "dani", "pin": "1319", "admin": True},
        {"username": "camilo", "pin": "3852", "admin": True}
    ]
    USERS_FILE.write_text(json.dumps(users_init, ensure_ascii=False, indent=2), encoding='utf-8')

for p in (OPS_FILE, CAJA_FILE):
    if not p.exists():
        if p == OPS_FILE:
            p.write_text("[]", encoding='utf-8')
        else:
            p.write_text(json.dumps({"movimientos": [], "saldo": 0.0}, ensure_ascii=False, indent=2), encoding='utf-8')

def read_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {} if path==CAJA_FILE else []

def write_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

app = Flask(__name__, static_folder=str(FRONT_DIR), static_url_path="/")
CORS(app)

# --- Static frontend routes ---
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def frontend(path):
    # si archivo existe, lo sirve; si no, index.html
    if path != "" and (FRONT_DIR / path).exists():
        return send_from_directory(str(FRONT_DIR), path)
    return send_from_directory(str(FRONT_DIR), 'index.html')

# --------------------
# Auth
# --------------------
@app.route('/api/login', methods=['POST'])
def api_login():
    body = request.json or {}
    username = (body.get('username') or '').strip().lower()
    pin = (body.get('pin') or '').strip()
    users = read_json(USERS_FILE)
    for u in users:
        if u.get('username') == username and u.get('pin') == pin:
            return jsonify({'ok': True, 'username': username, 'admin': u.get('admin', False)})
    return jsonify({'ok': False, 'msg': 'Usuario o PIN incorrecto'}), 401

# --------------------
# Operaciones
# --------------------
def next_op_id(ops):
    maxn = 0
    for o in ops:
        try:
            n = int(o.get('id', '0'))
            if n > maxn: maxn = n
        except:
            pass
    return f"{maxn+1:03d}"

@app.route('/api/operaciones', methods=['GET', 'POST'])
def api_operaciones():
    if request.method == 'GET':
        return jsonify(read_json(OPS_FILE))
    body = request.json or {}
    ops = read_json(OPS_FILE)
    nid = next_op_id(ops)
    op = {
        "id": nid,
        "fecha": time.strftime("%Y-%m-%d %H:%M:%S"),
        "cliente": body.get('cliente', ''),
        "efectivo": float(body.get('efectivo') or 0),
        "usdt": float(body.get('usdt') or 0),
        "comision": float(body.get('comision') or 0),
        "tipo": body.get('tipo', 'Cash'),
        "estado": body.get('estado', 'Finalizada'),
        "nota": body.get('nota', '')
    }
    ops.insert(0, op)
    write_json(OPS_FILE, ops)
    # actualizar caja
    actualizar_caja_por_op(op, crear=True)
    return jsonify({'ok': True, 'id': nid}), 201

@app.route('/api/operaciones/<op_id>', methods=['PUT', 'DELETE'])
def api_operacion_modify(op_id):
    ops = read_json(OPS_FILE)
    found = None
    for o in ops:
        if str(o.get('id')) == str(op_id):
            found = o
            break
    if not found:
        return jsonify({'ok': False, 'msg': 'No encontrada'}), 404
    if request.method == 'DELETE':
        found['estado'] = 'Eliminada'
        write_json(OPS_FILE, ops)
        # quitar movimientos de caja vinculados
        caja = read_json(CAJA_FILE)
        caja['movimientos'] = [m for m in caja.get('movimientos', []) if str(m.get('operacion_id')) != str(op_id)]
        caja['saldo'] = sum(m.get('importe', 0) for m in caja.get('movimientos', []))
        write_json(CAJA_FILE, caja)
        return jsonify({'ok': True})
    # PUT = editar
    body = request.json or {}
    changed_keys = []
    for k in ('cliente','efectivo','usdt','comision','tipo','estado','nota'):
        if k in body:
            found[k] = body[k]
            changed_keys.append(k)
    write_json(OPS_FILE, ops)
    # refrescar caja para esa operación
    actualizar_caja_por_op(found, crear=False)
    return jsonify({'ok': True})

def actualizar_caja_por_op(op, crear=False):
    """
    Mantiene movimientos en caja con SAME op id.
    Si crear=True -> añade; si crear=False -> elimina movimientos previos y añade según estado actual.
    """
    caja = read_json(CAJA_FILE)
    movs = caja.get('movimientos', [])
    oper_id = str(op.get('id'))
    # eliminar entradas previas para esa operacion
    movs = [m for m in movs if str(m.get('operacion_id')) != oper_id]
    # decidir si añadir
    tipo = op.get('tipo','')
    estado = op.get('estado','Finalizada')
    ef = float(op.get('efectivo') or 0)
    if (estado == 'Finalizada' and ef != 0) or tipo in ('Depósito','Cash'):
        # Entrada positiva
        if ef != 0:
            movs.insert(0, {"operacion_id": oper_id, "cliente": op.get('cliente'), "importe": float(ef), "tipo_mov": "Entrada", "fecha": op.get('fecha'), "nota": tipo})
    elif estado == 'Recogida pendiente':
        # Reserva: negative to subtract from available
        if ef != 0:
            movs.insert(0, {"operacion_id": oper_id, "cliente": op.get('cliente'), "importe": -abs(float(ef)), "tipo_mov": "Reserva", "fecha": op.get('fecha'), "nota": tipo})
    # else: El estado Eliminada no añade
    caja['movimientos'] = movs
    caja['saldo'] = sum(m.get('importe', 0) for m in movs)
    write_json(CAJA_FILE, caja)

# --------------------
# Caja: obtener movimientos y saldo
# --------------------
@app.route('/api/caja', methods=['GET'])
def api_caja():
    return jsonify(read_json(CAJA_FILE))

# --------------------
# Backup export/import
# --------------------
@app.route('/api/backup/export', methods=['GET'])
def api_export():
    return jsonify({'operaciones': read_json(OPS_FILE), 'caja': read_json(CAJA_FILE)})

@app.route('/api/backup/import', methods=['POST'])
def api_import():
    if 'file' not in request.files:
        return jsonify({'ok': False, 'msg': 'No file'}), 400
    f = request.files['file']
    try:
        payload = json.load(f)
        # validar estructura básica
        write_json(OPS_FILE, payload.get('operaciones', []))
        write_json(CAJA_FILE, payload.get('caja', {"movimientos": [], "saldo": 0.0}))
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'msg': str(e)}), 500

# --------------------
# Conversor (exchangerate.host)
# --------------------
@app.route('/api/convert', methods=['GET'])
def api_convert():
    base = request.args.get('base','EUR')
    target = request.args.get('target','USD')
    amount = float(request.args.get('amount','1') or 1)
    try:
        url = f'https://api.exchangerate.host/convert?from={base}&to={target}&amount={amount}'
        r = requests.get(url, timeout=6)
        j = r.json()
        return jsonify({'ok': True, 'rate': j.get('info',{}).get('rate'), 'result': j.get('result')})
    except Exception as e:
        return jsonify({'ok': False, 'msg': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
def static_proxy(path):
    if path=='' or path=='index.html':
        return send_from_directory(app.static_folder, 'index.html')
    full = os.path.join(app.static_folder, path)
    if os.path.exists(full):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/login', methods=['POST'])
def api_login():
    body = request.json or {}
    user = body.get('username','').strip()
    pin = body.get('pin','').strip()
    users = read_json(USERS_FILE)
    for u in users:
        if u.get('username')==user and u.get('password')==pin:
            return jsonify({'ok': True, 'username': user, 'admin': u.get('admin', False)})
    return jsonify({'ok': False, 'msg':'Usuario o PIN incorrecto'}), 401

@app.route('/api/operaciones', methods=['GET','POST'])
def api_operaciones():
    if request.method=='GET':
        return jsonify(read_json(OPS_FILE))
    op = request.json or {}
    ops = read_json(OPS_FILE)
    max_id = 0
    for o in ops:
        try:
            nid = int(o.get('id',0))
            if nid > max_id: max_id = nid
        except: pass
    new_id = f"{max_id+1:03d}"
    op['id'] = new_id
    op.setdefault('fecha', time.strftime('%Y-%m-%d %H:%M:%S'))
    ops.insert(0, op)
    write_json(OPS_FILE, ops)
    # update caja
    caja = read_json(CAJA_FILE)
    movs = caja.get('movimientos', [])
    tipo = op.get('tipo','')
    estado = op.get('estado','Finalizada')
    efectivo = float(op.get('efectivo') or 0)
    oper_id = op.get('id')
    if estado == 'Finalizada' or tipo=='Depósito' or tipo=='Cash':
        if efectivo>0:
            movs.insert(0, {'operacion_id': oper_id, 'cliente': op.get('cliente'), 'importe': float(efectivo), 'tipo_mov':'Entrada', 'fecha': op.get('fecha'), 'nota': tipo})
    elif estado=='Recogida pendiente':
        if efectivo>0:
            movs.insert(0, {'operacion_id': oper_id, 'cliente': op.get('cliente'), 'importe': -abs(float(efectivo)), 'tipo_mov':'Reserva', 'fecha': op.get('fecha'), 'nota': tipo})
    caja['movimientos'] = movs
    caja['saldo'] = sum(m.get('importe',0) for m in movs)
    write_json(CAJA_FILE, caja)
    return jsonify({'ok': True, 'id': new_id}), 201

@app.route('/api/operaciones/<op_id>', methods=['PUT','DELETE'])
def api_operacion_modify(op_id):
    ops = read_json(OPS_FILE)
    found = None
    for o in ops:
        if str(o.get('id'))==str(op_id):
            found = o
            break
    if not found:
        return jsonify({'ok': False, 'msg':'No encontrada'}), 404
    if request.method=='DELETE':
        found['estado'] = 'Eliminada'
        write_json(OPS_FILE, ops)
        caja = read_json(CAJA_FILE)
        caja['movimientos'] = [m for m in caja.get('movimientos',[]) if not (str(m.get('operacion_id'))==str(op_id))]
        caja['saldo'] = sum(m.get('importe',0) for m in caja['movimientos'])
        write_json(CAJA_FILE, caja)
        return jsonify({'ok': True})
    body = request.json or {}
    for k in ('cliente','efectivo','usdt','comision','estado','tipo'):
        if k in body:
            found[k] = body[k]
    write_json(OPS_FILE, ops)
    # refresh caja
    caja = read_json(CAJA_FILE)
    caja['movimientos'] = [m for m in caja.get('movimientos',[]) if str(m.get('operacion_id'))!=str(found.get('id'))]
    if found.get('estado')=='Finalizada' or found.get('tipo')=='Depósito' or found.get('tipo')=='Cash':
        if float(found.get('efectivo',0))>0:
            caja['movimientos'].insert(0, {'operacion_id': found.get('id'), 'cliente': found.get('cliente'), 'importe': float(found.get('efectivo')), 'tipo_mov':'Entrada', 'fecha': found.get('fecha'), 'nota': found.get('tipo')})
    elif found.get('estado')=='Recogida pendiente':
        if float(found.get('efectivo',0))>0:
            caja['movimientos'].insert(0, {'operacion_id': found.get('id'), 'cliente': found.get('cliente'), 'importe': -abs(float(found.get('efectivo'))), 'tipo_mov':'Reserva', 'fecha': found.get('fecha'), 'nota': found.get('tipo')})
    caja['saldo'] = sum(m.get('importe',0) for m in caja['movimientos'])
    write_json(CAJA_FILE, caja)
    return jsonify({'ok': True})

@app.route('/api/caja', methods=['GET'])
def api_caja():
    caja = read_json(CAJA_FILE)
    return jsonify(caja)

@app.route('/api/backup/export', methods=['GET'])
def api_backup_export():
    return jsonify({'operaciones': read_json(OPS_FILE), 'caja': read_json(CAJA_FILE)})

@app.route('/api/backup/import', methods=['POST'])
def api_backup_import():
    if 'file' not in request.files:
        return jsonify({'ok': False, 'msg': 'No file'}), 400
    f = request.files['file']
    try:
        payload = json.load(f)
        write_json(OPS_FILE, payload.get('operaciones', []))
        write_json(CAJA_FILE, payload.get('caja', {'movimientos': [], 'saldo': 0.0}))
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'msg': str(e)}), 500

@app.route('/api/convert', methods=['GET'])
def api_convert():
    base = request.args.get('base', 'EUR')
    target = request.args.get('target', 'USD')
    amount = request.args.get('amount', '1')
    try:
        url = f'https://api.exchangerate.host/convert?from={base}&to={target}&amount={amount}'
        r = requests.get(url, timeout=6)
        j = r.json()
        return jsonify({'ok': True, 'rate': j.get('info',{}).get('rate'), 'result': j.get('result')})
    except Exception as e:
        return jsonify({'ok': False, 'msg': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
