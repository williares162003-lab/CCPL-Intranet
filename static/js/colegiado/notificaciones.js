document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".filter-pill").forEach(function (boton) {
    boton.addEventListener("click", function () {
      document.querySelectorAll(".filter-pill").forEach(function (item) {
        item.classList.remove("active");
      });

      boton.classList.add("active");
      aplicarFiltro(boton.dataset.filter || "all");
    });
  });

  aplicarFiltro("all");
  actualizarResumen();
});

function obtenerItems() {
  return Array.from(document.querySelectorAll("#notif-list li"));
}

function contarNoLeidas() {
  return obtenerItems().filter(function (item) {
    return item.dataset.read === "false";
  }).length;
}

function actualizarResumen() {
  const total = obtenerItems().length;
  const noLeidas = contarNoLeidas();
  const resumen = document.getElementById("summary-text");
  const boton = document.getElementById("btn-mark-all");
  const badge = document.getElementById("notif-badge");
  const panelBadge = document.getElementById("panel-badge");

  if (resumen) resumen.textContent = total + " notificaciones en total - " + noLeidas + " sin leer";
  if (boton) boton.disabled = noLeidas === 0;

  if (badge) {
    badge.textContent = noLeidas > 9 ? "9+" : noLeidas;
    badge.classList.toggle("hidden", noLeidas === 0);
  }

  if (panelBadge) {
    panelBadge.textContent = noLeidas;
    panelBadge.classList.toggle("hidden", noLeidas === 0);
  }
}

function aplicarFiltro(tipo) {
  let visibles = 0;

  obtenerItems().forEach(function (item) {
    const mostrar = tipo === "all" || item.dataset.type === tipo;
    item.classList.toggle("hidden", !mostrar);
    if (mostrar) visibles++;
  });

  const contador = document.getElementById("filter-count");
  const vacio = document.getElementById("empty-state");
  if (contador) contador.textContent = visibles === 0 ? "Sin resultados" : "Mostrando " + visibles;
  if (vacio) vacio.classList.toggle("show", visibles === 0);
}

async function markRead(id) {
  const item = document.querySelector('#notif-list li[data-id="' + id + '"]');
  if (!item) return;

  item.dataset.read = "true";
  item.classList.remove("unread");
  const punto = item.querySelector(".unread-dot");
  const estado = item.querySelector("[data-read-status]");
  const boton = item.querySelector("[data-mark-read]");

  if (punto) punto.remove();
  if (estado) estado.textContent = "Leido";
  if (boton) boton.remove();

  const datos = new FormData();
  datos.append("id", id);
  await fetch("/notificaciones/mark-read", { method: "POST", body: datos });
  actualizarResumen();
}

function markAllRead() {
  obtenerItems().forEach(function (item) {
    if (item.dataset.read === "false") markRead(item.dataset.id);
  });
}

async function clearRead() {
  await fetch("/notificaciones/clear-read", { method: "POST" });

  obtenerItems().forEach(function (item) {
    if (item.dataset.read === "true") item.remove();
  });

  const activo = document.querySelector(".filter-pill.active");
  aplicarFiltro(activo ? activo.dataset.filter : "all");
  actualizarResumen();
}

window.markRead = markRead;
window.markAllRead = markAllRead;
window.clearRead = clearRead;
