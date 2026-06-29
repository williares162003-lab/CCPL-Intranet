function abrirModalEvidenciaPago(datos) {
  const form = document.querySelector("[data-evidencia-pago-form]");
  if (form) {
    form.reset();
    limpiarErroresFormulario(form);
  }

  document.getElementById("evidencia-cuota-id").value = datos.cuotaId || "";
  document.getElementById("evidencia-concepto").textContent = datos.concepto || "";
  document.getElementById("evidencia-monto").value = datos.monto || "";

  mostrarModal("modal-evidencia-pago");
}

function cerrarModalEvidenciaPago() {
  ocultarModal("modal-evidencia-pago");
}

function validarFormEvidenciaPago(form) {
  limpiarErroresFormulario(form);
  let valido = true;

  const medio = form.querySelector('[name="medio_pago_id"]');
  if (!medio.value.trim()) {
    mostrarErrorCampo(medio, "Seleccione el medio de pago.");
    valido = false;
  }

  const fecha = form.querySelector('[name="fecha_pago"]');
  if (!fecha.value.trim()) {
    mostrarErrorCampo(fecha, "Ingrese la fecha de pago.");
    valido = false;
  }

  const operacion = form.querySelector('[name="numero_operacion"]');
  if (!operacion.value.trim()) {
    mostrarErrorCampo(operacion, "Ingrese el número de operacion.");
    valido = false;
  }

  const monto = form.querySelector('[name="monto"]');
  if (!monto.value.trim() || parseFloat(monto.value) <= 0) {
    mostrarErrorCampo(monto, "Ingrese un monto mayor a 0.");
    valido = false;
  }

  const archivo = form.querySelector('[name="archivo_evidencia"]');
  if (!archivo.files || !archivo.files.length) {
    mostrarErrorCampo(archivo, "Adjunte el voucher o evidencia.");
    valido = false;
  }

  return valido;
}

function actualizarTotalAdelanto(form) {
  const salida = form.querySelector("[data-total-adelanto]");
  if (!salida) return;

  const monto = parseFloat(form.dataset.montoMensual || "0");
  const cantidad = parseInt(form.querySelector('[name="cantidad_meses"]').value || "0", 10);
  const total = monto > 0 && cantidad > 0 ? monto * cantidad : 0;
  salida.textContent = "S/ " + total.toFixed(2);
}

function validarFormAdelanto(form) {
  limpiarErroresFormulario(form);
  let valido = true;

  const anio = form.querySelector('[name="anio"]');
  const mesInicio = form.querySelector('[name="mes_inicio"]');
  const cantidad = form.querySelector('[name="cantidad_meses"]');
  const anioNum = parseInt(anio.value || "0", 10);
  const mesNum = parseInt(mesInicio.value || "0", 10);
  const cantidadNum = parseInt(cantidad.value || "0", 10);
  const hoy = new Date();
  const anioActual = hoy.getFullYear();
  const mesActual = hoy.getMonth() + 1;

  if (anioNum < anioActual) {
    mostrarErrorCampo(anio, "Seleccione el año actual o uno futuro.");
    valido = false;
  }
  if (mesNum < 1 || mesNum > 12) {
    mostrarErrorCampo(mesInicio, "Seleccione un mes válido.");
    valido = false;
  }
  if (anioNum === anioActual && mesNum < mesActual) {
    mostrarErrorCampo(mesInicio, "El mes inicial no puede ser anterior al mes actual.");
    valido = false;
  }
  if (cantidadNum < 1 || cantidadNum > 12) {
    mostrarErrorCampo(cantidad, "Ingrese una cantidad entre 1 y 12.");
    valido = false;
  } else if (mesNum + cantidadNum - 1 > 12) {
    mostrarErrorCampo(cantidad, "El rango no puede pasar de diciembre.");
    valido = false;
  }

  return valido;
}

document.addEventListener("DOMContentLoaded", function () {
  const modal = document.getElementById("modal-evidencia-pago");
  if (modal) {
    modal.addEventListener("click", function (e) {
      if (e.target === modal) cerrarModalEvidenciaPago();
    });
  }

  const form = document.querySelector("[data-evidencia-pago-form]");
  if (form) {
    form.addEventListener("submit", function (e) {
      if (!validarFormEvidenciaPago(form)) {
        e.preventDefault();
      }
    });

    form.querySelectorAll(".campo-formulario").forEach(function (campo) {
      campo.addEventListener("input", function () { limpiarErrorCampo(campo); });
      campo.addEventListener("change", function () { limpiarErrorCampo(campo); });
    });
  }

  document.querySelectorAll("[data-registrar-evidencia]").forEach(function (boton) {
    boton.addEventListener("click", function () {
      abrirModalEvidenciaPago(boton.dataset);
    });
  });

  const formAdelanto = document.querySelector("[data-adelantar-cuotas-form]");
  if (formAdelanto) {
    actualizarTotalAdelanto(formAdelanto);
    formAdelanto.addEventListener("submit", function (e) {
      if (!validarFormAdelanto(formAdelanto)) {
        e.preventDefault();
      }
    });
    formAdelanto.querySelectorAll(".campo-formulario").forEach(function (campo) {
      campo.addEventListener("input", function () {
        limpiarErrorCampo(campo);
        actualizarTotalAdelanto(formAdelanto);
      });
      campo.addEventListener("change", function () {
        limpiarErrorCampo(campo);
        actualizarTotalAdelanto(formAdelanto);
      });
    });
  }
});

window.abrirModalEvidenciaPago = abrirModalEvidenciaPago;
window.cerrarModalEvidenciaPago = cerrarModalEvidenciaPago;
