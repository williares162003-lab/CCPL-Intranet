import json
import re
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4
from bd import obtenerconexion
from sunat_beta import (SUNAT_BETA_ENDPOINT, SunatBetaError,
                        enviar_comprobante_sunat_beta)
from admin_crudAD import (_leer_registro_por_id, _leer_registros_crud, _insertar_registro_crud, _actualizar_registro_crud, _eliminar_registro_crud)
from admin_cuotasAD import leer_comprobante_pago_demo_admin

# ============================================================
# FACTURACION ELECTRONICA - PREPARADA PARA SUNAT
# ============================================================

def _facturacion_tablas_no_existen(error):
    texto = str(error).lower()
    return (
        "configuracion_facturacion" in texto
        or "comprobantes_fiscales" in texto
        or "comprobante_fiscal_detalle" in texto
        or "facturacion_sunat_logs" in texto
        or "doesn't exist" in texto
        or "no existe" in texto
    )


def _facturacion_tablas_existen(cursor):
    cursor.execute("SHOW TABLES LIKE 'comprobantes_fiscales'")
    return cursor.fetchone() is not None


def _obtener_config_facturacion(cursor, bloquear=False):
    sql =  " SELECT * "
    sql += "   FROM configuracion_facturacion "
    sql += "  WHERE activo = 1 "
    sql += "  ORDER BY id ASC "
    sql += "  LIMIT 1 "
    if bloquear:
        sql += " FOR UPDATE "
    cursor.execute(sql)
    config = cursor.fetchone()
    if config:
        return config

    sql =  " INSERT INTO configuracion_facturacion "
    sql += " (ruc, razon_social, nombre_comercial, direccion, serie_boleta, "
    sql += "  serie_factura, correlativo_boleta, correlativo_factura, "
    sql += "  modo_envio, activo) "
    sql += " VALUES ('00000000000', "
    sql += "         'Colegio de Contadores Publicos de Lambayeque', "
    sql += "         'CCPL', 'Lambayeque', 'B001', 'F001', 1, 1, "
    sql += "         'SUNAT_BETA', 1) "
    cursor.execute(sql)
    config_id = cursor.lastrowid
    cursor.execute(
        "SELECT * FROM configuracion_facturacion WHERE id = %s",
        (config_id,))
    return cursor.fetchone()


def obtener_configuracion_facturacion():
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    return _obtener_config_facturacion(cursor, bloquear=False)
        return None
    except Exception as e:
        if _facturacion_tablas_no_existen(e):
            return None
        raise


