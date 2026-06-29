function abrirModalNuevoMedioPago() {
  const form = document.querySelector("#modal-nuevo-medio-pago form");
  if (form) {
    form.reset();
    limpiarErroresFormulario(form);
  }
  mostrarModal("modal-nuevo-medio-pago");
}

function cerrarModalNuevoMedioPago() {
  ocultarModal("modal-nuevo-medio-pago");
}

function abrirModalEditarMedioPago(datos) {
  const form = document.getElementById("form-editar-medio-pago");
  limpiarErroresFormulario(form);
  form.action = "/admin/medios-pago/" + datos.id + "/editar";

  document.getElementById("edit-medio-nombre").value = datos.nombre || "";
  document.getElementById("edit-medio-descripcion").value = datos.descripcion || "";
  document.getElementById("edit-medio-cuenta").value = datos.numeroCuenta || "";
  document.getElementById("edit-medio-titular").value = datos.titular || "";
  document.getElementById("edit-medio-activo").value = datos.activo || "1";

  mostrarModal("modal-editar-medio-pago");
}

function cerrarModalEditarMedioPago() {
  ocultarModal("modal-editar-medio-pago");
}

function validarFormMedioPago(form) {
  limpiarErroresFormulario(form);
  let valido = true;

  const nombre = form.querySelector('[name="nombre"]');
  if (!nombre.value.trim()) {
    mostrarErrorCampo(nombre, "Ingrese el nombre del medio de pago.");
    valido = false;
  }

  const cuenta = form.querySelector('[name="numero_cuenta"]');
  if (!cuenta.value.trim()) {
    mostrarErrorCampo(cuenta, "Ingrese el número o identificador de cuenta.");
    valido = false;
  }

  const titular = form.querySelector('[name="titular"]');
  if (!titular.value.trim()) {
    mostrarErrorCampo(titular, "Ingrese el titular.");
    valido = false;
  }

  const activo = form.querySelector('[name="activo"]');
  if (!activo.value.trim()) {
    mostrarErrorCampo(activo, "Seleccione el estado.");
    valido = false;
  }

  return valido;
}

document.addEventListener("DOMContentLoaded", function () {
  ["modal-nuevo-medio-pago", "modal-editar-medio-pago"].forEach(function (id) {
    const modal = document.getElementById(id);
    if (!modal) return;
    modal.addEventListener("click", function (e) {
      if (e.target === modal) ocultarModal(id);
    });
  });

  document.querySelectorAll("[data-medio-pago-form]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      if (!validarFormMedioPago(form)) {
        e.preventDefault();
      }
    });

    form.querySelectorAll(".campo-formulario").forEach(function (campo) {
      campo.addEventListener("input", function () { limpiarErrorCampo(campo); });
      campo.addEventListener("change", function () { limpiarErrorCampo(campo); });
    });
  });

  document.querySelectorAll("[data-edit-medio-pago]").forEach(function (boton) {
    boton.addEventListener("click", function () {
      abrirModalEditarMedioPago(boton.dataset);
    });
  });
});

window.abrirModalNuevoMedioPago = abrirModalNuevoMedioPago;
window.cerrarModalNuevoMedioPago = cerrarModalNuevoMedioPago;
window.abrirModalEditarMedioPago = abrirModalEditarMedioPago;
window.cerrarModalEditarMedioPago = cerrarModalEditarMedioPago;
