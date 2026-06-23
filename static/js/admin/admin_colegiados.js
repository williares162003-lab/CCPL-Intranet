function abrirModalNuevo() {
  const form = document.querySelector("#modal-nuevo .formulario");
  if (form) {
    form.reset();
    limpiarErroresFormulario(form);
  }
  mostrarModal("modal-nuevo");
}

function cerrarModalNuevo() {
  ocultarModal("modal-nuevo");
}

function abrirModalEditar(id, nombre, especialidadId, direccion, correo, telefono, epc, vigencia, fechaColegiatura) {
  const form = document.getElementById("form-editar");
  limpiarErroresFormulario(form);
  form.action = "/admin/colegiados/" + id + "/editar";
  document.getElementById("edit-nombre").value = nombre || "";
  document.getElementById("edit-especialidad-id").value = especialidadId || "";
  document.getElementById("edit-direccion").value = direccion || "";
  document.getElementById("edit-correo").value = correo || "";
  document.getElementById("edit-telefono").value = telefono || "";
  const fechaInput = document.getElementById("edit-fecha-colegiatura");
  if (fechaInput) fechaInput.value = fechaColegiatura || "";
  document.getElementById("edit-epc").value = epc || 0;
  document.getElementById("edit-vigencia").value = vigencia || "";
  mostrarModal("modal-editar");
}

function cerrarModalEditar() {
  ocultarModal("modal-editar");
}

function _validarFormNuevo(form) {
  limpiarErroresFormulario(form);
  let valido = true;

  const nombre = form.querySelector('[name="nombre"]');
  if (!nombre.value.trim()) {
    mostrarErrorCampo(nombre, "El nombre es obligatorio.");
    valido = false;
  } else if (!validarNombrePeru(nombre.value)) {
    mostrarErrorCampo(nombre, "Solo letras, tildes y espacios (mínimo 3 caracteres).");
    valido = false;
  }

  const matricula = form.querySelector('[name="matricula"]');
  if (!matricula.value.trim()) {
    mostrarErrorCampo(matricula, "La matrícula es obligatoria.");
    valido = false;
  }

  const documento = form.querySelector('[name="documento"]');
  if (!documento.value.trim()) {
    mostrarErrorCampo(documento, "El DNI es obligatorio.");
    valido = false;
  } else if (!validarDNIPeru(documento.value)) {
    mostrarErrorCampo(documento, "El DNI debe tener exactamente 8 dígitos numéricos.");
    valido = false;
  }

  const especialidad = form.querySelector('[name="especialidad_id"]');
  if (!especialidad.value.trim()) {
    mostrarErrorCampo(especialidad, "La especialidad es obligatoria.");
    valido = false;
  }

  const direccion = form.querySelector('[name="direccion"]');
  if (!direccion.value.trim()) {
    mostrarErrorCampo(direccion, "La direccion es obligatoria.");
    valido = false;
  }

  const correo = form.querySelector('[name="correo"]');
  if (!correo.value.trim()) {
    mostrarErrorCampo(correo, "El correo es obligatorio.");
    valido = false;
  } else if (!validarCorreo(correo.value)) {
    mostrarErrorCampo(correo, "Ingrese un correo electrónico válido.");
    valido = false;
  }

  const telefono = form.querySelector('[name="telefono"]');
  if (telefono && !validarTelefonoPeru(telefono.value)) {
    mostrarErrorCampo(telefono, "Debe tener 9 dígitos y comenzar con 9 (ej: 987654321).");
    valido = false;
  }

  const password = form.querySelector('[name="password"]');
  if (!password.value.trim()) {
    mostrarErrorCampo(password, "La contraseña es obligatoria.");
    valido = false;
  }

  return valido;
}

function _validarFormEditar(form) {
  limpiarErroresFormulario(form);
  let valido = true;

  const nombre = form.querySelector('[name="nombre"]');
  if (!nombre.value.trim()) {
    mostrarErrorCampo(nombre, "El nombre es obligatorio.");
    valido = false;
  } else if (!validarNombrePeru(nombre.value)) {
    mostrarErrorCampo(nombre, "Solo letras, tildes y espacios (mínimo 3 caracteres).");
    valido = false;
  }

  const especialidad = form.querySelector('[name="especialidad_id"]');
  if (!especialidad.value.trim()) {
    mostrarErrorCampo(especialidad, "La especialidad es obligatoria.");
    valido = false;
  }

  const direccion = form.querySelector('[name="direccion"]');
  if (!direccion.value.trim()) {
    mostrarErrorCampo(direccion, "La direccion es obligatoria.");
    valido = false;
  }

  const correo = form.querySelector('[name="correo"]');
  if (correo.value.trim() && !validarCorreo(correo.value)) {
    mostrarErrorCampo(correo, "Ingrese un correo electrónico válido.");
    valido = false;
  }

  const telefono = form.querySelector('[name="telefono"]');
  if (telefono && !validarTelefonoPeru(telefono.value)) {
    mostrarErrorCampo(telefono, "Debe tener 9 dígitos y comenzar con 9 (ej: 987654321).");
    valido = false;
  }

  return valido;
}

document.addEventListener("DOMContentLoaded", function () {
  ["modal-nuevo", "modal-editar"].forEach(function (id) {
    const modal = document.getElementById(id);
    if (!modal) return;
    modal.addEventListener("click", function (e) {
      if (e.target === modal) ocultarModal(id);
    });
  });

  const formNuevo = document.querySelector("#modal-nuevo .formulario");
  if (formNuevo) {
    formNuevo.addEventListener("submit", function (e) {
      if (!_validarFormNuevo(formNuevo)) {
        e.preventDefault();
      }
    });
    formNuevo.querySelectorAll(".campo-formulario").forEach(function (campo) {
      campo.addEventListener("input", function () { limpiarErrorCampo(campo); });
    });
  }

  const formEditar = document.getElementById("form-editar");
  if (formEditar) {
    formEditar.addEventListener("submit", function (e) {
      if (!_validarFormEditar(formEditar)) {
        e.preventDefault();
      }
    });
    formEditar.querySelectorAll(".campo-formulario").forEach(function (campo) {
      campo.addEventListener("input", function () { limpiarErrorCampo(campo); });
    });
  }
});

window.abrirModalNuevo = abrirModalNuevo;
window.cerrarModalNuevo = cerrarModalNuevo;
window.abrirModalEditar = abrirModalEditar;
window.cerrarModalEditar = cerrarModalEditar;
