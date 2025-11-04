from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import json
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

DATA_FILE = "data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"usuarios": {}, "operaciones": []}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

@app.route("/api/tasa", methods=["GET"])
def get_tasa():
    try:
        res = requests.get("https://api.exchangerate.host/latest?base=EUR&symbols=USD")
        rate = res.json()["rates"]["USD"]
        return jsonify({"tasa": rate})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/operaciones", methods=["GET", "POST", "DELETE"])
def operaciones():
    data = load_data()
    if request.method == "GET":
        return jsonify(data["operaciones"])
    elif request.method == "POST":
        op = request.json
        op["id"] = datetime.now().strftime("%Y%m%d%H%M%S")
        data["operaciones"].append(op)
        save_data(data)
        return jsonify({"status": "ok"})
    elif request.method == "DELETE":
        id_to_delete = request.args.get("id")
        data["operaciones"] = [op for op in data["operaciones"] if op["id"] != id_to_delete]
        save_data(data)
        return jsonify({"status": "deleted"})

@app.route("/api/backup/export", methods=["GET"])
def export_backup():
    data = load_data()
    filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)
    return jsonify({"message": f"Backup guardado como {filename}"})

@app.route("/api/backup/import", methods=["POST"])
def import_backup():
    uploaded = request.files["file"]
    data = json.load(uploaded)
    save_data(data)
    return jsonify({"message": "Backup importado correctamente"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
