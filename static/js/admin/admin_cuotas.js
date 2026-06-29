function abrirModalNueva() {
  const form = document.querySelector("#modal-nueva .formulario");
  if (form) {
    form.reset();
    limpiarErroresFormulario(form);
    _limpiarBuscadorColegiado(form);
  }
  mostrarModal("modal-nueva");
}

function cerrarModalNueva() {
  ocultarModal("modal-nueva");
}

function _validarFormCuota(form) {
  limpiarErroresFormulario(form);
  let valido = true;

  const matricula = form.querySelector('[name="matricula"]');
  const inputColegiado = form.querySelector("[data-colegiado-input]");
  if (!matricula.value.trim()) {
    mostrarErrorCampo(inputColegiado || matricula, "Busque y seleccione un colegiado.");
    valido = false;
  }

  const fecha = form.querySelector('[name="fecha"]');
  if (!fecha.value.trim()) {
    mostrarErrorCampo(fecha, "La fecha es obligatoria.");
    valido = false;
  }

  const fechaVencimiento = form.querySelector('[name="fecha_vencimiento"]');
  if (fechaVencimiento && fecha.value && fechaVencimiento.value &&
      fechaVencimiento.value < fecha.value) {
    mostrarErrorCampo(fechaVencimiento, "El vencimiento no puede ser anterior a la fecha.");
    valido = false;
  }

  const monto = form.querySelector('[name="monto"]');
  if (!monto.value.trim() || parseFloat(monto.value) <= 0) {
    mostrarErrorCampo(monto, "Ingrese un monto mayor a 0.");
    valido = false;
  }

  const concepto = form.querySelector('[name="concepto"]');
  if (!concepto.value.trim()) {
    mostrarErrorCampo(concepto, "El concepto es obligatorio.");
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

function _inicializarBuscadorColegiado(picker) {
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
    seleccion.textContent = "Seleccione un resultado para usarlo en la cuota.";

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
      mostrarMensaje("No se pudo realizar la búsqueda.");
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

function _validarFormPagoAnual(form) {
  limpiarErroresFormulario(form);
  let valido = true;

  const matricula = form.querySelector('[name="matricula"]');
  const inputColegiado = form.querySelector("[data-colegiado-input]");
  if (!matricula.value.trim()) {
    mostrarErrorCampo(inputColegiado || matricula, "Busque y seleccione un colegiado.");
    valido = false;
  }

  const monto = form.querySelector('[name="monto_mensual"]');
  if (!monto.value.trim() || parseFloat(monto.value) <= 0) {
    mostrarErrorCampo(monto, "Ingrese un monto mensual mayor a 0.");
    valido = false;
  }

  const descuento = form.querySelector('[name="descuento_anual"]');
  if (descuento && (!descuento.value.trim() || parseFloat(descuento.value) < 0 || parseFloat(descuento.value) > 50)) {
    mostrarErrorCampo(descuento, "Ingrese un descuento entre 0 y 50.");
    valido = false;
  }

  return valido;
}

function _actualizarTotalAdelantado(form) {
  const salida = form.querySelector("[data-total-adelantado]");
  if (!salida) return;

  const monto = parseFloat(form.querySelector('[name="monto_mensual"]').value || "0");
  const cantidad = parseInt(form.querySelector('[name="cantidad_meses"]').value || "0", 10);
  const total = monto > 0 && cantidad > 0 ? monto * cantidad : 0;
  salida.textContent = "S/ " + total.toFixed(2);
}

function _validarFormPagoAdelantado(form) {
  limpiarErroresFormulario(form);
  let valido = true;

  const matricula = form.querySelector('[name="matricula"]');
  const inputColegiado = form.querySelector("[data-colegiado-input]");
  if (!matricula.value.trim()) {
    mostrarErrorCampo(inputColegiado || matricula, "Busque y seleccione un colegiado.");
    valido = false;
  }

  const mesInicio = form.querySelector('[name="mes_inicio"]');
  const cantidad = form.querySelector('[name="cantidad_meses"]');
  const monto = form.querySelector('[name="monto_mensual"]');
  const mes = parseInt(mesInicio.value || "0", 10);
  const meses = parseInt(cantidad.value || "0", 10);

  if (mes < 1 || mes > 12) {
    mostrarErrorCampo(mesInicio, "Seleccione un mes válido.");
    valido = false;
  }
  if (meses < 1 || meses > 12) {
    mostrarErrorCampo(cantidad, "Ingrese una cantidad entre 1 y 12.");
    valido = false;
  } else if (mes + meses - 1 > 12) {
    mostrarErrorCampo(cantidad, "El rango no puede pasar de diciembre.");
    valido = false;
  }
  if (!monto.value.trim() || parseFloat(monto.value) <= 0) {
    mostrarErrorCampo(monto, "Ingrese un monto mensual mayor a 0.");
    valido = false;
  }

  return valido;
}

document.addEventListener("DOMContentLoaded", function () {
  const modal = document.getElementById("modal-nueva");
  if (modal) {
    modal.addEventListener("click", function (e) {
      if (e.target === modal) cerrarModalNueva();
    });
  }

  const form = document.querySelector("#modal-nueva .formulario");
  if (form) {
    form.addEventListener("submit", function (e) {
      if (!_validarFormCuota(form)) {
        e.preventDefault();
      }
    });
    form.querySelectorAll(".campo-formulario").forEach(function (campo) {
      campo.addEventListener("change", function () { limpiarErrorCampo(campo); });
      campo.addEventListener("input", function () { limpiarErrorCampo(campo); });
    });
  }

  const formMensual = document.querySelector(".procesamiento-grid form[action*='procesar-mensuales']");
  if (formMensual) {
    formMensual.addEventListener("submit", function (e) {
      const montoMensual = formMensual.querySelector('[name="monto_mensual"]');
      limpiarErroresFormulario(formMensual);
      if (!montoMensual.value.trim() || parseFloat(montoMensual.value) <= 0) {
        e.preventDefault();
        mostrarErrorCampo(montoMensual, "Ingrese un monto mensual mayor a 0.");
      }
    });
    formMensual.querySelectorAll(".campo-formulario").forEach(function (campo) {
      campo.addEventListener("input", function () { limpiarErrorCampo(campo); });
    });
  }

  const formAnual = document.querySelector("[data-pago-anual-form]");
  if (formAnual) {
    formAnual.addEventListener("submit", function (e) {
      if (!_validarFormPagoAnual(formAnual)) {
        e.preventDefault();
      }
    });
    formAnual.querySelectorAll(".campo-formulario").forEach(function (campo) {
      campo.addEventListener("change", function () { limpiarErrorCampo(campo); });
      campo.addEventListener("input", function () { limpiarErrorCampo(campo); });
    });
  }

  const formAdelantado = document.querySelector("[data-pago-adelantado-form]");
  if (formAdelantado) {
    _actualizarTotalAdelantado(formAdelantado);
    formAdelantado.addEventListener("submit", function (e) {
      if (!_validarFormPagoAdelantado(formAdelantado)) {
        e.preventDefault();
      }
    });
    formAdelantado.querySelectorAll(".campo-formulario").forEach(function (campo) {
      campo.addEventListener("change", function () {
        limpiarErrorCampo(campo);
        _actualizarTotalAdelantado(formAdelantado);
      });
      campo.addEventListener("input", function () {
        limpiarErrorCampo(campo);
        _actualizarTotalAdelantado(formAdelantado);
      });
    });
  }

  document.querySelectorAll("[data-colegiado-picker]").forEach(function (picker) {
    _inicializarBuscadorColegiado(picker);
  });
});

window.abrirModalNueva = abrirModalNueva;
window.cerrarModalNueva = cerrarModalNueva;
