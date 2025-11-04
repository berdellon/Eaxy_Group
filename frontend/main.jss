const baseURL = "https://tu-render-url.onrender.com/api";

document.getElementById("entrar").onclick = () => {
  const usuario = document.getElementById("usuario").value;
  if (usuario) {
    document.getElementById("login").classList.add("hidden");
    document.getElementById("home").classList.remove("hidden");
    document.getElementById("bienvenida").innerText = `Hola, ${usuario}`;
  }
};

document.querySelectorAll(".volver").forEach(btn => {
  btn.onclick = () => {
    document.querySelectorAll("section").forEach(s => s.classList.add("hidden"));
    document.getElementById("home").classList.remove("hidden");
  };
});

document.getElementById("btn-conversor").onclick = () => mostrar("conversor");
document.getElementById("btn-caja").onclick = () => mostrar("caja");
document.getElementById("btn-ajustes").onclick = () => mostrar("ajustes");

function mostrar(id) {
  document.querySelectorAll("section").forEach(s => s.classList.add("hidden"));
  document.getElementById(id).classList.remove("hidden");
}

// CONVERSOR
document.getElementById("actualizar-tasa").onclick = async () => {
  const r = await fetch(`${baseURL}/tasa`);
  const data = await r.json();
  window.tasa = data.tasa;
  alert(`Tasa actual: 1 EUR = ${data.tasa.toFixed(3)} USD`);
};

document.getElementById("convertir").onclick = () => {
  const monto = parseFloat(document.getElementById("monto").value);
  const dir = document.getElementById("direccion").value;
  if (!window.tasa) return alert("Primero actualiza la tasa.");
  let resultado = dir === "EURtoUSD" ? monto * window.tasa : monto / window.tasa;
  document.getElementById("resultado").innerText = `Resultado: ${resultado.toFixed(2)}`;
};

// AJUSTES - BACKUP
document.getElementById("exportar").onclick = async () => {
  const r = await fetch(`${baseURL}/backup/export`);
  const data = await r.json();
  alert(data.message);
};

document.getElementById("btn-importar").onclick = () => {
  document.getElementById("importar").click();
};

document.getElementById("importar").onchange = async (e) => {
  const file = e.target.files[0];
  const formData = new FormData();
  formData.append("file", file);
  const r = await fetch(`${baseURL}/backup/import`, { method: "POST", body: formData });
  const data = await r.json();
  alert(data.message);
};