def actualizar_configuracion_facturacion(datos):
    try:
        modo = "SUNAT_BETA"

        ruc = re.sub(r"\D", "", str(datos.get("ruc") or ""))
        razon_social = (datos.get("razon_social") or "").strip()
        nombre_comercial = (datos.get("nombre_comercial") or "").strip()
        direccion = (datos.get("direccion") or "").strip()
        serie_boleta = (datos.get("serie_boleta") or "B001").strip().upper()
        serie_factura = (datos.get("serie_factura") or "F001").strip().upper()
        usuario_sol = (datos.get("usuario_sol") or "").strip()
        clave_sol = (datos.get("clave_sol") or "").strip()
        certificado_ruta = (datos.get("certificado_ruta") or "").strip()
        certificado_clave = (datos.get("certificado_clave") or "").strip()
        endpoint_beta = (datos.get("endpoint_beta") or SUNAT_BETA_ENDPOINT).strip()

        if len(ruc) != 11:
            return {"ok": False, "mensaje": "El RUC del emisor debe tener 11 digitos."}
        if not razon_social:
            return {"ok": False, "mensaje": "Ingrese la razon social del emisor."}
        if not nombre_comercial:
            nombre_comercial = "CCPL"
        if not direccion:
            return {"ok": False, "mensaje": "Ingrese la direccion fiscal del emisor."}

        if not usuario_sol:
            return {"ok": False, "mensaje": "Ingrese el usuario SOL secundario."}
        if not certificado_ruta:
            return {"ok": False, "mensaje": "Suba el certificado digital .pfx o .p12."}
        if not Path(certificado_ruta).exists():
            return {
                "ok": False,
                "mensaje": "No se encontró el certificado digital guardado.",
            }
        if not endpoint_beta:
            return {"ok": False, "mensaje": "Ingrese el endpoint de SUNAT beta."}

        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    config = _obtener_config_facturacion(cursor, bloquear=True)
                    if not clave_sol:
                        clave_sol = config.get("clave_sol") or ""
                    if not certificado_clave:
                        certificado_clave = config.get("certificado_clave") or ""

                    if not clave_sol:
                        return {"ok": False, "mensaje": "Ingrese la clave SOL."}
                    if not certificado_clave:
                        return {"ok": False, "mensaje": "Ingrese la clave del certificado."}

                    sql =  " UPDATE configuracion_facturacion "
                    sql += "    SET ruc = %s, razon_social = %s, "
                    sql += "        nombre_comercial = %s, direccion = %s, "
                    sql += "        serie_boleta = %s, serie_factura = %s, "
                    sql += "        modo_envio = %s, usuario_sol = %s, "
                    sql += "        clave_sol = %s, certificado_ruta = %s, "
                    sql += "        certificado_clave = %s, endpoint_beta = %s "
                    sql += "  WHERE id = %s "
                    cursor.execute(sql, (
                        ruc,
                        razon_social,
                        nombre_comercial,
                        direccion,
                        serie_boleta,
                        serie_factura,
                        modo,
                        usuario_sol,
                        clave_sol,
                        certificado_ruta,
                        certificado_clave,
                        endpoint_beta,
                        config["id"],
                    ))
                conn.commit()
            return {
                "ok": True,
                "mensaje": "Configuracion de facturacion actualizada.",
                "modo": modo,
            }
        return {"ok": False, "mensaje": "No se pudo conectar con la base de datos."}
    except Exception as e:
        print(repr(e))
        if _facturacion_tablas_no_existen(e):
            return {
                "ok": False,
                "mensaje": "Actualice la base con database/alter_sunat_beta.sql.",
            }
        return {"ok": False, "mensaje": "No se pudo guardar la configuracion SUNAT."}


def _tipo_documento_cliente(documento):
    doc = str(documento or "").strip()
    if len(doc) == 11 and doc.isdigit():
        return "RUC"
    if len(doc) == 8 and doc.isdigit():
        return "DNI"
    return "Documento"


def _numero_comprobante_fiscal(fila):
    return (
        str(fila.get("serie") or "") + "-" +
        str(fila.get("numero") or 0).zfill(8)
    )


def _registrar_log_facturacion(cursor, comprobante_id, accion, estado,
                               mensaje, payload=None):
    data = ""
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False)
    sql =  " INSERT INTO facturacion_sunat_logs "
    sql += " (comprobante_fiscal_id, accion, estado, mensaje, payload) "
    sql += " VALUES (%s, %s, %s, %s, %s) "
    cursor.execute(sql, (comprobante_id, accion, estado, mensaje, data))


def _filtros_facturacion(p_estado=None, p_busqueda=None):
    filtros = []
    params = []
    if p_estado:
        filtros.append("cf.estado = %s")
        params.append(p_estado)
    if p_busqueda:
        like = f"%{p_busqueda}%"
        filtros.append(
            "(cf.cliente_nombre LIKE %s OR c.matricula LIKE %s OR "
            "cf.concepto LIKE %s OR "
            "CONCAT(cf.serie, '-', LPAD(cf.numero, 8, '0')) LIKE %s OR "
            "cf.ticket_sunat LIKE %s)"
        )
        params.extend([like, like, like, like, like])
    return filtros, params


def contar_comprobantes_fiscales(p_estado=None, p_busqueda=None):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT COUNT(*) AS total "
                    sql += "   FROM comprobantes_fiscales cf "
                    sql += "   JOIN colegiados c ON c.id = cf.colegiado_id "
                    filtros, params = _filtros_facturacion(p_estado, p_busqueda)
                    if filtros:
                        sql += " WHERE " + " AND ".join(filtros)
                    cursor.execute(sql, tuple(params))
                    fila = cursor.fetchone() or {}
                    return fila.get("total", 0) or 0
        return 0
    except Exception as e:
        if _facturacion_tablas_no_existen(e):
            return 0
        raise


