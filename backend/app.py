from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os, json, time, pathlib, requests

BASE_DIR = pathlib.Path(__file__).parent.resolve()
FRONTEND_DIR = (BASE_DIR.parent / "frontend").resolve()

app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="/")
CORS(app)

DATA_DIR = BASE_DIR / "data"
USERS_FILE = DATA_DIR / "users.json"
OPS_FILE = DATA_DIR / "operaciones.json"
CAJA_FILE = DATA_DIR / "caja.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)
if not USERS_FILE.exists():
    with USERS_FILE.open('w', encoding='utf-8') as f:
        json.dump([{"username":"dani","password":"1319","admin":True},{"username":"camilo","password":"3852","admin":True}], f, ensure_ascii=False, indent=2)
if not OPS_FILE.exists():
    with OPS_FILE.open('w', encoding='utf-8') as f:
        json.dump([], f, ensure_ascii=False, indent=2)
if not CAJA_FILE.exists():
    with CAJA_FILE.open('w', encoding='utf-8') as f:
        json.dump({"movimientos": [], "saldo": 0.0}, f, ensure_ascii=False, indent=2)

def read_json(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def write_json(p, data):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.route('/', defaults={'path':''})
@app.route('/<path:path>')
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
