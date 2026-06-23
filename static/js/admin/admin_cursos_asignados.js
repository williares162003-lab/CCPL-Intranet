function abrirModalNuevaInscripcion() {
  const form = document.querySelector("[data-nueva-inscripcion-form]");
  if (form) {
    form.reset();
    limpiarErroresFormulario(form);
    _limpiarBuscadorColegiado(form);
  }
  mostrarModal("modal-nueva-inscripcion");
}

function cerrarModalNuevaInscripcion() {
  ocultarModal("modal-nueva-inscripcion");
}

function abrirModalEditarAsignacion(datos) {
  const form = document.getElementById("form-editar-asignacion");
  limpiarErroresFormulario(form);
  form.action = "/admin/cursos-asignados/" + datos.id + "/actualizar";

  document.getElementById("edit-asignacion-colegiado").textContent = datos.nombre || "";
  document.getElementById("edit-asignacion-matricula").textContent = datos.matricula || "";
  document.getElementById("edit-asignacion-curso").textContent = datos.titulo || "";
  document.getElementById("edit-estado-pago").value = datos.estadoPago || "Pendiente";

  mostrarModal("modal-editar-asignacion");
}

function cerrarModalEditarAsignacion() {
  ocultarModal("modal-editar-asignacion");
}

function abrirModalSubirCertificado(datos) {
  const form = document.getElementById("form-subir-certificado");
  limpiarErroresFormulario(form);
  form.reset();
  form.action = "/admin/cursos-asignados/" + datos.id + "/certificado";

  document.getElementById("certificado-colegiado").textContent = datos.nombre || "";
  document.getElementById("certificado-matricula").textContent = datos.matricula || "";
  document.getElementById("certificado-curso").textContent = datos.titulo || "";
  const regla = document.getElementById("certificado-regla");
  if (regla) {
    regla.textContent = "Regla: pago " + (datos.estadoPago || "-") +
      " y progreso " + (datos.progreso || "0") + "%. Solo se permite con pago Pagado y 100%.";
  }
  const actual = document.getElementById("certificado-actual");
  if (actual) {
    actual.textContent = datos.certificado
      ? "Archivo actual: " + datos.certificado.split("/").pop()
      : "Adjunte PDF o imagen del certificado.";
  }

  mostrarModal("modal-subir-certificado");
}

function cerrarModalSubirCertificado() {
  ocultarModal("modal-subir-certificado");
}

function validarFormAsignacion(form) {
  limpiarErroresFormulario(form);
  let valido = true;

  const estadoPago = form.querySelector('[name="estado_pago"]');
  if (!estadoPago.value.trim()) {
    mostrarErrorCampo(estadoPago, "Seleccione el estado de pago.");
    valido = false;
  }

  return valido;
}

function validarFormCertificado(form) {
  limpiarErroresFormulario(form);
  const archivo = form.querySelector('[name="certificado_archivo"]');

  if (!archivo.files || !archivo.files.length) {
    mostrarErrorCampo(archivo, "Seleccione el archivo del certificado.");
    return false;
  }
  return true;
}

function validarFormNuevaInscripcion(form) {
  limpiarErroresFormulario(form);
  let valido = true;

  const matricula = form.querySelector('[name="matricula"]');
  const inputColegiado = form.querySelector("[data-colegiado-input]");
  if (!matricula.value.trim()) {
    mostrarErrorCampo(inputColegiado || matricula, "Busque y seleccione un colegiado.");
    valido = false;
  }

  const curso = form.querySelector('[name="curso_id"]');
  if (!curso.value.trim()) {
    mostrarErrorCampo(curso, "Seleccione un curso.");
    valido = false;
  }

  const estadoPago = form.querySelector('[name="estado_pago"]');
  if (!estadoPago.value.trim()) {
    mostrarErrorCampo(estadoPago, "Seleccione el estado de pago.");
    valido = false;
  }

  return valido;
}

function _limpiarBuscadorColegiado(form) {
  const picker = form.querySelector("[data-colegiado-picker]");
  if (!picker) return;

  const input = picker.querySelector("[data-colegiado-input]");
  const hidden = picker.querySelector("[data-colegiado-hidden]");
  const results = picker.querySelector("[data-colegiado-results]");
  const seleccion = picker.querySelector("[data-colegiado-seleccion]");

  if (input) input.value = "";
  if (hidden) hidden.value = "";
  if (results) {
    results.innerHTML = "";
    results.classList.add("hidden");
  }
  if (seleccion) {
    seleccion.textContent = "Escriba al menos 2 caracteres y seleccione un colegiado.";
  }
}

function _crearResultadoColegiado(item, seleccionar) {
  const boton = document.createElement("button");
  boton.type = "button";
  boton.className = "resultado-colegiado";

  const nombre = document.createElement("span");
  nombre.className = "resultado-nombre";
  nombre.textContent = item.nombre || "Sin nombre";

  const detalle = document.createElement("span");
  detalle.className = "resultado-detalle";
  detalle.textContent = `${item.matricula || ""} · ${item.estado || ""}`;

  boton.appendChild(nombre);
  boton.appendChild(detalle);
  boton.addEventListener("click", function () { seleccionar(item); });
  return boton;
}