def leer_comprobantes_fiscales(p_estado=None, p_busqueda=None,
                               p_limite=None, p_offset=0):
    try:
        conn = obtenerconexion()
        result = []
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT cf.id, cf.comprobante_pago_id, "
                    sql += "        cf.tipo_comprobante, cf.serie, cf.numero, "
                    sql += "        cf.fecha_emision, cf.enviado_en, "
                    sql += "        cf.cliente_nombre, cf.numero_documento_cliente, "
                    sql += "        cf.concepto, cf.subtotal, cf.igv, cf.total, "
                    sql += "        cf.moneda, cf.estado, cf.ticket_sunat, "
                    sql += "        cf.codigo_sunat, cf.cdr_estado, "
                    sql += "        cf.emitido_por_nombre, cf.emitido_por_matricula, "
                    sql += "        cf.anulado_por_nombre, cf.anulado_por_matricula, "
                    sql += "        cf.motivo_anulacion, cf.anulado_en, "
                    sql += "        c.nombre, c.matricula, cp.estado AS estado_interno "
                    sql += "   FROM comprobantes_fiscales cf "
                    sql += "   JOIN colegiados c ON c.id = cf.colegiado_id "
                    sql += "   JOIN comprobantes_pago cp ON cp.id = cf.comprobante_pago_id "
                    filtros, params = _filtros_facturacion(p_estado, p_busqueda)
                    if filtros:
                        sql += " WHERE " + " AND ".join(filtros)
                    sql += "  ORDER BY cf.fecha_emision DESC, cf.id DESC "
                    if p_limite:
                        limite = max(1, min(int(p_limite), 100))
                        offset = max(0, int(p_offset or 0))
                        sql += " LIMIT %s OFFSET %s "
                        params.extend([limite, offset])
                    cursor.execute(sql, tuple(params))
                    result = cursor.fetchall()
        return result
    except Exception as e:
        if _facturacion_tablas_no_existen(e):
            return []
        raise


def resumir_facturacion():
    resumen = {
        "total": 0,
        "pendientes": 0,
        "aceptados": 0,
        "anulados": 0,
        "rechazados": 0,
        "monto_emitido": 0,
        "monto_aceptado": 0,
        "por_estado": [],
    }
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT COUNT(*) AS total, "
                        "COALESCE(SUM(CASE WHEN estado = 'Pendiente' THEN 1 ELSE 0 END), 0) AS pendientes, "
                        "COALESCE(SUM(CASE WHEN estado = 'Aceptado' THEN 1 ELSE 0 END), 0) AS aceptados, "
                        "COALESCE(SUM(CASE WHEN estado = 'Anulado' THEN 1 ELSE 0 END), 0) AS anulados, "
                        "COALESCE(SUM(CASE WHEN estado = 'Rechazado' THEN 1 ELSE 0 END), 0) AS rechazados, "
                        "COALESCE(SUM(CASE WHEN estado <> 'Anulado' THEN total ELSE 0 END), 0) AS monto_emitido, "
                        "COALESCE(SUM(CASE WHEN estado = 'Aceptado' THEN total ELSE 0 END), 0) AS monto_aceptado "
                        "FROM comprobantes_fiscales"
                    )
                    fila = cursor.fetchone() or {}
                    resumen.update(fila)
                    cursor.execute(
                        "SELECT estado, COUNT(*) AS total, "
                        "COALESCE(SUM(total), 0) AS monto "
                        "FROM comprobantes_fiscales "
                        "GROUP BY estado "
                        "ORDER BY total DESC"
                    )
                    resumen["por_estado"] = cursor.fetchall()
        return resumen
    except Exception as e:
        if _facturacion_tablas_no_existen(e):
            return resumen
        raise


