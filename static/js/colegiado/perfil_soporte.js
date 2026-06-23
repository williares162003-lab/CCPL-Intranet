function toggleEditForm() {
  const vista = document.getElementById("vista-perfil");
  const form = document.getElementById("form-editar");
  if (!vista || !form) return;
  const editando = !form.classList.contains("hidden");
  if (editando) {
    limpiarErroresFormulario(form);
    form.classList.add("hidden");
    vista.classList.remove("hidden");
  } else {
    vista.classList.add("hidden");
    form.classList.remove("hidden");
  }
}

function abrirTicket() {
  const form = document.querySelector("#modal-ticket .formulario");
  if (form) {
    form.reset();
    limpiarErroresFormulario(form);
  }
  mostrarModal("modal-ticket");
}

function cerrarTicket() {
  ocultarModal("modal-ticket");
}

function toggleSwitch(boton) {
  const activo = boton.dataset.active === "true";
  boton.dataset.active = activo ? "false" : "true";
  boton.classList.toggle("activo", !activo);
}

document.addEventListener("DOMContentLoaded", function () {
  const modalTicket = document.getElementById("modal-ticket");
  if (modalTicket) {
    modalTicket.addEventListener("click", function (e) {
      if (e.target === modalTicket) cerrarTicket();
    });
  }

  const formTicket = document.querySelector("#modal-ticket .formulario");
  if (formTicket) {
    formTicket.addEventListener("submit", function (e) {
      limpiarErroresFormulario(formTicket);
      let valido = true;

      const asunto = formTicket.querySelector('[name="asunto"]');
      if (!asunto.value.trim()) {
        mostrarErrorCampo(asunto, "El asunto es obligatorio.");
        valido = false;
      }

      const descripcion = formTicket.querySelector('[name="descripcion"]');
      if (!descripcion.value.trim()) {
        mostrarErrorCampo(descripcion, "La descripción es obligatoria.");
        valido = false;
      }

      if (!valido) e.preventDefault();
    });

    formTicket.querySelectorAll(".campo-formulario").forEach(function (campo) {
      campo.addEventListener("input", function () { limpiarErrorCampo(campo); });
    });
  }

  const formEditar = document.getElementById("form-editar");
  if (formEditar) {
    formEditar.addEventListener("submit", function (e) {
      limpiarErroresFormulario(formEditar);
      let valido = true;

      const correo = formEditar.querySelector('[name="correo"]');
      if (correo && correo.value.trim() && !validarCorreo(correo.value)) {
        mostrarErrorCampo(correo, "Ingrese un correo electrónico válido.");
        valido = false;
      }

      const telefono = formEditar.querySelector('[name="telefono"]');
      if (telefono && !validarTelefonoPeru(telefono.value)) {
        mostrarErrorCampo(telefono, "Debe tener 9 dígitos y comenzar con 9 (ej: 987654321).");
        valido = false;
      }

      if (!valido) e.preventDefault();
    });

    formEditar.querySelectorAll(".campo-formulario").forEach(function (campo) {
      campo.addEventListener("input", function () { limpiarErrorCampo(campo); });
    });
  }
});

window.toggleEditForm = toggleEditForm;
window.abrirTicket = abrirTicket;
window.cerrarTicket = cerrarTicket;
window.toggleSwitch = toggleSwitch;
