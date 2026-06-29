document.addEventListener("DOMContentLoaded", () => {
  const config = document.getElementById("edni-config");
  const estado = document.getElementById("edni-estado");
  const btnVerificar = document.getElementById("btn-verificar-edni");
  const btnFirmar = document.getElementById("btn-firmar-edni");
  const inputPin = document.getElementById("edni-pin");

  if (!config || !estado || !btnVerificar || !btnFirmar) return;

  const escapeHtml = (valor) => String(valor || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

  const esDetalleTecnico = (texto) => {
    const valor = String(texto || "").toLowerCase();
    return [
      "traceback",
      "no module named",
      "could not",
      "private key",
      "ckr_",
      "pkcs11",
      "exception"
    ].some((patron) => valor.includes(patron));
  };

  const mensajeFirmaAmigable = (data) => {
    const mensaje = String(data?.message || "");
    const detalle = String(data?.detalle || "");
    const tipo = String(data?.tipo_error || "");
    const texto = `${mensaje} ${detalle} ${tipo}`.toLowerCase();

    if (texto.includes("pinincorrect") || texto.includes("pin incorrect")) {
      return "PIN incorrecto. Verifique el PIN de firma del DNIe antes de volver a intentar.";
    }
    if (texto.includes("private key")) {
      return "No se pudo usar la llave privada del certificado de firma. Verifique que el DNIe este insertado, activo y con PIN correcto.";
    }
    if (texto.includes("no module named")) {
      return "Falta una dependencia del módulo de firma. Revise la instalación antes de volver a intentar.";
    }
    if (texto.includes("pkcs11") || texto.includes("middleware")) {
      return "No se pudo acceder al certificado del DNIe. Revise el driver RENIEC, el middleware y que el DNIe este insertado.";
    }
    return mensaje || "No se pudo completar la firma eDNI.";
  };

  const mensajeConexionFirmador = (error) => {
    const texto = String(error?.message || "").toLowerCase();
    if (texto.includes("failed to fetch") || texto.includes("networkerror")) {
      return "No se pudo conectar con el firmador local. Ejecute iniciar_firmador_edni.bat en esta computadora y vuelva a verificar.";
    }
    return error?.message || "Revise la instalación del firmador eDNI antes de continuar.";
  };

  const setEstado = (tipo, titulo, detalle, icono) => {
    estado.className = `edni-estado ${tipo}`;
    estado.innerHTML = `
      <span class="material-symbols-outlined">${icono}</span>
      <div>
        <strong>${escapeHtml(titulo)}</strong>
        <p>${escapeHtml(detalle)}</p>
      </div>
    `;
  };

  const setEstadoHtml = (tipo, titulo, detalleHtml, icono) => {
    estado.className = `edni-estado ${tipo}`;
    estado.innerHTML = `
      <span class="material-symbols-outlined">${icono}</span>
      <div>
        <strong>${escapeHtml(titulo)}</strong>
        ${detalleHtml}
      </div>
    `;
  };

  const detalleFirmador = (data) => {
    const certificado = Array.isArray(data.certificados) ? data.certificados[0] : null;
    const token = data.token || {};
    const lectores = Number(data.lectores || 0);
    const textoLector = lectores <= 0
      ? "No conectado"
      : `${lectores} conectado${lectores === 1 ? "" : "s"}`;
    const textoDni = data.tarjeta_responde === false
      ? "Insertado, no responde"
      : (data.dni_insertado ? "Insertado" : "No insertado");
    const lineas = [
      `<p>${escapeHtml(data.message || "Estado del firmador verificado.")}</p>`,
      `<ul class="edni-datos">`,
      `<li><span>Lector:</span><strong>${escapeHtml(textoLector)}</strong></li>`,
      `<li><span>DNIe:</span><strong>${escapeHtml(textoDni)}</strong></li>`
    ];

    if (token.label || token.serie) {
      lineas.push(`<li><span>Token:</span><strong>${escapeHtml(token.label || token.serie)}</strong></li>`);
    }

    if (data.token_firma) {
      lineas.push(`<li><span>Uso:</span><strong>Firma digital</strong></li>`);
    }

    if (data.driver_detectado) {
      lineas.push(`<li><span>Driver:</span><strong>${escapeHtml(data.driver_detectado)}</strong></li>`);
    }

    if (data.requiere_middleware) {
      lineas.push(`<li><span>Firma:</span><strong>Middleware requerido</strong></li>`);
    }

    if (data.detalle && !esDetalleTecnico(data.detalle)) {
      lineas.push(`<li><span>Detalle:</span><strong>${escapeHtml(data.detalle)}</strong></li>`);
    }

    if (certificado && !certificado.error) {
      lineas.push(`<li><span>Certificado:</span><strong>${escapeHtml(certificado.label || "FIR detectado")}</strong></li>`);
      lineas.push(`<li><span>Titular:</span><strong>${escapeHtml(certificado.titular || "No identificado")}</strong></li>`);
      if (certificado.dni || certificado.documento) {
        lineas.push(`<li><span>DNI / doc.:</span><strong>${escapeHtml(certificado.dni || certificado.documento)}</strong></li>`);
      }
      if (certificado.vigente_hasta) {
        lineas.push(`<li><span>Vigente hasta:</span><strong>${escapeHtml(certificado.vigente_hasta)}</strong></li>`);
      }
    }

    if (certificado && certificado.error) {
      lineas.push(`<li><span>Certificado:</span><strong>No legible sin PIN o middleware correcto</strong></li>`);
    }

    lineas.push(`</ul>`);
    return lineas.join("");
  };

  const blobToBase64 = (blob) => new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const texto = String(reader.result || "");
      resolve(texto.includes(",") ? texto.split(",", 2)[1] : texto);
    };
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });

  const verificarFirmador = async () => {
    btnFirmar.disabled = true;
    setEstado("proceso", "Verificando", "Revisando lector, DNIe y certificado de firma.", "sync");
    try {
      const respuesta = await fetch(config.dataset.estadoUrl, { method: "GET" });
      const data = await respuesta.json().catch(() => null);
      if (!data) throw new Error("Sin respuesta del módulo de firma eDNI.");
      const ok = data.code === 1 || data.ok === true || data.estado === "ok";
      const tieneCertificado = Array.isArray(data.certificados) && data.certificados.length > 0;
      const tieneCertificadoFirma = data.certificado_firma_detectado === true || (
        tieneCertificado && String(data.certificados[0].label || "").toUpperCase().includes(" FIR ")
      );
      if (!ok) {
        const sinLector = Number(data.lectores || 0) === 0;
        const tarjetaMuda = data.tarjeta_responde === false;
        const requiereMiddleware = data.requiere_middleware === true;
        setEstadoHtml(
          requiereMiddleware ? "proceso" : (data.dni_insertado || sinLector ? "error" : "proceso"),
          requiereMiddleware
            ? "Middleware requerido"
            : data.dni_insertado
            ? (tarjetaMuda ? "DNIe no responde" : "Certificado no disponible")
            : (sinLector ? "Lector no conectado" : "Lector detectado"),
          detalleFirmador(data),
          requiereMiddleware ? "admin_panel_settings" : (data.dni_insertado || sinLector ? "error" : "badge")
        );
        btnFirmar.disabled = true;
        return;
      }
      setEstadoHtml(
        "ok",
        tieneCertificadoFirma ? "DNIe listo para firmar" : "Certificado de firma no detectado",
        detalleFirmador(data),
        tieneCertificadoFirma ? "check_circle" : "warning"
      );
      btnFirmar.disabled = !tieneCertificadoFirma;
    } catch (error) {
      setEstado("error", "Modulo de firma no disponible", mensajeConexionFirmador(error), "error");
    }
  };

  const firmarConEdni = async () => {
    const pin = inputPin ? inputPin.value.trim() : "";
    if (!pin) {
      setEstado("error", "PIN requerido", "Ingrese el PIN del DNIe para continuar.", "lock");
      if (inputPin) inputPin.focus();
      return;
    }

    btnFirmar.disabled = true;
    setEstado("proceso", "Preparando PDF", "Enviando certificado base al firmador local.", "pending");
    try {
      const pdfRespuesta = await fetch(config.dataset.pdfUrl, { credentials: "same-origin" });
      if (!pdfRespuesta.ok) throw new Error("No se pudo obtener el PDF base.");
      const pdfBase64 = await blobToBase64(await pdfRespuesta.blob());

      const firmaRespuesta = await fetch(config.dataset.firmaUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tramite_id: config.dataset.tramiteId,
          nombre_archivo: config.dataset.nombreArchivo,
          archivo_pdf_base64: pdfBase64,
          pin
        })
      });
      const firmaData = await firmaRespuesta.json().catch(() => null);
      if (!firmaData) throw new Error("El firmador no devolvió una respuesta legible.");
      if (!firmaRespuesta.ok) {
        throw new Error(mensajeFirmaAmigable(firmaData));
      }
      if (!(firmaData.code === 1 || firmaData.ok === true) || !firmaData.archivo_pdf_base64) {
        throw new Error(mensajeFirmaAmigable(firmaData));
      }

      setEstado("proceso", "Registrando", "Guardando PDF firmado en el sistema.", "upload_file");
      const guardarRespuesta = await fetch(config.dataset.guardarUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nombre_archivo: firmaData.nombre_archivo || config.dataset.nombreArchivo,
          archivo_pdf_base64: firmaData.archivo_pdf_base64
        })
      });
      const guardarData = await guardarRespuesta.json();
      if (!(guardarRespuesta.ok && guardarData.code === 1)) {
        throw new Error(guardarData.message || "No se pudo registrar el PDF firmado.");
      }
      setEstado("ok", "Certificado registrado", "El PDF firmado fue guardado correctamente.", "verified");
      if (guardarData.redirect) {
        window.location.href = guardarData.redirect;
      }
    } catch (error) {
      setEstado("error", "Firma no completada", mensajeConexionFirmador(error), "error");
      btnFirmar.disabled = false;
    }
  };

  btnVerificar.addEventListener("click", verificarFirmador);
  btnFirmar.addEventListener("click", firmarConEdni);
});
