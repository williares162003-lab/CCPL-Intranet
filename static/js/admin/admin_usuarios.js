function abrirModalNuevoUsuario() {
  const form = document.querySelector("#modal-nuevo-usuario .formulario");
  if (form) {
    form.reset();
    limpiarErroresFormulario(form);
  }
  mostrarModal("modal-nuevo-usuario");
}

function cerrarModalNuevoUsuario() {
  ocultarModal("modal-nuevo-usuario");
}

function abrirModalEditarUsuario(datos) {
  const form = document.getElementById("form-editar-usuario");
  limpiarErroresFormulario(form);
  form.reset();
  form.action = "/admin/usuarios/" + datos.id + "/editar";

  document.getElementById("edit-usuario-matricula").textContent = datos.matricula || "";
  document.getElementById("edit-usuario-rol").value = datos.rol || "colegiado";
  document.getElementById("edit-usuario-activo").value = datos.activo || "1";

  mostrarModal("modal-editar-usuario");
}

function cerrarModalEditarUsuario() {
  ocultarModal("modal-editar-usuario");
}

function validarUsuarioNuevo(form) {
  limpiarErroresFormulario(form);
  let valido = true;

  const matricula = form.querySelector('[name="matricula"]');
  if (!matricula.value.trim()) {
    mostrarErrorCampo(matricula, "Ingrese usuario o matrícula.");
    valido = false;
  }

  const rol = form.querySelector('[name="rol"]');
  if (!rol.value.trim()) {
    mostrarErrorCampo(rol, "Seleccione un rol.");
    valido = false;
  }

  const password = form.querySelector('[name="password"]');
  if (!password.value.trim()) {
    mostrarErrorCampo(password, "Ingrese una contraseña.");
    valido = false;
  }

  return valido;
}

function validarUsuarioEditar(form) {
  limpiarErroresFormulario(form);
  let valido = true;

  const rol = form.querySelector('[name="rol"]');
  if (!rol.value.trim()) {
    mostrarErrorCampo(rol, "Seleccione un rol.");
    valido = false;
  }

  const activo = form.querySelector('[name="activo"]');
  if (!activo.value.trim()) {
    mostrarErrorCampo(activo, "Seleccione un estado.");
    valido = false;
  }

  return valido;
}

document.addEventListener("DOMContentLoaded", function () {
  ["modal-nuevo-usuario", "modal-editar-usuario"].forEach(function (id) {
    const modal = document.getElementById(id);
    if (!modal) return;
    modal.addEventListener("click", function (e) {
      if (e.target === modal) ocultarModal(id);
    });
  });

  const formNuevo = document.querySelector("[data-usuario-form]");
  if (formNuevo) {
    formNuevo.addEventListener("submit", function (e) {
      if (!validarUsuarioNuevo(formNuevo)) {
        e.preventDefault();
      }
    });
    formNuevo.querySelectorAll(".campo-formulario").forEach(function (campo) {
      campo.addEventListener("input", function () { limpiarErrorCampo(campo); });
      campo.addEventListener("change", function () { limpiarErrorCampo(campo); });
    });
  }

  const formEditar = document.querySelector("[data-usuario-edit-form]");
  if (formEditar) {
    formEditar.addEventListener("submit", function (e) {
      if (!validarUsuarioEditar(formEditar)) {
        e.preventDefault();
      }
    });
    formEditar.querySelectorAll(".campo-formulario").forEach(function (campo) {
      campo.addEventListener("input", function () { limpiarErrorCampo(campo); });
      campo.addEventListener("change", function () { limpiarErrorCampo(campo); });
    });
  }

  document.querySelectorAll("[data-edit-usuario]").forEach(function (boton) {
    boton.addEventListener("click", function () {
      abrirModalEditarUsuario(boton.dataset);
    });
  });
});

window.abrirModalNuevoUsuario = abrirModalNuevoUsuario;
window.cerrarModalNuevoUsuario = cerrarModalNuevoUsuario;
window.abrirModalEditarUsuario = abrirModalEditarUsuario;
window.cerrarModalEditarUsuario = cerrarModalEditarUsuario;
