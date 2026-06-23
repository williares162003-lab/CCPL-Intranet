document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".btn-continuar").forEach(function (boton) {
    boton.addEventListener("click", function () {
      mostrarCurso(boton);
    });
  });

  const modal = document.getElementById("modal-curso");
  if (modal) {
    modal.addEventListener("click", function (e) {
      if (e.target === modal) cerrarModal();
    });
  }
});

function mostrarCurso(boton) {
  const progreso = parseInt(boton.dataset.progress || "0", 10);
  const pagado = boton.dataset.badge === "Pagado";
  const completo = progreso === 100;
  const certificado = boton.dataset.certificate || "";
  const inscripcionId = boton.dataset.inscriptionId || "";
  let materiales = [];

  try {
    materiales = JSON.parse(boton.dataset.materials || "[]");
  } catch (e) {
    materiales = [];
  }

  document.getElementById("modal-titulo").textContent = boton.dataset.title || "";
  document.getElementById("modal-categoria").textContent = boton.dataset.category || "";
  document.getElementById("modal-fecha").textContent = boton.dataset.date || "";
  document.getElementById("modal-ponente").textContent = "Ponente: " + (boton.dataset.speaker || "-");
  document.getElementById("modal-detalles-curso").textContent =
    (boton.dataset.modality || "-") + " | " +
    (boton.dataset.hours || "0") + " horas | S/ " +
    parseFloat(boton.dataset.amount || "0").toFixed(2);
  document.getElementById("modal-progress-txt").textContent = progreso + "%";

  const barra = document.getElementById("modal-progress-bar");
  barra.style.width = progreso + "%";
  barra.className = "barra-progreso-valor " + (completo ? "barra-verde" : "barra-azul");

  document.getElementById("modal-badge-wrap").innerHTML =
    pagado
      ? '<span class="estado-badge estado-pagado">Pago confirmado</span>'
      : '<span class="estado-badge estado-pendiente">Pago pendiente</span>';

  document.getElementById("modal-descripcion-curso").textContent =
    boton.dataset.description || "Aun no hay descripcion registrada.";
  renderizarMateriales(materiales);

  const acciones = document.getElementById("modal-acciones");
  if (!pagado) {
    acciones.innerHTML = '<a href="/estado-cuenta" class="boton boton-primario boton-ancho"><span class="material-symbols-outlined">payments</span> Ir a pagar</a>';
  } else if (completo && certificado) {
    acciones.innerHTML =
      '<a href="/educacion-continua/' + inscripcionId + '/certificado" class="boton boton-primario boton-ancho">' +
      '<span class="material-symbols-outlined">workspace_premium</span> Ver certificado</a>';
  } else if (completo) {
    acciones.innerHTML = '<button onclick="cerrarModal()" class="boton boton-secundario boton-ancho"><span class="material-symbols-outlined">hourglass_empty</span> Certificado pendiente</button>';
  } else {
    acciones.innerHTML = '<button onclick="cerrarModal()" class="boton boton-secundario boton-ancho"><span class="material-symbols-outlined">pending_actions</span> Progreso pendiente del ponente</button>';
  }
  acciones.innerHTML += '<button onclick="cerrarModal()" class="boton boton-secundario boton-ancho">Cerrar</button>';

  mostrarModal("modal-curso");
}

function renderizarMateriales(materiales) {
  const contenedor = document.getElementById("modal-materiales-curso");
  contenedor.innerHTML = "";

  if (!materiales.length) {
    const vacio = document.createElement("p");
    vacio.className = "texto-pequeno";
    vacio.textContent = "Aun no hay materiales publicados para este curso.";
    contenedor.appendChild(vacio);
    return;
  }

  materiales.forEach(function (material) {
    contenedor.appendChild(crearMaterialItem(material));
  });
}

function crearMaterialItem(material) {
  const item = document.createElement("article");
  item.className = "curso-material-item";

  const titulo = document.createElement("p");
  titulo.className = "texto-principal";
  titulo.textContent = material.title || "Material";
  item.appendChild(titulo);

  const descripcion = document.createElement("p");
  descripcion.className = "texto-secundario";
  descripcion.textContent = material.description || "";
  item.appendChild(descripcion);

  if (material.link) {
    const enlace = document.createElement("a");
    enlace.className = "boton-link";
    enlace.href = material.link;
    enlace.target = "_blank";
    enlace.rel = "noopener";
    enlace.textContent = "Abrir enlace";
    item.appendChild(enlace);
  }

  if (material.file) {
    const archivo = document.createElement("a");
    archivo.className = "boton-link";
    archivo.href = "/static/" + material.file;
    archivo.target = "_blank";
    archivo.rel = "noopener";
    archivo.textContent = "Ver archivo";
    item.appendChild(archivo);
  }

  return item;
}

function cerrarModal() {
  ocultarModal("modal-curso");
}

window.cerrarModal = cerrarModal;
