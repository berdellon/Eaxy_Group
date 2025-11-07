// ---------- GLOBAL ----------
const API_URL = "/api";
let currentUser = null;

// ---------- LOGIN ----------
async function doLogin() {
    const user = document.getElementById("user").value.trim();
    const pin = document.getElementById("pin").value.trim();

    const res = await fetch(`${API_URL}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user, pin })
    });

    const data = await res.json();

    if (!data.ok) {
        alert("Usuario o PIN incorrecto");
        return;
    }

    currentUser = user;
    loadHome();
}

// ---------- LOAD HOME ----------
function loadHome() {
    fetch("pages/home.html")
        .then(res => res.text())
        .then(html => {
            document.getElementById("app").innerHTML = html;
        });
}

// ---------- OPERACIONES ----------
async function openOperaciones() {
    fetch("pages/operaciones.html")
        .then(res => res.text())
        .then(html => {
            document.getElementById("app").innerHTML = html;
        });
}

// ---------- CAJA FUERTE ----------
async function openCajaFuerte() {
    fetch("pages/caja_fuerte.html")
        .then(res => res.text())
        .then(html => document.getElementById("app").innerHTML = html);
}

// ---------- CONVERSOR ----------
async function openConversor() {
    fetch("pages/conversor.html")
        .then(res => res.text())
        .then(html => document.getElementById("app").innerHTML = html);
}

async function actualizarTasa() {
    const res = await fetch("https://api.exchangerate.host/latest?base=EUR&symbols=USD");
    const json = await res.json();
    window.tasa = json.rates.USD;

    document.getElementById("tasa_actual").innerText =
        `1 EUR = ${window.tasa.toFixed(4)} USD`;
}

function convertirMoneda() {
    const v = parseFloat(document.getElementById("cantidad").value);
    if (!window.tasa) window.tasa = 1.07;

    const res = v * window.tasa;

    document.getElementById("resultado").innerText =
        `${res.toFixed(2)} USD`;
}

function copiarResultado() {
    navigator.clipboard.writeText(document.getElementById("resultado").innerText);
    alert("Copiado ✅");
}

// ---------- AJUSTES ----------
function openAjustes() {
    fetch("pages/ajustes.html")
        .then(res => res.text())
        .then(html => {
            document.getElementById("app").innerHTML = html;
        });
}

// ---------- IMPORTAR / EXPORTAR ----------
async function exportBackup() {
    const res = await fetch(`${API_URL}/export`);
    const data = await res.json();

    const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json"
    });

    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `backup_${Date.now()}.json`;
    a.click();
}

async function importBackup(ev) {
    const file = ev.target.files[0];
    if (!file) return;

    const text = await file.text();
    await fetch(`${API_URL}/import`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: text
    });

    alert("Backup importado correctamente ✅");
}