def leer_comprobante_fiscal_admin(p_id):
    data = {"comprobante": None, "detalle": [], "logs": []}
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT cf.*, c.nombre, c.matricula, c.documento, "
                    sql += "        c.correo, cp.serie AS interno_serie, "
                    sql += "        cp.numero AS interno_numero, "
                    sql += "        cp.estado AS interno_estado, tp.metodo, "
                    sql += "        tp.codigo_transaccion, tp.codigo_autorizacion "
                    sql += "   FROM comprobantes_fiscales cf "
                    sql += "   JOIN colegiados c ON c.id = cf.colegiado_id "
                    sql += "   JOIN comprobantes_pago cp ON cp.id = cf.comprobante_pago_id "
                    sql += "   JOIN transacciones_pago tp ON tp.id = cf.transaccion_id "
                    sql += "  WHERE cf.id = %s "
                    cursor.execute(sql, (p_id,))
                    data["comprobante"] = cursor.fetchone()
                    if not data["comprobante"]:
                        return data

                    cursor.execute(
                        "SELECT id, descripcion, cantidad, valor_unitario, "
                        "       subtotal, igv, total "
                        "FROM comprobante_fiscal_detalle "
                        "WHERE comprobante_fiscal_id = %s "
                        "ORDER BY id ASC",
                        (p_id,))
                    data["detalle"] = cursor.fetchall()

                    cursor.execute(
                        "SELECT accion, estado, mensaje, payload, creado_en "
                        "FROM facturacion_sunat_logs "
                        "WHERE comprobante_fiscal_id = %s "
                        "ORDER BY creado_en DESC, id DESC",
                        (p_id,))
                    data["logs"] = cursor.fetchall()
        return data
    except Exception as e:
        if _facturacion_tablas_no_existen(e):
            return data
        raise