function _inicializarBuscadorColegiado() {
  const picker = document.querySelector("[data-colegiado-picker]");
  if (!picker) return;

  const input = picker.querySelector("[data-colegiado-input]");
  const hidden = picker.querySelector("[data-colegiado-hidden]");
  const results = picker.querySelector("[data-colegiado-results]");
  const seleccion = picker.querySelector("[data-colegiado-seleccion]");
  let timer = null;

  function ocultarResultados() {
    results.classList.add("hidden");
  }

  function seleccionar(item) {
    hidden.value = item.matricula || "";
    input.value = `${item.nombre || ""} (${item.matricula || ""})`;
    seleccion.textContent = `Seleccionado: ${item.nombre || ""} (${item.matricula || ""})`;
    ocultarResultados();
    limpiarErrorCampo(input);
  }

  function mostrarMensaje(texto) {
    results.innerHTML = "";
    const mensaje = document.createElement("p");
    mensaje.className = "resultado-vacio";
    mensaje.textContent = texto;
    results.appendChild(mensaje);
    results.classList.remove("hidden");
  }

  async function buscar() {
    const q = input.value.trim();
    hidden.value = "";
    seleccion.textContent = "Seleccione un resultado para usarlo en la inscripcion.";

    if (q.length < 2) {
      results.innerHTML = "";
      ocultarResultados();
      seleccion.textContent = "Escriba al menos 2 caracteres y seleccione un colegiado.";
      return;
    }

    mostrarMensaje("Buscando...");

    try {
      const respuesta = await fetch(`/api/colegiados/buscar?q=${encodeURIComponent(q)}`);
      const payload = await respuesta.json();
      const data = payload.data || [];

      results.innerHTML = "";
      if (!data.length) {
        mostrarMensaje("No se encontraron colegiados.");
        return;
      }

      data.forEach(function (item) {
        results.appendChild(_crearResultadoColegiado(item, seleccionar));
      });
      results.classList.remove("hidden");
    } catch (error) {
      mostrarMensaje("No se pudo realizar la busqueda.");
    }
  }

  input.addEventListener("input", function () {
    limpiarErrorCampo(input);
    clearTimeout(timer);
    timer = setTimeout(buscar, 250);
  });

  input.addEventListener("focus", function () {
    if (input.value.trim().length >= 2 && !hidden.value) buscar();
  });

  document.addEventListener("click", function (e) {
    if (!picker.contains(e.target)) ocultarResultados();
  });
}

document.addEventListener("DOMContentLoaded", function () {
  [
    ["modal-nueva-inscripcion", cerrarModalNuevaInscripcion],
    ["modal-editar-asignacion", cerrarModalEditarAsignacion],
    ["modal-subir-certificado", cerrarModalSubirCertificado],
  ].forEach(function (item) {
    const modal = document.getElementById(item[0]);
    if (!modal) return;
    modal.addEventListener("click", function (e) {
      if (e.target === modal) item[1]();
    });
  });

  const formNuevaInscripcion = document.querySelector("[data-nueva-inscripcion-form]");
  if (formNuevaInscripcion) {
    formNuevaInscripcion.addEventListener("submit", function (e) {
      if (!validarFormNuevaInscripcion(formNuevaInscripcion)) {
        e.preventDefault();
      }
    });
    formNuevaInscripcion.querySelectorAll(".campo-formulario").forEach(function (campo) {
      campo.addEventListener("change", function () { limpiarErrorCampo(campo); });
      campo.addEventListener("input", function () { limpiarErrorCampo(campo); });
    });
  }

  const form = document.querySelector("[data-asignacion-form]");
  if (form) {
    form.addEventListener("submit", function (e) {
      if (!validarFormAsignacion(form)) {
        e.preventDefault();
      }
    });
    form.querySelectorAll(".campo-formulario").forEach(function (campo) {
      campo.addEventListener("input", function () { limpiarErrorCampo(campo); });
      campo.addEventListener("change", function () { limpiarErrorCampo(campo); });
    });
  }

  const formCertificado = document.querySelector("[data-certificado-form]");
  if (formCertificado) {
    formCertificado.addEventListener("submit", function (e) {
      if (!validarFormCertificado(formCertificado)) {
        e.preventDefault();
      }
    });
    formCertificado.querySelectorAll(".campo-formulario").forEach(function (campo) {
      campo.addEventListener("change", function () { limpiarErrorCampo(campo); });
    });
  }

  document.querySelectorAll("[data-edit-asignacion]").forEach(function (boton) {
    boton.addEventListener("click", function () {
      abrirModalEditarAsignacion(boton.dataset);
    });
  });

  document.querySelectorAll("[data-upload-certificado]").forEach(function (boton) {
    boton.addEventListener("click", function () {
      if (boton.disabled) return;
      abrirModalSubirCertificado(boton.dataset);
    });
  });

  _inicializarBuscadorColegiado();
});

window.abrirModalEditarAsignacion = abrirModalEditarAsignacion;
window.cerrarModalEditarAsignacion = cerrarModalEditarAsignacion;
window.abrirModalSubirCertificado = abrirModalSubirCertificado;
window.cerrarModalSubirCertificado = cerrarModalSubirCertificado;
window.abrirModalNuevaInscripcion = abrirModalNuevaInscripcion;
window.cerrarModalNuevaInscripcion = cerrarModalNuevaInscripcion;
