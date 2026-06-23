document.addEventListener("DOMContentLoaded", function () {
  const form = document.querySelector("[data-contenido-form]");

  if (form) {
    const contenido = form.querySelector('[name="descripcion"]');

    form.addEventListener("submit", function (e) {
      limpiarErroresFormulario(form);
      if (!contenido.value.trim()) {
        e.preventDefault();
        mostrarErrorCampo(contenido, "Ingrese el contenido del curso.");
      }
    });

    contenido.addEventListener("input", function () {
      limpiarErrorCampo(contenido);
    });
  }

  const materialForm = document.querySelector("[data-material-form]");
  if (materialForm) {
    const titulo = materialForm.querySelector('[name="titulo"]');
    const descripcion = materialForm.querySelector('[name="descripcion"]');

    materialForm.addEventListener("submit", function (e) {
      limpiarErroresFormulario(materialForm);
      let valido = true;

      if (!titulo.value.trim()) {
        mostrarErrorCampo(titulo, "Ingrese el titulo del material.");
        valido = false;
      }
      if (!descripcion.value.trim()) {
        mostrarErrorCampo(descripcion, "Ingrese la descripcion del material.");
        valido = false;
      }
      if (!valido) e.preventDefault();
    });

    [titulo, descripcion].forEach(function (campo) {
      campo.addEventListener("input", function () {
        limpiarErrorCampo(campo);
      });
      campo.addEventListener("change", function () {
        limpiarErrorCampo(campo);
      });
    });
  }

  iniciarEdicionProgreso();
});

function abrirModalEditarProgreso(datos) {
  const form = document.getElementById("form-editar-progreso");
  if (!form) return;

  limpiarErroresFormulario(form);
  form.action = "/ponente/inscripciones/" + datos.id + "/progreso";

  document.getElementById("progreso-colegiado").textContent = datos.nombre || "";
  document.getElementById("progreso-matricula").textContent = datos.matricula || "";
  document.getElementById("progreso-curso-id").value = datos.cursoId || "";
  document.getElementById("progreso-valor").value = datos.progreso || "0";

  mostrarModal("modal-editar-progreso");
}

function cerrarModalEditarProgreso() {
  ocultarModal("modal-editar-progreso");
}

function validarFormProgreso(form) {
  limpiarErroresFormulario(form);

  const progreso = form.querySelector('[name="progreso"]');
  const valor = parseInt(progreso.value, 10);

  if (Number.isNaN(valor) || valor < 0 || valor > 100) {
    mostrarErrorCampo(progreso, "Ingrese un progreso entre 0 y 100.");
    return false;
  }
  return true;
}

function iniciarEdicionProgreso() {
  const modal = document.getElementById("modal-editar-progreso");
  if (modal) {
    modal.addEventListener("click", function (e) {
      if (e.target === modal) cerrarModalEditarProgreso();
    });
  }

  const form = document.querySelector("[data-progreso-form]");
  if (form) {
    form.addEventListener("submit", function (e) {
      if (!validarFormProgreso(form)) {
        e.preventDefault();
      }
    });

    form.querySelectorAll(".campo-formulario").forEach(function (campo) {
      campo.addEventListener("input", function () { limpiarErrorCampo(campo); });
      campo.addEventListener("change", function () { limpiarErrorCampo(campo); });
    });
  }

  document.querySelectorAll("[data-edit-progreso]").forEach(function (boton) {
    boton.addEventListener("click", function () {
      abrirModalEditarProgreso(boton.dataset);
    });
  });
}

window.abrirModalEditarProgreso = abrirModalEditarProgreso;
window.cerrarModalEditarProgreso = cerrarModalEditarProgreso;