def emitir_comprobante_fiscal_desde_interno(p_comprobante_pago_id,
                                            p_tipo_comprobante=None,
                                            p_usuario_matricula=None,
                                            p_usuario_nombre=None):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT cp.id AS comprobante_pago_id, "
                    sql += "        cp.transaccion_id, cp.cuota_id, cp.colegiado_id, "
                    sql += "        cp.concepto, cp.subtotal, cp.igv, cp.total, "
                    sql += "        cp.moneda, cp.estado, c.nombre, c.matricula, "
                    sql += "        c.documento, c.correo "
                    sql += "   FROM comprobantes_pago cp "
                    sql += "   JOIN colegiados c ON c.id = cp.colegiado_id "
                    sql += "  WHERE cp.id = %s "
                    sql += "  FOR UPDATE "
                    cursor.execute(sql, (p_comprobante_pago_id,))
                    comprobante = cursor.fetchone()
                    if not comprobante:
                        return {"ok": False, "mensaje": "No se encontró el comprobante interno."}
                    if comprobante.get("estado") != "Emitido":
                        return {
                            "ok": False,
                            "mensaje": "Solo se puede facturar un comprobante interno emitido.",
                        }

                    cursor.execute(
                        "SELECT id, serie, numero, estado "
                        "FROM comprobantes_fiscales "
                        "WHERE comprobante_pago_id = %s "
                        "LIMIT 1",
                        (p_comprobante_pago_id,))
                    existente = cursor.fetchone()
                    if existente:
                        return {
                            "ok": False,
                            "mensaje": (
                                "Este pago ya tiene comprobante fiscal " +
                                _numero_comprobante_fiscal(existente) + "."
                            ),
                            "comprobante_id": existente.get("id"),
                        }

                    doc_cliente = str(comprobante.get("documento") or "").strip()
                    tipo_doc_cliente = _tipo_documento_cliente(doc_cliente)
                    tipo = (p_tipo_comprobante or "").strip()
                    if tipo not in ["Boleta", "Factura"]:
                        tipo = "Factura" if tipo_doc_cliente == "RUC" else "Boleta"
                    if tipo == "Factura" and tipo_doc_cliente != "RUC":
                        return {
                            "ok": False,
                            "mensaje": "Para emitir factura el colegiado debe tener RUC de 11 digitos.",
                        }

                    config = _obtener_config_facturacion(cursor, bloquear=True)
                    if tipo == "Factura":
                        serie = config.get("serie_factura") or "F001"
                        numero = int(config.get("correlativo_factura") or 1)
                        campo_correlativo = "correlativo_factura"
                    else:
                        serie = config.get("serie_boleta") or "B001"
                        numero = int(config.get("correlativo_boleta") or 1)
                        campo_correlativo = "correlativo_boleta"

                    usuario_matricula = p_usuario_matricula or "admin"
                    usuario_nombre = p_usuario_nombre or "Administrador CCPL"
                    hash_doc = uuid4().hex.upper()
                    payload = {
                        "modo": config.get("modo_envio") or "SUNAT_BETA",
                        "emisor": {
                            "ruc": config.get("ruc"),
                            "razon_social": config.get("razon_social"),
                        },
                        "cliente": {
                            "tipo_documento": tipo_doc_cliente,
                            "numero_documento": doc_cliente,
                            "nombre": comprobante.get("nombre"),
                        },
                        "comprobante": {
                            "tipo": tipo,
                            "serie": serie,
                            "numero": numero,
                            "moneda": comprobante.get("moneda") or "PEN",
                            "total": float(comprobante.get("total") or 0),
                        },
                    }

                    sql =  " INSERT INTO comprobantes_fiscales "
                    sql += " (comprobante_pago_id, transaccion_id, cuota_id, "
                    sql += "  colegiado_id, tipo_comprobante, serie, numero, "
                    sql += "  fecha_emision, tipo_documento_cliente, "
                    sql += "  numero_documento_cliente, cliente_nombre, "
                    sql += "  cliente_correo, concepto, subtotal, igv, total, "
                    sql += "  moneda, estado, codigo_hash, json_envio, "
                    sql += "  emitido_por_matricula, emitido_por_nombre) "
                    sql += " VALUES (%s, %s, %s, %s, %s, %s, %s, CURDATE(), "
                    sql += "         %s, %s, %s, %s, %s, %s, %s, %s, %s, "
                    sql += "         'Pendiente', %s, %s, %s, %s) "
                    cursor.execute(sql, (
                        comprobante["comprobante_pago_id"],
                        comprobante["transaccion_id"],
                        comprobante["cuota_id"],
                        comprobante["colegiado_id"],
                        tipo,
                        serie,
                        numero,
                        tipo_doc_cliente,
                        doc_cliente,
                        comprobante["nombre"],
                        comprobante.get("correo"),
                        comprobante["concepto"],
                        comprobante.get("subtotal") or 0,
                        comprobante.get("igv") or 0,
                        comprobante.get("total") or 0,
                        comprobante.get("moneda") or "PEN",
                        hash_doc,
                        json.dumps(payload, ensure_ascii=False),
                        usuario_matricula,
                        usuario_nombre,
                    ))
                    fiscal_id = cursor.lastrowid

                    sql =  " INSERT INTO comprobante_fiscal_detalle "
                    sql += " (comprobante_fiscal_id, descripcion, cantidad, "
                    sql += "  valor_unitario, subtotal, igv, total) "
                    sql += " VALUES (%s, %s, 1.00, %s, %s, %s, %s) "
                    cursor.execute(sql, (
                        fiscal_id,
                        comprobante["concepto"],
                        comprobante.get("subtotal") or comprobante.get("total") or 0,
                        comprobante.get("subtotal") or 0,
                        comprobante.get("igv") or 0,
                        comprobante.get("total") or 0,
                    ))

                    cursor.execute(
                        "UPDATE configuracion_facturacion "
                        "SET " + campo_correlativo + " = " + campo_correlativo + " + 1 "
                        "WHERE id = %s",
                        (config["id"],))

                    _registrar_log_facturacion(
                        cursor,
                        fiscal_id,
                        "EMISION",
                        "Pendiente",
                        "Comprobante fiscal creado para envio SUNAT beta.",
                        payload
                    )
                conn.commit()
            return {
                "ok": True,
                "mensaje": "Comprobante fiscal creado.",
                "comprobante_id": fiscal_id,
                "numero": serie + "-" + str(numero).zfill(8),
            }
        return {"ok": False, "mensaje": "No se pudo conectar con la base de datos."}
    except Exception as e:
        print(repr(e))
        if _facturacion_tablas_no_existen(e):
            return {
                "ok": False,
                "mensaje": "Actualice la base con database/schema.sql.",
            }
        return {"ok": False, "mensaje": "No se pudo emitir el comprobante fiscal."}


