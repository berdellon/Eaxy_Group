from flask import Flask, jsonify, request, send_from_directory
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

# ensure data files exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
for p, default in ((USERS_FILE, [{"username":"dani","password":"1319"},{"username":"camilo","password":"3852"}]),
                  (OPS_FILE, []),
                  (CAJA_FILE, {"movimientos": [], "saldo": 0.0})):
    if not p.exists():
        with p.open("w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=2)

def read_json(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def write_json(p, data):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Serve frontend
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def static_proxy(path):
    if path == "" or path == "index.html":
        return send_from_directory(app.static_folder, "index.html")
    full = os.path.join(app.static_folder, path)
    if os.path.exists(full):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")

# API: login
@app.route("/api/login", methods=["POST"])
def api_login():
    body = request.json or {}
    user = body.get("username","").strip()
    pin = body.get("pin","").strip()
    users = read_json(USERS_FILE)
    for u in users:
        if u.get("username")==user and u.get("password")==pin:
            return jsonify({"ok": True, "username": user})
    return jsonify({"ok": False, "msg":"Usuario o PIN incorrecto"}), 401

# API: operaciones
@app.route("/api/operaciones", methods=["GET","POST"])
def api_operaciones():
    if request.method == "GET":
        return jsonify(read_json(OPS_FILE))
    else:
        op = request.json or {}
        ops = read_json(OPS_FILE)
        # assign sequential id as string 001...
        max_id = 0
        for o in ops:
            try:
                nid = int(o.get("id",0))
                if nid > max_id: max_id = nid
            except: pass
        new_id = f"{max_id+1:03d}"
        op["id"] = new_id
        op.setdefault("fecha", time.strftime("%Y-%m-%d %H:%M:%S"))
        ops.insert(0, op)
        write_json(OPS_FILE, ops)
        # update caja if needed
        update_caja_for_new_op(op)
        return jsonify({"ok": True, "id": new_id}), 201

@app.route("/api/operaciones/<op_id>", methods=["PUT","DELETE"])
def api_operacion_modify(op_id):
    ops = read_json(OPS_FILE)
    found = None
    for o in ops:
        if str(o.get("id"))==str(op_id):
            found = o
            break
    if not found:
        return jsonify({"ok": False, "msg":"No encontrada"}), 404
    if request.method=="DELETE":
        # mark as Eliminada
        found["estado"] = "Eliminada"
        write_json(OPS_FILE, ops)
        # remove related caja movs
        caja = read_json(CAJA_FILE)
        caja["movimientos"] = [m for m in caja.get("movimientos",[]) if str(m.get("operacion_id"))!=str(op_id)]
        # recompute saldo
        caja["saldo"] = sum(m.get("importe",0) for m in caja["movimientos"])
        write_json(CAJA_FILE, caja)
        return jsonify({"ok": True})
    else:
        body = request.json or {}
        # update fields
        for k in ("cliente","efectivo","usdt","comision","estado","tipo"):
            if k in body:
                found[k] = body[k]
        write_json(OPS_FILE, ops)
        # refresh caja entries for this op
        refresh_caja_for_operacion(found)
        return jsonify({"ok": True})

def update_caja_for_new_op(op):
    caja = read_json(CAJA_FILE)
    movs = caja.get("movimientos", [])
    tipo = op.get("tipo","")
    estado = op.get("estado","Finalizada")
    efectivo = float(op.get("efectivo") or 0)
    oper_id = op.get("id")
    if estado == "Finalizada" or tipo=="Depósito" or tipo=="Cash":
        if efectivo>0:
            movs.insert(0, {"operacion_id": oper_id, "cliente": op.get("cliente"), "importe": float(efectivo), "tipo_mov":"Entrada", "fecha": op.get("fecha"), "nota": tipo})
    elif estado=="Recogida pendiente":
        if efectivo>0:
            movs.insert(0, {"operacion_id": oper_id, "cliente": op.get("cliente"), "importe": -abs(float(efectivo)), "tipo_mov":"Reserva", "fecha": op.get("fecha"), "nota": tipo})
    caja["movimientos"] = movs
    caja["saldo"] = sum(m.get("importe",0) for m in movs)
    write_json(CAJA_FILE, caja)

def refresh_caja_for_operacion(op):
    # remove previous movs for this op and recreate according to current op state
    caja = read_json(CAJA_FILE)
    movs = [m for m in caja.get("movimientos",[]) if str(m.get("operacion_id"))!=str(op.get("id"))]
    caja["movimientos"] = movs
    write_json(CAJA_FILE, caja)
    # recreate if needed
    update_caja_for_new_op(op)

# API: caja
@app.route("/api/caja", methods=["GET"])
def api_caja():
    caja = read_json(CAJA_FILE)
    return jsonify(caja)

# API: backup export/import
@app.route("/api/backup/export", methods=["GET"])
def api_backup_export():
    return jsonify({"operaciones": read_json(OPS_FILE), "caja": read_json(CAJA_FILE)})

@app.route("/api/backup/import", methods=["POST"])
def api_backup_import():
    if "file" not in request.files:
        return jsonify({"ok": False, "msg": "No file"}), 400
    f = request.files["file"]
    try:
        payload = json.load(f)
        write_json(OPS_FILE, payload.get("operaciones", []))
        write_json(CAJA_FILE, payload.get("caja", {"movimientos": [], "saldo": 0.0}))
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500

# API: convert EUR<->USD using exchangerate.host
@app.route("/api/convert", methods=["GET"])
def api_convert():
    base = request.args.get("base", "EUR")
    target = request.args.get("target", "USD")
    amount = request.args.get("amount", "1")
    try:
        url = f"https://api.exchangerate.host/convert?from={base}&to={target}&amount={amount}"
        r = requests.get(url, timeout=6)
        j = r.json()
        return jsonify({"ok": True, "rate": j.get("info",{}).get("rate"), "result": j.get("result")})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
