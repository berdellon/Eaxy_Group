
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os, json, datetime, requests

app = Flask(__name__)
CORS(app)

DATA_FILE = os.path.join(os.path.dirname(__file__), "data.json")

DEFAULT_DATA = {
    "usuarios": {"Dani": {"pin": "1319", "role": "admin"}, "Camilo": {"pin": "3852", "role": "admin"}},
    "ultimo_usuario": None,
    "operaciones": [],
    "caja_fuerte": []
}

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    save_data(DEFAULT_DATA)
    return DEFAULT_DATA

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data = load_data()

def now_iso():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def parse_float(x):
    try:
        if isinstance(x, str):
            x = x.replace(",", ".").strip()
        return float(x)
    except:
        return 0.0

def next_id():
    ops = data.get("operaciones", [])
    maxn = 0
    for o in ops:
        oid = str(o.get("id", ""))
        if oid.isdigit():
            n = int(oid)
            if n > maxn:
                maxn = n
    return f"{maxn+1:03d}"

@app.post("/api/login")
def api_login():
    body = request.get_json(force=True, silent=True) or {}
    user = (body.get("user") or "").strip()
    pin = (body.get("pin") or "").strip()
    users = data.get("usuarios", {})
    if user in users and users[user].get("pin") == pin:
        data["ultimo_usuario"] = user
        save_data(data)
        return jsonify({"ok": True, "user": user, "role": users[user].get("role", "user")})
    return jsonify({"ok": False, "error": "Credenciales incorrectas"}), 401

@app.get("/api/operaciones")
def api_get_ops():
    return jsonify(data.get("operaciones", []))

@app.post("/api/operaciones")
def api_add_op():
    body = request.get_json(force=True, silent=True) or {}
    tipo = body.get("tipo", "")
    cliente = body.get("cliente", "")
    importe = parse_float(body.get("importe", 0))
    usdt = parse_float(body.get("usdt", 0))
    estado = body.get("estado", "Finalizada")

    oid = next_id()
    op = {
        "id": oid, "cliente": cliente, "importe": importe, "importe_eur": importe,
        "usdt": usdt, "tipo": tipo, "estado": estado, "fecha": now_iso()
    }
    data.setdefault("operaciones", []).append(op)

    # caja fuerte entry mirrors by id
    if estado == "Finalizada":
        data.setdefault("caja_fuerte", []).append({
            "id": oid, "fecha": now_iso(), "cliente": cliente, "importe": importe, "tipo": "Entrada", "nota": tipo
        })
    elif "pendiente" in estado.lower():
        data.setdefault("caja_fuerte", []).append({
            "id": oid, "fecha": now_iso(), "cliente": cliente, "importe": -importe, "tipo": "Reserva", "nota": tipo
        })

    save_data(data)
    return jsonify({"ok": True, "op": op})

@app.put("/api/operaciones/<oid>")
def api_edit_op(oid):
    body = request.get_json(force=True, silent=True) or {}
    changed = False
    for op in data.get("operaciones", []):
        if str(op.get("id")) == str(oid):
            for k in ["cliente","importe","usdt","estado","tipo"]:
                if k in body:
                    if k in ["importe","usdt"]:
                        op[k] = parse_float(body[k])
                        if k == "importe":
                            op["importe_eur"] = op[k]
                    else:
                        op[k] = body[k]
                    changed = True
            for mov in data.get("caja_fuerte", []):
                if str(mov.get("id")) == str(oid):
                    if "pendiente" in op.get("estado","").lower():
                        mov["tipo"] = "Reserva"
                        mov["importe"] = -parse_float(op.get("importe", 0))
                    else:
                        mov["tipo"] = "Entrada"
                        mov["importe"] = parse_float(op.get("importe", 0))
                    mov["cliente"] = op.get("cliente","")
                    mov["nota"] = op.get("tipo","")
            break
    if changed:
        save_data(data)
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "No encontrada"}), 404

@app.delete("/api/operaciones/<oid>")
def api_delete_op(oid):
    for op in data.get("operaciones", []):
        if str(op.get("id")) == str(oid):
            op["estado"] = "Eliminada"
            save_data(data)
            return jsonify({"ok": True})
    return jsonify({"ok": False}), 404

@app.post("/api/historial/<oid>/restore")
def api_restore_op(oid):
    found = None
    for op in data.get("operaciones", []):
        if str(op.get("id")) == str(oid) and op.get("estado")=="Eliminada":
            op["estado"] = "Finalizada"
            found = op
            break
    if not found:
        return jsonify({"ok": False}), 404
    exists = any(str(m.get("id"))==str(oid) for m in data.get("caja_fuerte", []))
    if not exists:
        data.setdefault("caja_fuerte", []).append({
            "id": oid, "fecha": now_iso(), "cliente": found.get("cliente",""), "importe": float(found.get("importe",0)),
            "tipo": "Entrada restaurada", "nota": found.get("tipo","")
        })
    save_data(data)
    return jsonify({"ok": True})

@app.post("/api/historial/<oid>/purge")
def api_purge_op(oid):
    data["operaciones"] = [o for o in data.get("operaciones", []) if str(o.get("id")) != str(oid)]
    data["caja_fuerte"] = [c for c in data.get("caja_fuerte", []) if str(c.get("id")) != str(oid)]
    save_data(data)
    return jsonify({"ok": True})

@app.get("/api/caja")
def api_caja():
    movs = data.get("caja_fuerte", [])
    total = sum([float(m.get("importe",0)) for m in movs])
    entradas = [m for m in movs if float(m.get("importe",0)) >= 0]
    salidas = [m for m in movs if m.get("tipo")=="Salida"]
    reservas = [m for m in movs if m.get("tipo") in ("Reserva","Entrada reservada")]
    return jsonify({"total": total, "movimientos": movs, "entradas": entradas, "salidas": salidas, "reservas": reservas})

@app.post("/api/pendiente/<oid>/completar")
def api_pendiente_completar(oid):
    for op in data.get("operaciones", []):
        if str(op.get("id")) == str(oid):
            op["estado"] = "Recogida completada"
            break
    for m in data.get("caja_fuerte", []):
        if str(m.get("id")) == str(oid) and m.get("tipo")=="Reserva":
            m["tipo"] = "Salida"
            m["importe"] = -abs(float(m.get("importe", 0)))
    save_data(data)
    return jsonify({"ok": True})

@app.get("/api/backup/export")
def api_backup_export():
    return send_file(DATA_FILE, as_attachment=True, download_name="backup.json")

@app.post("/api/backup/import")
def api_backup_import():
    incoming = request.get_json(force=True, silent=True)
    if not incoming and "file" in request.files:
        incoming = json.load(request.files["file"].stream)
    if not isinstance(incoming, dict):
        return jsonify({"ok": False, "error": "Formato inválido"}), 400
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(incoming, f, ensure_ascii=False, indent=2)
    return jsonify({"ok": True})

@app.get("/api/rate")
def api_rate():
    try:
        r = requests.get("https://api.exchangerate.host/latest", params={"base":"EUR","symbols":"USD"}, timeout=6)
        if r.status_code == 200:
            rate = r.json().get("rates", {}).get("USD")
            return jsonify({"ok": True, "rate": rate})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    return jsonify({"ok": False}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