def enviar_comprobante_fiscal_sunat(p_id, p_usuario_matricula=None,
                                    p_usuario_nombre=None):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    config = _obtener_config_facturacion(cursor, bloquear=False)
                    cursor.execute(
                        "SELECT cf.*, cp.serie AS interno_serie, "
                        "       cp.numero AS interno_numero "
                        "FROM comprobantes_fiscales cf "
                        "JOIN comprobantes_pago cp ON cp.id = cf.comprobante_pago_id "
                        "WHERE cf.id = %s FOR UPDATE",
                        (p_id,))
                    comprobante = cursor.fetchone()
                    if not comprobante:
                        return {"ok": False, "mensaje": "No se encontró el comprobante fiscal."}
                    if comprobante["estado"] == "Anulado":
                        return {"ok": False, "mensaje": "No se puede enviar un comprobante anulado."}
                    if comprobante["estado"] == "Aceptado":
                        return {"ok": False, "mensaje": "El comprobante ya fue aceptado por SUNAT."}

                    numero = _numero_comprobante_fiscal(comprobante)
                    modo = str(config.get("modo_envio") or "SUNAT_BETA").upper()
                    if modo != "SUNAT_BETA":
                        _registrar_log_facturacion(
                            cursor,
                            p_id,
                            "SUNAT_BETA",
                            "Rechazado",
                            "La facturacion debe estar configurada en modo SUNAT_BETA.",
                            {"modo_actual": modo, "comprobante": numero}
                        )
                        conn.commit()
                        return {
                            "ok": False,
                            "mensaje": "Active SUNAT_BETA en la configuracion de facturacion.",
                        }

                    cursor.execute(
                        "SELECT descripcion, cantidad, valor_unitario, "
                        "       subtotal, igv, total "
                        "FROM comprobante_fiscal_detalle "
                        "WHERE comprobante_fiscal_id = %s "
                        "ORDER BY id ASC",
                        (p_id,))
                    detalle = cursor.fetchall() or []
                    try:
                        respuesta_beta = enviar_comprobante_sunat_beta(
                            config,
                            comprobante,
                            detalle,
                            Path("static") / "uploads" / "sunat",
                        )
                    except SunatBetaError as exc:
                        payload_error = {
                            "modo": "SUNAT_BETA",
                            "comprobante": numero,
                            "error": str(exc),
                        }
                        _registrar_log_facturacion(
                            cursor,
                            p_id,
                            "SUNAT_BETA",
                            "Rechazado",
                            str(exc),
                            payload_error
                        )
                        conn.commit()
                        return {"ok": False, "mensaje": str(exc)}

                    estado_beta = "Aceptado" if respuesta_beta.get("aceptado") else "Rechazado"
                    sql =  " UPDATE comprobantes_fiscales "
                    sql += "    SET estado = %s, enviado_en = NOW(), "
                    sql += "        ticket_sunat = %s, codigo_sunat = %s, "
                    sql += "        cdr_estado = %s, cdr_descripcion = %s, "
                    sql += "        xml_archivo = %s, respuesta_sunat = %s "
                    sql += "  WHERE id = %s "
                    cursor.execute(sql, (
                        estado_beta,
                        respuesta_beta.get("ticket") or respuesta_beta.get("nombre_zip") or "",
                        respuesta_beta.get("codigo") or "",
                        respuesta_beta.get("cdr_estado") or estado_beta,
                        respuesta_beta.get("cdr_descripcion") or "",
                        respuesta_beta.get("xml_archivo") or "",
                        respuesta_beta.get("json") or json.dumps(respuesta_beta, ensure_ascii=False),
                        p_id,
                    ))
                    _registrar_log_facturacion(
                        cursor,
                        p_id,
                        "SUNAT_BETA",
                        estado_beta,
                        respuesta_beta.get("cdr_descripcion") or "Respuesta recibida de SUNAT beta.",
                        respuesta_beta
                    )
                conn.commit()
            if estado_beta == "Aceptado":
                return {
                    "ok": True,
                    "mensaje": "Comprobante aceptado por SUNAT beta.",
                    "numero": numero,
                    "modo": "SUNAT_BETA",
                }
            return {
                "ok": False,
                "mensaje": (
                    respuesta_beta.get("cdr_descripcion") or
                    "SUNAT beta rechazo el comprobante."
                ),
            }
        return {"ok": False, "mensaje": "No se pudo conectar con la base de datos."}
    except Exception as e:
        print(repr(e))
        if _facturacion_tablas_no_existen(e):
            return {
                "ok": False,
                "mensaje": "Actualice la base con database/schema.sql.",
            }
        return {"ok": False, "mensaje": "No se pudo enviar el comprobante fiscal."}


