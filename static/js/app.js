document.addEventListener("DOMContentLoaded", function () {
  iniciarPanelNotificaciones();
  iniciarBarrasProgreso();
  iniciarConfirmaciones();
});

function mostrarModal(id) {
  const modal = document.getElementById(id);
  if (!modal) return;
  modal.classList.remove("hidden");
}

function ocultarModal(id) {
  const modal = document.getElementById(id);
  if (!modal) return;
  modal.classList.add("hidden");
}

function iniciarPanelNotificaciones() {
  const boton = document.getElementById("btn-notificaciones");
  const panel = document.getElementById("notif-panel");
  const fondo = document.getElementById("notif-backdrop");
  const cerrar = document.getElementById("btn-cerrar-notificaciones");

  if (!boton || !panel || !fondo) return;

  boton.addEventListener("click", function () {
    const abrir = panel.classList.contains("hidden");
    panel.classList.toggle("hidden", !abrir);
    fondo.classList.toggle("hidden", !abrir);
  });

  fondo.addEventListener("click", cerrarPanelNotificaciones);
  if (cerrar) cerrar.addEventListener("click", cerrarPanelNotificaciones);
}

function cerrarPanelNotificaciones() {
  const panel = document.getElementById("notif-panel");
  const fondo = document.getElementById("notif-backdrop");
  if (panel) panel.classList.add("hidden");
  if (fondo) fondo.classList.add("hidden");
}

function iniciarBarrasProgreso() {
  document.querySelectorAll("[data-progress-bar]").forEach(function (barra) {
    barra.style.width = (barra.dataset.progress || "0") + "%";
  });
}

function iniciarConfirmaciones() {
  document.addEventListener("submit", function (e) {
    if (e.defaultPrevented) return;
    const form = e.target;
    if (!form || !form.dataset || !form.dataset.confirm) return;
    if (form.dataset.confirmado === "true") {
      delete form.dataset.confirmado;
      return;
    }

    e.preventDefault();
    mostrarConfirmacion(form.dataset.confirm, function () {
      form.dataset.confirmado = "true";
      HTMLFormElement.prototype.submit.call(form);
    });
  });

  document.addEventListener("click", function (e) {
    const boton = e.target.closest("[data-confirm-click]");
    if (!boton) return;

    if (boton.dataset.confirmadoClick === "true") {
      delete boton.dataset.confirmadoClick;
      return;
    }

    e.preventDefault();
    e.stopImmediatePropagation();

    mostrarConfirmacion(boton.dataset.confirmClick, function () {
      boton.dataset.confirmadoClick = "true";
      boton.click();
    });
  }, true);
}

function obtenerModalConfirmacion() {
  let modal = document.getElementById("confirmacion-modal");
  if (modal) return modal;

  modal = document.createElement("div");
  modal.id = "confirmacion-modal";
  modal.className = "confirmacion-fondo hidden";
  modal.innerHTML = [
    '<div class="confirmacion-caja" role="dialog" aria-modal="true" aria-labelledby="confirmacion-titulo">',
    '  <div class="confirmacion-barra"></div>',
    '  <div class="confirmacion-cuerpo">',
    '    <div class="confirmacion-icono">',
    '      <span class="material-symbols-outlined">help</span>',
    '    </div>',
    '    <div>',
    '      <p class="modal-subtitulo">Confirmación</p>',
    '      <h3 id="confirmacion-titulo" class="modal-titulo">Confirmar acción</h3>',
    '      <p id="confirmacion-mensaje" class="confirmacion-mensaje"></p>',
    '    </div>',
    '    <div class="confirmacion-acciones">',
    '      <button type="button" class="boton boton-secundario" data-confirm-cancelar>Cancelar</button>',
    '      <button type="button" class="boton boton-primario" data-confirm-aceptar>Aceptar</button>',
    '    </div>',
    '  </div>',
    '</div>'
  ].join("");

  document.body.appendChild(modal);
  return modal;
}

function mostrarConfirmacion(mensaje, alAceptar) {
  const modal = obtenerModalConfirmacion();
  const texto = modal.querySelector("#confirmacion-mensaje");
  const aceptar = modal.querySelector("[data-confirm-aceptar]");
  const cancelar = modal.querySelector("[data-confirm-cancelar]");

  texto.textContent = mensaje || "¿Desea continuar?";
  modal.classList.remove("hidden");
  aceptar.focus();

  function cerrar() {
    modal.classList.add("hidden");
    aceptar.removeEventListener("click", confirmar);
    cancelar.removeEventListener("click", cerrar);
    modal.removeEventListener("click", cerrarPorFondo);
    document.removeEventListener("keydown", cerrarPorEscape);
  }

  function confirmar() {
    cerrar();
    if (typeof alAceptar === "function") alAceptar();
  }

  function cerrarPorFondo(e) {
    if (e.target === modal) cerrar();
  }

  function cerrarPorEscape(e) {
    if (e.key === "Escape") cerrar();
  }

  aceptar.addEventListener("click", confirmar);
  cancelar.addEventListener("click", cerrar);
  modal.addEventListener("click", cerrarPorFondo);
  document.addEventListener("keydown", cerrarPorEscape);
}

window.mostrarModal = mostrarModal;
window.ocultarModal = ocultarModal;

function mostrarErrorCampo(campo, mensaje) {
  campo.classList.add("campo-error");
  let span = campo.parentElement.querySelector(".error-campo");
  if (!span) {
    span = document.createElement("span");
    span.className = "error-campo";
    campo.parentElement.appendChild(span);
  }
  span.textContent = mensaje;
}

function limpiarErrorCampo(campo) {
  campo.classList.remove("campo-error");
  const span = campo.parentElement.querySelector(".error-campo");
  if (span) span.remove();
}

function limpiarErroresFormulario(form) {
  form.querySelectorAll(".campo-error").forEach(function (c) { c.classList.remove("campo-error"); });
  form.querySelectorAll(".error-campo").forEach(function (s) { s.remove(); });
}

function validarDNIPeru(dni) {
  return /^\d{8}$/.test(dni.trim());
}

function validarNombrePeru(nombre) {
  return /^[A-Za-záéíóúÁÉÍÓÚüÜñÑ\s.\-]{3,100}$/.test(nombre.trim());
}

function validarTelefonoPeru(tel) {
  if (!tel.trim()) return true;
  return /^9\d{8}$/.test(tel.trim());
}

function validarCorreo(correo) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(correo.trim());
}

window.mostrarErrorCampo = mostrarErrorCampo;
window.limpiarErrorCampo = limpiarErrorCampo;
window.limpiarErroresFormulario = limpiarErroresFormulario;
window.validarDNIPeru = validarDNIPeru;
window.validarNombrePeru = validarNombrePeru;
window.validarTelefonoPeru = validarTelefonoPeru;
window.validarCorreo = validarCorreo;
