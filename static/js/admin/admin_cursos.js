function abrirModalNuevoCurso() {
  const form = document.querySelector("#modal-nuevo-curso .formulario");
  if (form) {
    form.reset();
    limpiarErroresFormulario(form);
  }
  mostrarModal("modal-nuevo-curso");
}

function cerrarModalNuevoCurso() {
  ocultarModal("modal-nuevo-curso");
}

function abrirModalEditarCurso(datos) {
  const form = document.getElementById("form-editar-curso");
  limpiarErroresFormulario(form);
  form.dataset.inscritos = datos.inscritos || "0";
  form.action = "/admin/cursos/" + datos.id + "/editar";
  document.getElementById("edit-titulo").value = datos.titulo || "";
  document.getElementById("edit-categoria").value = datos.categoria || "";
  document.getElementById("edit-descripcion").value = datos.descripcion || "";
  document.getElementById("edit-monto").value = datos.monto || "";
  document.getElementById("edit-monto-inhabil").value = datos.montoInhabil || datos.monto || "";
  document.getElementById("edit-ponente").value = datos.ponente || "";
  document.getElementById("edit-modalidad").value = datos.modalidad || "";
  document.getElementById("edit-duracion-horas").value = datos.duracionHoras || "";
  document.getElementById("edit-fecha-inicio").value = datos.fechaInicio || "";
  document.getElementById("edit-fecha-fin").value = datos.fechaFin || "";
  document.getElementById("edit-cupos").value = datos.cupos || "";
  document.getElementById("edit-cupos-ayuda").textContent =
    "Inscritos actuales: " + (datos.inscritos || "0") + ". No puede guardar menos cupos que inscritos.";
  document.getElementById("edit-estado").value = datos.estado || "Activo";
  mostrarModal("modal-editar-curso");
}

function cerrarModalEditarCurso() {
  ocultarModal("modal-editar-curso");
}

function validarFormCurso(form) {
  limpiarErroresFormulario(form);
  let valido = true;

  const titulo = form.querySelector('[name="titulo"]');
  if (!titulo.value.trim()) {
    mostrarErrorCampo(titulo, "El titulo es obligatorio.");
    valido = false;
  }

  const categoria = form.querySelector('[name="categoria"]');
  if (!categoria.value.trim()) {
    mostrarErrorCampo(categoria, "Seleccione una categoria.");
    valido = false;
  }

  const monto = form.querySelector('[name="monto"]');
  if (!monto.value.trim() || parseFloat(monto.value) <= 0) {
    mostrarErrorCampo(monto, "Ingrese un precio habil mayor a 0.");
    valido = false;
  }

  const montoInhabil = form.querySelector('[name="monto_inhabil"]');
  if (!montoInhabil.value.trim() || parseFloat(montoInhabil.value) <= 0) {
    mostrarErrorCampo(montoInhabil, "Ingrese un precio inhabil mayor a 0.");
    valido = false;
  } else if (monto.value.trim() && parseFloat(montoInhabil.value) < parseFloat(monto.value)) {
    mostrarErrorCampo(montoInhabil, "Debe ser mayor o igual al precio habil.");
    valido = false;
  }

  const ponente = form.querySelector('[name="ponente"]');
  if (!ponente.value.trim()) {
    mostrarErrorCampo(ponente, "El ponente es obligatorio.");
    valido = false;
  }

  const modalidad = form.querySelector('[name="modalidad"]');
  if (!modalidad.value.trim()) {
    mostrarErrorCampo(modalidad, "Seleccione una modalidad.");
    valido = false;
  }

  const duracion = form.querySelector('[name="duracion_horas"]');
  if (!duracion.value.trim() || parseInt(duracion.value, 10) <= 0) {
    mostrarErrorCampo(duracion, "Ingrese una duracion mayor a 0.");
    valido = false;
  }

  const fechaInicio = form.querySelector('[name="fecha_inicio"]');
  const fechaFin = form.querySelector('[name="fecha_fin"]');
  if (!fechaInicio.value.trim()) {
    mostrarErrorCampo(fechaInicio, "Ingrese la fecha de inicio.");
    valido = false;
  }
  if (!fechaFin.value.trim()) {
    mostrarErrorCampo(fechaFin, "Ingrese la fecha fin.");
    valido = false;
  }
  if (fechaInicio.value && fechaFin.value && fechaFin.value < fechaInicio.value) {
    mostrarErrorCampo(fechaFin, "La fecha fin no puede ser menor que la fecha inicio.");
    valido = false;
  }

  const cupos = form.querySelector('[name="cupos"]');
  if (!cupos.value.trim() || parseInt(cupos.value, 10) <= 0) {
    mostrarErrorCampo(cupos, "Ingrese cupos mayores a 0.");
    valido = false;
  } else {
    const inscritos = parseInt(form.dataset.inscritos || "0", 10);
    const valorCupos = parseInt(cupos.value, 10);
    if (inscritos > 0 && valorCupos < inscritos) {
      mostrarErrorCampo(cupos, "No puede ser menor que los inscritos actuales.");
      valido = false;
    }
  }

  const estado = form.querySelector('[name="estado"]');
  if (!estado.value.trim()) {
    mostrarErrorCampo(estado, "Seleccione el estado.");
    valido = false;
  }

  return valido;
}

document.addEventListener("DOMContentLoaded", function () {
  ["modal-nuevo-curso", "modal-editar-curso"].forEach(function (id) {
    const modal = document.getElementById(id);
    if (!modal) return;
    modal.addEventListener("click", function (e) {
      if (e.target === modal) ocultarModal(id);
    });
  });

  document.querySelectorAll("[data-curso-form]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      if (!validarFormCurso(form)) {
        e.preventDefault();
      }
    });
    form.querySelectorAll(".campo-formulario").forEach(function (campo) {
      campo.addEventListener("input", function () { limpiarErrorCampo(campo); });
      campo.addEventListener("change", function () { limpiarErrorCampo(campo); });
    });
  });

  document.querySelectorAll("[data-edit-curso]").forEach(function (boton) {
    boton.addEventListener("click", function () {
      abrirModalEditarCurso(boton.dataset);
    });
  });
});

window.abrirModalNuevoCurso = abrirModalNuevoCurso;
window.cerrarModalNuevoCurso = cerrarModalNuevoCurso;
window.abrirModalEditarCurso = abrirModalEditarCurso;
window.cerrarModalEditarCurso = cerrarModalEditarCurso;