def anular_comprobante_fiscal(p_id, p_usuario_matricula=None,
                              p_usuario_nombre=None, p_motivo=None):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT id, tipo_comprobante, serie, numero, estado, "
                        "       cliente_nombre "
                        "FROM comprobantes_fiscales "
                        "WHERE id = %s FOR UPDATE",
                        (p_id,))
                    comprobante = cursor.fetchone()
                    if not comprobante:
                        return {"ok": False, "mensaje": "No se encontró el comprobante fiscal."}
                    if comprobante["estado"] == "Anulado":
                        return {"ok": False, "mensaje": "El comprobante fiscal ya está anulado."}
                    motivo = (p_motivo or "").strip()
                    if len(motivo) < 5:
                        return {
                            "ok": False,
                            "mensaje": "Ingrese un motivo de anulación mas detallado.",
                        }

                    usuario_matricula = p_usuario_matricula or "admin"
                    usuario_nombre = p_usuario_nombre or "Administrador CCPL"
                    numero = _numero_comprobante_fiscal(comprobante)
                    payload = {
                        "modo": "SUNAT_BETA",
                        "accion": "ANULACION_LOCAL",
                        "comprobante": numero,
                        "motivo": motivo,
                    }
                    sql =  " UPDATE comprobantes_fiscales "
                    sql += "    SET estado = 'Anulado', "
                    sql += "        anulado_por_matricula = %s, "
                    sql += "        anulado_por_nombre = %s, "
                    sql += "        motivo_anulacion = %s, "
                    sql += "        anulado_en = NOW(), "
                    sql += "        cdr_estado = 'Anulado local', "
                    sql += "        cdr_descripcion = 'Anulación registrada localmente. Baja SUNAT pendiente.', "
                    sql += "        respuesta_sunat = %s "
                    sql += "  WHERE id = %s "
                    cursor.execute(sql, (
                        usuario_matricula,
                        usuario_nombre,
                        motivo,
                        json.dumps(payload, ensure_ascii=False),
                        p_id,
                    ))
                    _registrar_log_facturacion(
                        cursor,
                        p_id,
                        "ANULACION_LOCAL",
                        "Anulado",
                        "Comprobante fiscal anulado localmente.",
                        payload
                    )
                conn.commit()
            return {
                "ok": True,
                "mensaje": "Comprobante fiscal anulado.",
                "numero": numero,
            }
        return {"ok": False, "mensaje": "No se pudo conectar con la base de datos."}
    except Exception as e:
        print(repr(e))
        if _facturacion_tablas_no_existen(e):
            return {
                "ok": False,
                "mensaje": "Actualice la base con database/schema.sql.",
            }
        return {"ok": False, "mensaje": "No se pudo anular el comprobante fiscal."}

# ============================================================
# FUNCIONES CRUD - FACTURACION
# ============================================================

def leer_configuraciones_facturacion_crud():
    return _leer_registros_crud("configuracion_facturacion")


def leer_configuracion_facturacion_por_id(p_id):
    return _leer_registro_por_id("configuracion_facturacion", p_id)


def insertar_configuracion_facturacion_crud(p_datos):
    columnas = [
        "ruc", "razon_social", "nombre_comercial", "direccion",
        "serie_boleta", "serie_factura", "correlativo_boleta",
        "correlativo_factura", "modo_envio", "usuario_sol", "clave_sol",
        "certificado_ruta", "certificado_clave", "endpoint_beta",
        "activo", "actualizado_en"
    ]
    return _insertar_registro_crud("configuracion_facturacion", p_datos, columnas)


def actualizar_configuracion_facturacion_crud(p_datos):
    columnas = [
        "ruc", "razon_social", "nombre_comercial", "direccion",
        "serie_boleta", "serie_factura", "correlativo_boleta",
        "correlativo_factura", "modo_envio", "usuario_sol", "clave_sol",
        "certificado_ruta", "certificado_clave", "endpoint_beta",
        "activo", "actualizado_en"
    ]
    return _actualizar_registro_crud("configuracion_facturacion", p_datos, columnas)


