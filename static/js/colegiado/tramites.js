document.addEventListener("DOMContentLoaded", function () {
  const fileInput = document.getElementById("file-input");
  const fileName = document.getElementById("file-name");
  const bloqueDocumento = document.getElementById("bloque-documento");
  const tituloDocumento = document.getElementById("titulo-documento");
  const ayudaDocumento = document.getElementById("ayuda-documento");
  const uploadBox = document.querySelector(".upload-box");

  if (fileInput && fileName) {
    fileInput.addEventListener("change", function (e) {
      const archivo = e.target.files[0];
      fileName.textContent = archivo ? "Archivo: " + archivo.name : "";
      limpiarErrorArchivo();
    });
  }

  const form = document.querySelector("form.formulario-tramite");
  if (!form) return;
  const tipo = form.querySelector('[name="tipo_tramite"]');

  function requiereSustento() {
    if (!tipo || !tipo.selectedOptions.length) return false;
    return tipo.selectedOptions[0].dataset.requiereSustento === "1";
  }

  function actualizarDocumento() {
    const obligatorio = requiereSustento();
    if (bloqueDocumento) bloqueDocumento.classList.toggle("requiere-sustento", obligatorio);
    if (tituloDocumento) {
      tituloDocumento.textContent = obligatorio ? "Sustento obligatorio" : "Sustento opcional";
    }
    if (ayudaDocumento) {
      ayudaDocumento.textContent = obligatorio
        ? "Adjunte el documento de baja o traslado en PDF o imagen"
        : "PDF o imagen, si el tramite lo requiere";
    }
  }

  function limpiarErrorArchivo() {
    if (!fileInput) return;
    limpiarErrorCampo(fileInput);
    if (uploadBox) uploadBox.classList.remove("upload-box-error");
  }

  if (tipo) {
    tipo.addEventListener("change", function () {
      actualizarDocumento();
      limpiarErrorCampo(tipo);
      limpiarErrorArchivo();
    });
    actualizarDocumento();
  }

  form.addEventListener("submit", function (e) {
    limpiarErroresFormulario(form);
    if (uploadBox) uploadBox.classList.remove("upload-box-error");
    let valido = true;

    if (tipo && !tipo.value.trim()) {
      mostrarErrorCampo(tipo, "Seleccione el tipo de tramite.");
      valido = false;
    }

    const asunto = form.querySelector('[name="asunto"]');
    if (asunto && !asunto.value.trim()) {
      mostrarErrorCampo(asunto, "Ingrese el asunto del tramite.");
      valido = false;
    }

    const descripcion = form.querySelector('[name="descripcion"]');
    if (!descripcion.value.trim()) {
      mostrarErrorCampo(descripcion, "La descripcion es obligatoria.");
      valido = false;
    } else if (descripcion.value.trim().length < 10) {
      mostrarErrorCampo(descripcion, "La descripcion debe tener al menos 10 caracteres.");
      valido = false;
    }

    if (requiereSustento() && fileInput && !fileInput.files.length) {
      mostrarErrorCampo(fileInput, "Adjunte el documento sustentatorio para baja o traslado.");
      if (uploadBox) uploadBox.classList.add("upload-box-error");
      valido = false;
    }

    if (!valido) e.preventDefault();
  });

  form.addEventListener("reset", function () {
    setTimeout(function () {
      actualizarDocumento();
      limpiarErrorArchivo();
      if (fileName) fileName.textContent = "";
    }, 0);
  });

  form.querySelectorAll(".campo-formulario").forEach(function (campo) {
    campo.addEventListener("change", function () { limpiarErrorCampo(campo); });
    campo.addEventListener("input", function () { limpiarErrorCampo(campo); });
  });
});