def eliminar_configuracion_facturacion(p_id):
    return _eliminar_registro_crud("configuracion_facturacion", p_id)


def insertar_comprobante_fiscal_crud(p_datos):
    columnas = [
        "comprobante_pago_id", "transaccion_id", "cuota_id", "colegiado_id",
        "tipo_comprobante", "serie", "numero", "fecha_emision", "enviado_en",
        "tipo_documento_cliente", "numero_documento_cliente", "cliente_nombre",
        "cliente_correo", "concepto", "subtotal", "igv", "total", "moneda",
        "estado", "ticket_sunat", "codigo_sunat", "cdr_estado",
        "cdr_descripcion", "codigo_hash", "xml_archivo", "pdf_archivo",
        "json_envio", "respuesta_sunat", "emitido_por_matricula",
        "emitido_por_nombre", "anulado_por_matricula", "anulado_por_nombre",
        "motivo_anulacion", "anulado_en"
    ]
    return _insertar_registro_crud("comprobantes_fiscales", p_datos, columnas)


def actualizar_comprobante_fiscal_crud(p_datos):
    columnas = [
        "comprobante_pago_id", "transaccion_id", "cuota_id", "colegiado_id",
        "tipo_comprobante", "serie", "numero", "fecha_emision", "enviado_en",
        "tipo_documento_cliente", "numero_documento_cliente", "cliente_nombre",
        "cliente_correo", "concepto", "subtotal", "igv", "total", "moneda",
        "estado", "ticket_sunat", "codigo_sunat", "cdr_estado",
        "cdr_descripcion", "codigo_hash", "xml_archivo", "pdf_archivo",
        "json_envio", "respuesta_sunat", "emitido_por_matricula",
        "emitido_por_nombre", "anulado_por_matricula", "anulado_por_nombre",
        "motivo_anulacion", "anulado_en"
    ]
    return _actualizar_registro_crud("comprobantes_fiscales", p_datos, columnas)


def eliminar_comprobante_fiscal(p_id):
    return _eliminar_registro_crud("comprobantes_fiscales", p_id)


def leer_comprobantes_fiscales_detalle_crud():
    return _leer_registros_crud("comprobante_fiscal_detalle")


def leer_comprobante_fiscal_detalle_por_id(p_id):
    return _leer_registro_por_id("comprobante_fiscal_detalle", p_id)


def insertar_comprobante_fiscal_detalle_crud(p_datos):
    columnas = [
        "comprobante_fiscal_id", "descripcion", "cantidad", "valor_unitario",
        "subtotal", "igv", "total"
    ]
    return _insertar_registro_crud("comprobante_fiscal_detalle", p_datos, columnas)


def actualizar_comprobante_fiscal_detalle_crud(p_datos):
    columnas = [
        "comprobante_fiscal_id", "descripcion", "cantidad", "valor_unitario",
        "subtotal", "igv", "total"
    ]
    return _actualizar_registro_crud("comprobante_fiscal_detalle", p_datos, columnas)


def eliminar_comprobante_fiscal_detalle(p_id):
    return _eliminar_registro_crud("comprobante_fiscal_detalle", p_id)


def leer_facturacion_sunat_logs_crud():
    return _leer_registros_crud("facturacion_sunat_logs")


def leer_facturacion_sunat_log_por_id(p_id):
    return _leer_registro_por_id("facturacion_sunat_logs", p_id)


def insertar_facturacion_sunat_log_crud(p_datos):
    columnas = ["comprobante_fiscal_id", "accion", "estado", "mensaje", "payload"]
    return _insertar_registro_crud("facturacion_sunat_logs", p_datos, columnas)


def actualizar_facturacion_sunat_log_crud(p_datos):
    columnas = ["comprobante_fiscal_id", "accion", "estado", "mensaje", "payload"]
    return _actualizar_registro_crud("facturacion_sunat_logs", p_datos, columnas)


def eliminar_facturacion_sunat_log(p_id):
    return _eliminar_registro_crud("facturacion_sunat_logs", p_id)
