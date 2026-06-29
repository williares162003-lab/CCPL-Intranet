import json
import re
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4
from bd import obtenerconexion
from admin_modelosAD import clsCuota
from admin_crudAD import (_leer_registro_por_id, _leer_registros_crud, _insertar_registro_crud, _actualizar_registro_crud, _eliminar_registro_crud)
from admin_cursosAD import _curso_monto_inhabil_sql, _condicion_habilidad_colegiado, _precio_curso_por_condicion

# ============================================================
# CUOTAS Y PAGOS
# ============================================================

def _filtros_cuotas(p_matricula=None, p_tipo=None, p_busqueda=None):
    filtros = []
    params = []
    if p_matricula:
        filtros.append("c.matricula = %s")
        params.append(p_matricula)
    if p_tipo:
        filtros.append("q.tipo = %s")
        params.append(p_tipo)
    if p_busqueda:
        filtros.append("(c.matricula LIKE %s OR c.nombre LIKE %s OR q.concepto LIKE %s)")
        like = f"%{p_busqueda}%"
        params.extend([like, like, like])
    return filtros, params


def leer_cuotas(p_matricula=None, p_tipo=None, p_busqueda=None,
                p_limite=None, p_offset=0):
    try:
        conn = obtenerconexion()
        result = None
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT q.id, q.fecha, q.fecha_emision, q.fecha_vencimiento, "
                    sql += "        q.fecha_pago, q.concepto, q.monto, q.estado, "
                    sql += "        q.tipo, q.periodo_mes, q.periodo_anio, "
                    sql += "        q.curso_id, q.inscripcion_id, "
                    sql += "        c.nombre, c.matricula "
                    sql += "   FROM cuotas q "
                    sql += "   JOIN colegiados c ON c.id = q.colegiado_id "
                    filtros, params = _filtros_cuotas(
                        p_matricula,
                        p_tipo,
                        p_busqueda
                    )
                    if filtros:
                        sql += " WHERE " + " AND ".join(filtros) + " "
                    sql += "  ORDER BY q.fecha DESC, q.id DESC "
                    if p_limite:
                        limite = max(1, min(int(p_limite), 100))
                        offset = max(0, int(p_offset or 0))
                        sql += " LIMIT %s OFFSET %s "
                        params.extend([limite, offset])
                    cursor.execute(sql, tuple(params))
                    result = cursor.fetchall()
        return result
    except Exception:
        raise


def contar_cuotas(p_matricula=None, p_tipo=None, p_busqueda=None):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT COUNT(*) AS total "
                    sql += "   FROM cuotas q "
                    sql += "   JOIN colegiados c ON c.id = q.colegiado_id "
                    filtros, params = _filtros_cuotas(
                        p_matricula,
                        p_tipo,
                        p_busqueda
                    )
                    if filtros:
                        sql += " WHERE " + " AND ".join(filtros) + " "
                    cursor.execute(sql, tuple(params))
                    fila = cursor.fetchone() or {}
                    return fila.get("total", 0) or 0
        return 0
    except Exception:
        raise


def resumir_cuotas(p_matricula=None, p_tipo=None, p_busqueda=None):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT COUNT(*) AS total, "
                    sql += "        COALESCE(SUM(CASE WHEN q.estado = 'Pendiente' THEN q.monto ELSE 0 END), 0) AS total_pendiente, "
                    sql += "        COALESCE(SUM(CASE WHEN q.estado = 'Pagado' THEN q.monto ELSE 0 END), 0) AS total_pagado "
                    sql += "   FROM cuotas q "
                    sql += "   JOIN colegiados c ON c.id = q.colegiado_id "
                    filtros, params = _filtros_cuotas(
                        p_matricula,
                        p_tipo,
                        p_busqueda
                    )
                    if filtros:
                        sql += " WHERE " + " AND ".join(filtros) + " "
                    cursor.execute(sql, tuple(params))
                    return cursor.fetchone() or {
                        "total": 0,
                        "total_pendiente": 0,
                        "total_pagado": 0
                    }
        return {"total": 0, "total_pendiente": 0, "total_pagado": 0}
    except Exception:
        raise


def insertar_cuota(p_cuota):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT id FROM colegiados WHERE matricula = %s",
                                   (p_cuota.matricula,))
                    colegiado = cursor.fetchone()
                    if not colegiado:
                        return False

                    fecha_vencimiento = p_cuota.fecha_vencimiento or p_cuota.fecha
                    fecha_pago = p_cuota.fecha if p_cuota.estado == "Pagado" else None
                    sql =  "INSERT INTO `cuotas` "
                    sql += "(`colegiado_id`, `fecha`, `fecha_emision`, "
                    sql += " `fecha_vencimiento`, `fecha_pago`, `concepto`, `monto`, "
                    sql += " `estado`, `tipo`, `periodo_mes`, `periodo_anio`) "
                    sql += "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                    cursor.execute(sql, (colegiado["id"], p_cuota.fecha,
                                        p_cuota.fecha,
                                        fecha_vencimiento,
                                        fecha_pago,
                                        p_cuota.concepto, p_cuota.monto,
                                        p_cuota.estado, p_cuota.tipo,
                                        p_cuota.periodo_mes,
                                        p_cuota.periodo_anio))
                conn.commit()
            return True
        return False
    except Exception as e:
        print(repr(e))
        return False


def pagar_cuota(p_id):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT id AS cuota_id, colegiado_id, concepto, monto, "
                        "       estado AS cuota_estado, tipo, inscripcion_id "
                        "FROM cuotas WHERE id = %s",
                        (p_id,))
                    cuota = cursor.fetchone()
                    if not cuota:
                        return {"ok": False, "mensaje": "No se encontró la cuota."}
                    if cuota["cuota_estado"] != "Pendiente":
                        return {"ok": False, "mensaje": "La cuota ya no está pendiente."}

                    emision = _emitir_comprobante_desde_cuota(
                        cursor,
                        cuota,
                        "Registro administrativo",
                        "Pago administrativo",
                        "Pago marcado por administración."
                    )
                    if not emision.get("ok"):
                        conn.rollback()
                        return emision

                    sql =  "UPDATE `cuotas` "
                    sql += "   SET `estado` = 'Pagado', `fecha_pago` = CURDATE() "
                    sql += " WHERE `id` = %s "
                    cursor.execute(sql, (p_id,))

                    if cuota.get("inscripcion_id"):
                        sql2 =  "UPDATE inscripciones_curso "
                        sql2 += "   SET estado_pago = 'Pagado' "
                        sql2 += " WHERE id = %s "
                        cursor.execute(sql2, (cuota["inscripcion_id"],))
                    elif cuota and cuota["concepto"].startswith("Inscripción Curso: "):
                        titulo = cuota["concepto"].replace("Inscripción Curso: ", "", 1)
                        sql2 =  "UPDATE inscripciones_curso i "
                        sql2 += "  JOIN cursos cu ON cu.id = i.curso_id "
                        sql2 += "   SET i.estado_pago = 'Pagado' "
                        sql2 += " WHERE i.colegiado_id = %s AND cu.titulo = %s "
                        cursor.execute(sql2, (cuota["colegiado_id"], titulo))
                conn.commit()
            return {"ok": True, "mensaje": "La cuota fue marcada como pagada."}
        return {"ok": False, "mensaje": "No se pudo conectar con la base de datos."}
    except Exception as e:
        print(repr(e))
        if _pagos_demo_tablas_no_existen(e):
            return {
                "ok": False,
                "mensaje": "Actualice la base con database/schema.sql para emitir comprobantes."
            }
        return {"ok": False, "mensaje": "No se pudo marcar la cuota como pagada."}


def eliminar_cuota(p_id):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute("SHOW TABLES LIKE 'comprobantes_pago'")
                    if cursor.fetchone():
                        cursor.execute(
                            "SELECT id FROM comprobantes_pago WHERE cuota_id = %s LIMIT 1",
                            (p_id,))
                        if cursor.fetchone():
                            return {
                                "ok": False,
                                "mensaje": "No se puede eliminar la cuota porque tiene comprobantes registrados.",
                            }

                    cursor.execute("SHOW TABLES LIKE 'transacciones_pago'")
                    if cursor.fetchone():
                        cursor.execute(
                            "SELECT id FROM transacciones_pago WHERE cuota_id = %s LIMIT 1",
                            (p_id,))
                        if cursor.fetchone():
                            return {
                                "ok": False,
                                "mensaje": "No se puede eliminar la cuota porque tiene transacciones registradas.",
                            }

                    cursor.execute("DELETE FROM `cuotas` WHERE `id` = %s", (p_id,))
                conn.commit()
            return {"ok": True, "mensaje": "La cuota fue eliminada correctamente."}
        return {"ok": False, "mensaje": "No se pudo conectar con la base de datos."}
    except Exception as e:
        print(repr(e))
        return {"ok": False, "mensaje": "No se pudo eliminar la cuota."}


def leer_historial_cuota_admin(p_id):
    data = {
        "cuota": None,
        "evidencias": [],
        "transacciones": [],
        "comprobantes": [],
    }
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT q.id, q.fecha, q.fecha_emision, q.fecha_vencimiento, "
                    sql += "        q.fecha_pago, q.concepto, q.monto, q.estado, "
                    sql += "        q.tipo, q.periodo_mes, q.periodo_anio, "
                    sql += "        q.creado_en, c.nombre, c.matricula, c.documento, "
                    sql += "        c.correo, c.estado AS estado_colegiado "
                    sql += "   FROM cuotas q "
                    sql += "   JOIN colegiados c ON c.id = q.colegiado_id "
                    sql += "  WHERE q.id = %s "
                    cursor.execute(sql, (p_id,))
                    data["cuota"] = cursor.fetchone()
                    if not data["cuota"]:
                        return data

                    tiene_auditoria = _evidencias_tiene_auditoria(cursor)
                    auditoria_sql = (
                        "accion_revision, revisado_por_matricula, "
                        "revisado_por_nombre, detalle_revision, revisado_en"
                    )
                    if not tiene_auditoria:
                        auditoria_sql = (
                            "NULL AS accion_revision, NULL AS revisado_por_matricula, "
                            "NULL AS revisado_por_nombre, NULL AS detalle_revision, "
                            "NULL AS revisado_en"
                        )
                    sql =  " SELECT id, medio_pago_id, fecha_pago, numero_operacion, "
                    sql += "        monto, comentario, archivo, estado, creado_en, "
                    sql += "        " + auditoria_sql + " "
                    sql += "   FROM evidencias_pago "
                    sql += "  WHERE cuota_id = %s "
                    sql += "  ORDER BY creado_en DESC, id DESC "
                    cursor.execute(sql, (p_id,))
                    data["evidencias"] = cursor.fetchall()

                    cursor.execute("SHOW TABLES LIKE 'transacciones_pago'")
                    if cursor.fetchone():
                        tiene_evidencia = _transacciones_tiene_evidencia(cursor)
                        evidencia_sql = "evidencia_id" if tiene_evidencia else "NULL AS evidencia_id"
                        sql =  " SELECT id, proveedor, metodo, codigo_transaccion, "
                        sql += "        codigo_autorizacion, monto, moneda, estado, "
                        sql += "        respuesta_pasarela, pagado_en, creado_en, "
                        sql += "        " + evidencia_sql + " "
                        sql += "   FROM transacciones_pago "
                        sql += "  WHERE cuota_id = %s "
                        sql += "  ORDER BY creado_en DESC, id DESC "
                        cursor.execute(sql, (p_id,))
                        data["transacciones"] = cursor.fetchall()

                    cursor.execute("SHOW TABLES LIKE 'comprobantes_pago'")
                    if cursor.fetchone():
                        tiene_anulacion = _comprobantes_tiene_anulacion(cursor)
                        tiene_evidencia = _comprobantes_tiene_evidencia(cursor)
                        auditoria_comp = (
                            "anulado_por_matricula, anulado_por_nombre, "
                            "motivo_anulacion, anulado_en"
                        )
                        if not tiene_anulacion:
                            auditoria_comp = (
                                "NULL AS anulado_por_matricula, NULL AS anulado_por_nombre, "
                                "NULL AS motivo_anulacion, NULL AS anulado_en"
                            )
                        evidencia_sql = "evidencia_id" if tiene_evidencia else "NULL AS evidencia_id"
                        sql =  " SELECT id, transaccion_id, tipo_comprobante, serie, "
                        sql += "        numero, fecha_emision, concepto, subtotal, igv, "
                        sql += "        total, moneda, estado, codigo_hash, creado_en, "
                        sql += "        " + evidencia_sql + ", " + auditoria_comp + " "
                        sql += "   FROM comprobantes_pago "
                        sql += "  WHERE cuota_id = %s "
                        sql += "  ORDER BY creado_en DESC, id DESC "
                        cursor.execute(sql, (p_id,))
                        data["comprobantes"] = cursor.fetchall()
        return data
    except Exception:
        raise

# ============================================================
# PROCESAMIENTO DE CUOTAS
# ============================================================

def _sumar_un_mes(p_anio, p_mes):
    if p_mes == 12:
        return p_anio + 1, 1
    return p_anio, p_mes + 1


def _ultimo_dia_mes(p_anio, p_mes):
    if p_mes == 12:
        siguiente = date(p_anio + 1, 1, 1)
    else:
        siguiente = date(p_anio, p_mes + 1, 1)
    return siguiente - timedelta(days=1)


def _nombre_mes(p_mes):
    meses = [
        "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    return meses[int(p_mes)] if p_mes else ""


def obtener_resumen_cuotas_mensuales():
    try:
        conn = obtenerconexion()
        hoy = date.today()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT COUNT(*) AS total FROM colegiados WHERE estado = 'Vigente'"
                    )
                    vigentes = (cursor.fetchone() or {}).get("total", 0) or 0

                    sql =  " SELECT q.periodo_anio, q.periodo_mes, "
                    sql += "        COUNT(DISTINCT q.colegiado_id) AS total "
                    sql += "   FROM cuotas q "
                    sql += "   JOIN colegiados c ON c.id = q.colegiado_id "
                    sql += "  WHERE q.tipo = 'mensual' "
                    sql += "    AND c.estado = 'Vigente' "
                    sql += "    AND q.periodo_anio IS NOT NULL "
                    sql += "    AND q.periodo_mes IS NOT NULL "
                    sql += "    AND (q.periodo_anio < %s "
                    sql += "      OR (q.periodo_anio = %s AND q.periodo_mes <= %s)) "
                    sql += "  GROUP BY q.periodo_anio, q.periodo_mes "
                    sql += " HAVING COUNT(DISTINCT q.colegiado_id) >= %s "
                    sql += "  ORDER BY q.periodo_anio DESC, q.periodo_mes DESC "
                    sql += "  LIMIT 1 "
                    cursor.execute(sql, (hoy.year, hoy.year, hoy.month, vigentes))
                    ultimo_completo = cursor.fetchone()

                    if ultimo_completo:
                        siguiente_anio, siguiente_mes = _sumar_un_mes(
                            int(ultimo_completo["periodo_anio"]),
                            int(ultimo_completo["periodo_mes"])
                        )
                    else:
                        siguiente_anio, siguiente_mes = hoy.year, hoy.month

                    cursor.execute(
                        "SELECT COUNT(DISTINCT q.colegiado_id) AS total "
                        "FROM cuotas q "
                        "JOIN colegiados c ON c.id = q.colegiado_id "
                        "WHERE q.tipo = 'mensual' "
                        "AND c.estado = 'Vigente' "
                        "AND q.periodo_anio = %s AND q.periodo_mes = %s",
                        (siguiente_anio, siguiente_mes))
                    existentes = (cursor.fetchone() or {}).get("total", 0) or 0
                    faltantes = max(int(vigentes) - int(existentes), 0)

                    es_futuro = (
                        siguiente_anio > hoy.year or
                        (siguiente_anio == hoy.year and siguiente_mes > hoy.month)
                    )
                    puede_procesar = (
                        not es_futuro and
                        int(vigentes) > 0 and
                        faltantes > 0
                    )

                    return {
                        "ultimo_anio": (
                            ultimo_completo.get("periodo_anio")
                            if ultimo_completo else None
                        ),
                        "ultimo_mes": (
                            ultimo_completo.get("periodo_mes")
                            if ultimo_completo else None
                        ),
                        "ultimo_label": (
                            f"{_nombre_mes(ultimo_completo.get('periodo_mes'))} {ultimo_completo.get('periodo_anio')}"
                            if ultimo_completo else "Sin periodos completos"
                        ),
                        "siguiente_anio": siguiente_anio,
                        "siguiente_mes": siguiente_mes,
                        "siguiente_label": f"{_nombre_mes(siguiente_mes)} {siguiente_anio}",
                        "colegiados_vigentes": vigentes,
                        "cuotas_existentes": existentes,
                        "faltantes": faltantes,
                        "puede_procesar": puede_procesar,
                        "mensaje": (
                            "No hay colegiados vigentes para procesar."
                            if int(vigentes) <= 0 else
                            "No hay periodos mensuales pendientes por procesar."
                            if es_futuro else
                            "Listo para procesar el siguiente periodo. Faltan " +
                            str(faltantes) + " colegiado(s)."
                        ),
                    }
        return None
    except Exception as e:
        print(repr(e))
        return None


def procesar_cuotas_mensuales(p_monto):
    try:
        monto = float(p_monto)
        if monto <= 0:
            return {"ok": False, "mensaje": "Ingrese un monto mensual mayor a cero."}

        resumen = obtener_resumen_cuotas_mensuales()
        if not resumen or not resumen.get("puede_procesar"):
            return {"ok": False, "mensaje": "No hay periodo mensual disponible para procesar."}

        anio = int(resumen["siguiente_anio"])
        mes = int(resumen["siguiente_mes"])
        emision = date(anio, mes, 1)
        vencimiento = _ultimo_dia_mes(anio, mes)
        concepto = f"Cuota Ordinaria - {_nombre_mes(mes)} {anio}"

        conn = obtenerconexion()
        generadas = 0
        existentes = 0
        notificaciones = []
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT id, matricula, nombre FROM colegiados WHERE estado = 'Vigente'"
                    )
                    colegiados = cursor.fetchall()

                    for colegiado in colegiados:
                        cursor.execute(
                            "SELECT id FROM cuotas "
                            "WHERE colegiado_id = %s AND tipo = 'mensual' "
                            "AND periodo_anio = %s AND periodo_mes = %s",
                            (colegiado["id"], anio, mes))
                        if cursor.fetchone():
                            existentes += 1
                            continue

                        sql =  "INSERT INTO cuotas "
                        sql += "(colegiado_id, fecha, fecha_emision, fecha_vencimiento, "
                        sql += " concepto, monto, estado, tipo, periodo_mes, periodo_anio) "
                        sql += "VALUES (%s, %s, %s, %s, %s, %s, 'Pendiente', 'mensual', %s, %s)"
                        cursor.execute(sql, (colegiado["id"], emision, emision,
                                            vencimiento, concepto, monto,
                                            mes, anio))
                        generadas += 1
                        notificaciones.append({
                            "matricula": colegiado["matricula"],
                            "nombre": colegiado.get("nombre", ""),
                            "concepto": concepto,
                            "monto": monto,
                            "periodo": f"{_nombre_mes(mes)} {anio}",
                            "vencimiento": vencimiento,
                        })
                conn.commit()
            return {
                "ok": True,
                "periodo": f"{_nombre_mes(mes)} {anio}",
                "generadas": generadas,
                "existentes": existentes,
                "vigentes": len(colegiados),
                "notificaciones": notificaciones,
            }
        return {"ok": False, "mensaje": "No se pudo conectar con la base de datos."}
    except Exception as e:
        print(repr(e))
        return {"ok": False, "mensaje": "No se pudieron procesar las cuotas mensuales."}


def obtener_resumen_pago_anual():
    hoy = date.today()
    habilitado = hoy.month in [1, 2, 3]
    monto_mensual = 80.00
    descuento = 10.00
    monto_total = monto_mensual * 12
    monto_descuento = monto_total * (descuento / 100)
    return {
        "anio": hoy.year,
        "habilitado": habilitado,
        "ventana_label": "Enero a marzo " + str(hoy.year),
        "mensaje": (
            "Disponible para registrar pago anual anticipado."
            if habilitado else
            "El pago anual anticipado solo se registra de enero a marzo."
        ),
        "monto_mensual": monto_mensual,
        "descuento": descuento,
        "monto_total": monto_total - monto_descuento,
    }


def registrar_pago_anual_anticipado(p_matricula, p_anio, p_monto_mensual,
                                    p_descuento=10):
    try:
        hoy = date.today()
        if hoy.month not in [1, 2, 3]:
            return {
                "ok": False,
                "mensaje": "El pago anual anticipado solo se puede registrar de enero a marzo."
            }

        try:
            anio = int(p_anio)
            monto = float(p_monto_mensual)
            descuento = float(p_descuento)
        except ValueError:
            return {
                "ok": False,
                "mensaje": "Ingrese un año, monto y descuento válidos."
            }

        if anio != hoy.year:
            return {
                "ok": False,
                "mensaje": "Solo se puede registrar el pago anual del año actual."
            }
        if monto <= 0:
            return {
                "ok": False,
                "mensaje": "Ingrese un monto mensual mayor a cero."
            }
        if descuento < 0 or descuento > 50:
            return {
                "ok": False,
                "mensaje": "El descuento anual debe estar entre 0% y 50%."
            }

        conn = obtenerconexion()
        generadas = 0
        actualizadas = 0
        ya_pagadas = 0
        comprobantes = 0
        monto_aplicado = round(monto * (1 - (descuento / 100)), 2)
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT id, matricula, nombre, estado "
                        "FROM colegiados WHERE matricula = %s",
                        (p_matricula,))
                    colegiado = cursor.fetchone()
                    if not colegiado:
                        return {
                            "ok": False,
                            "mensaje": "No se encontró el colegiado seleccionado."
                        }
                    if colegiado.get("estado") != "Vigente":
                        return {
                            "ok": False,
                            "mensaje": "Solo se puede registrar pago anual a colegiados vigentes."
                        }

                    for mes in range(1, 13):
                        fecha_periodo = date(anio, mes, 1)
                        vencimiento = _ultimo_dia_mes(anio, mes)
                        concepto = (
                            f"Cuota Ordinaria - {_nombre_mes(mes)} {anio} "
                            "(Pago anual con descuento)"
                        )

                        cursor.execute(
                            "SELECT id, estado FROM cuotas "
                            "WHERE colegiado_id = %s AND tipo = 'mensual' "
                            "AND periodo_anio = %s AND periodo_mes = %s",
                            (colegiado["id"], anio, mes))
                        cuota = cursor.fetchone()

                        if cuota and cuota.get("estado") == "Pagado":
                            ya_pagadas += 1
                            continue

                        if cuota:
                            cursor.execute(
                                "UPDATE cuotas "
                                "SET fecha = %s, fecha_emision = %s, "
                                "    fecha_vencimiento = %s, concepto = %s, "
                                "    monto = %s, estado = 'Pendiente', fecha_pago = NULL "
                                "WHERE id = %s",
                                (fecha_periodo, fecha_periodo, vencimiento,
                                 concepto, monto_aplicado, cuota["id"]))
                            cuota_id = cuota["id"]
                            actualizadas += 1
                        else:
                            sql =  "INSERT INTO cuotas "
                            sql += "(colegiado_id, fecha, fecha_emision, fecha_vencimiento, "
                            sql += " concepto, monto, estado, tipo, periodo_mes, periodo_anio) "
                            sql += "VALUES (%s, %s, %s, %s, %s, %s, 'Pendiente', 'mensual', %s, %s)"
                            cursor.execute(sql, (colegiado["id"], fecha_periodo,
                                                fecha_periodo, vencimiento,
                                                concepto, monto_aplicado, mes,
                                                anio))
                            cuota_id = cursor.lastrowid
                            generadas += 1

                        cuota_pago = {
                            "cuota_id": cuota_id,
                            "colegiado_id": colegiado["id"],
                            "concepto": concepto,
                            "monto": monto_aplicado,
                        }
                        emision = _emitir_comprobante_desde_cuota(
                            cursor,
                            cuota_pago,
                            "Administracion CCPL",
                            "Pago anual anticipado",
                            "Pago anual anticipado " + str(anio) +
                            " registrado en campania enero-marzo. " +
                            "Descuento aplicado: " + str(descuento) + "%."
                        )
                        if not emision.get("ok"):
                            conn.rollback()
                            return emision

                        cursor.execute(
                            "UPDATE cuotas "
                            "SET estado = 'Pagado', fecha_pago = %s "
                            "WHERE id = %s",
                            (hoy, cuota_id))
                        comprobantes += 1
                conn.commit()

            return {
                "ok": True,
                "colegiado": colegiado,
                "anio": anio,
                "monto_mensual": monto_aplicado,
                "descuento": descuento,
                "monto_total": monto_aplicado * 12,
                "generadas": generadas,
                "actualizadas": actualizadas,
                "ya_pagadas": ya_pagadas,
                "comprobantes": comprobantes,
            }
        return {"ok": False, "mensaje": "No se pudo conectar con la base de datos."}
    except Exception as e:
        print(repr(e))
        if _pagos_demo_tablas_no_existen(e):
            return {
                "ok": False,
                "mensaje": "Actualice la base con database/schema.sql para emitir comprobantes."
            }
        return {"ok": False, "mensaje": "No se pudo registrar el pago anual anticipado."}


def obtener_resumen_pago_adelantado():
    hoy = date.today()
    return {
        "anio": hoy.year,
        "mes_inicio": hoy.month,
        "cantidad_meses": 3,
        "monto_mensual": 80.00,
        "mensaje": (
            "Permite pagar varios meses ordinarios de un colegiado. "
            "Si una cuota futura no existe, se genera y se marca como pagada."
        ),
    }


def registrar_pago_adelantado_cuotas(p_matricula, p_anio, p_mes_inicio,
                                     p_cantidad_meses, p_monto_mensual):
    try:
        try:
            anio = int(p_anio)
            mes_inicio = int(p_mes_inicio)
            cantidad_meses = int(p_cantidad_meses)
            monto = float(p_monto_mensual)
        except ValueError:
            return {
                "ok": False,
                "mensaje": "Ingrese año, mes, cantidad y monto válidos."
            }

        if mes_inicio < 1 or mes_inicio > 12:
            return {"ok": False, "mensaje": "Seleccione un mes inicial válido."}
        if cantidad_meses < 1 or cantidad_meses > 12:
            return {
                "ok": False,
                "mensaje": "La cantidad de meses debe estar entre 1 y 12."
            }
        if mes_inicio + cantidad_meses - 1 > 12:
            return {
                "ok": False,
                "mensaje": "El rango de meses no puede pasar de diciembre."
            }
        if monto <= 0:
            return {
                "ok": False,
                "mensaje": "Ingrese un monto mensual mayor a cero."
            }

        conn = obtenerconexion()
        generadas = 0
        actualizadas = 0
        ya_pagadas = 0
        comprobantes = 0
        periodos = []
        hoy = date.today()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT id, matricula, nombre, estado "
                        "FROM colegiados WHERE matricula = %s",
                        (p_matricula,))
                    colegiado = cursor.fetchone()
                    if not colegiado:
                        return {
                            "ok": False,
                            "mensaje": "No se encontró el colegiado seleccionado."
                        }
                    if colegiado.get("estado") != "Vigente":
                        return {
                            "ok": False,
                            "mensaje": "Solo se puede registrar pago adelantado a colegiados vigentes."
                        }

                    for mes in range(mes_inicio, mes_inicio + cantidad_meses):
                        fecha_periodo = date(anio, mes, 1)
                        vencimiento = _ultimo_dia_mes(anio, mes)
                        periodo_label = f"{_nombre_mes(mes)} {anio}"
                        concepto = "Cuota Ordinaria - " + periodo_label

                        cursor.execute(
                            "SELECT id, estado FROM cuotas "
                            "WHERE colegiado_id = %s AND tipo = 'mensual' "
                            "AND periodo_anio = %s AND periodo_mes = %s",
                            (colegiado["id"], anio, mes))
                        cuota = cursor.fetchone()

                        if cuota and cuota.get("estado") == "Pagado":
                            ya_pagadas += 1
                            periodos.append(periodo_label + " (ya pagada)")
                            continue

                        if cuota:
                            cursor.execute(
                                "UPDATE cuotas "
                                "SET fecha = %s, fecha_emision = %s, "
                                "    fecha_vencimiento = %s, concepto = %s, "
                                "    monto = %s, estado = 'Pendiente', fecha_pago = NULL "
                                "WHERE id = %s",
                                (fecha_periodo, fecha_periodo, vencimiento,
                                 concepto, monto, cuota["id"]))
                            cuota_id = cuota["id"]
                            actualizadas += 1
                        else:
                            sql =  "INSERT INTO cuotas "
                            sql += "(colegiado_id, fecha, fecha_emision, fecha_vencimiento, "
                            sql += " concepto, monto, estado, tipo, periodo_mes, periodo_anio) "
                            sql += "VALUES (%s, %s, %s, %s, %s, %s, 'Pendiente', 'mensual', %s, %s)"
                            cursor.execute(sql, (colegiado["id"], fecha_periodo,
                                                fecha_periodo, vencimiento,
                                                concepto, monto, mes, anio))
                            cuota_id = cursor.lastrowid
                            generadas += 1

                        cuota_pago = {
                            "cuota_id": cuota_id,
                            "colegiado_id": colegiado["id"],
                            "concepto": concepto,
                            "monto": monto,
                        }
                        emision = _emitir_comprobante_desde_cuota(
                            cursor,
                            cuota_pago,
                            "Administracion CCPL",
                            "Pago adelantado de cuotas",
                            "Pago adelantado de cuotas ordinarias."
                        )
                        if not emision.get("ok"):
                            conn.rollback()
                            return emision

                        cursor.execute(
                            "UPDATE cuotas "
                            "SET estado = 'Pagado', fecha_pago = %s "
                            "WHERE id = %s",
                            (hoy, cuota_id))
                        comprobantes += 1
                        periodos.append(periodo_label)
                conn.commit()

            return {
                "ok": True,
                "colegiado": colegiado,
                "anio": anio,
                "mes_inicio": mes_inicio,
                "cantidad_meses": cantidad_meses,
                "monto_mensual": monto,
                "monto_total": monto * comprobantes,
                "generadas": generadas,
                "actualizadas": actualizadas,
                "ya_pagadas": ya_pagadas,
                "comprobantes": comprobantes,
                "periodos": periodos,
            }
        return {"ok": False, "mensaje": "No se pudo conectar con la base de datos."}
    except Exception as e:
        print(repr(e))
        if _pagos_demo_tablas_no_existen(e):
            return {
                "ok": False,
                "mensaje": "Actualice la base con database/schema.sql para emitir comprobantes."
            }
        return {"ok": False, "mensaje": "No se pudo registrar el pago adelantado."}


def procesar_cuotas_cursos_faltantes():
    try:
        conn = obtenerconexion()
        generadas = 0
        existentes = 0
        notificaciones = []
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    monto_inhabil_sql = _curso_monto_inhabil_sql(cursor)
                    sql =  " SELECT i.id AS inscripcion_id, i.colegiado_id, "
                    sql += "        i.estado_pago, cu.id AS curso_id, "
                    sql += "        cu.titulo, cu.monto, " + monto_inhabil_sql + ", "
                    sql += "        c.matricula, c.nombre "
                    sql += "   FROM inscripciones_curso i "
                    sql += "   JOIN cursos cu ON cu.id = i.curso_id "
                    sql += "   JOIN colegiados c ON c.id = i.colegiado_id "
                    cursor.execute(sql)
                    inscripciones = cursor.fetchall()

                    for inscripcion in inscripciones:
                        habilidad = _condicion_habilidad_colegiado(
                            cursor, inscripcion["colegiado_id"]
                        )
                        condicion = habilidad["condicion"]
                        precio_curso = _precio_curso_por_condicion(
                            inscripcion, condicion
                        )
                        concepto = (
                            "Inscripción Curso: " + inscripcion["titulo"] +
                            " (colegiado " + condicion.lower() + ")"
                        )
                        cursor.execute(
                            "SELECT id FROM cuotas WHERE inscripcion_id = %s",
                            (inscripcion["inscripcion_id"],))
                        cuota = cursor.fetchone()
                        if cuota:
                            cursor.execute(
                                "UPDATE cuotas "
                                "SET tipo = 'curso', curso_id = %s, estado = %s, "
                                "    monto = %s, concepto = %s, "
                                "    fecha_pago = CASE WHEN %s = 'Pagado' "
                                "      THEN COALESCE(fecha_pago, CURDATE()) ELSE NULL END "
                                "WHERE id = %s",
                                (inscripcion["curso_id"],
                                 inscripcion["estado_pago"],
                                 precio_curso,
                                 concepto,
                                 inscripcion["estado_pago"],
                                 cuota["id"]))
                            existentes += 1
                            continue

                        cursor.execute(
                            "SELECT id FROM cuotas "
                            "WHERE colegiado_id = %s AND concepto = %s",
                            (inscripcion["colegiado_id"], concepto))
                        cuota_legacy = cursor.fetchone()
                        if cuota_legacy:
                            cursor.execute(
                                "UPDATE cuotas "
                                "SET tipo = 'curso', curso_id = %s, "
                                "    inscripcion_id = %s, estado = %s, "
                                "    monto = %s, concepto = %s, "
                                "    fecha_pago = CASE WHEN %s = 'Pagado' "
                                "      THEN COALESCE(fecha_pago, CURDATE()) ELSE NULL END "
                                "WHERE id = %s",
                                (inscripcion["curso_id"],
                                 inscripcion["inscripcion_id"],
                                 inscripcion["estado_pago"],
                                 precio_curso,
                                 concepto,
                                 inscripcion["estado_pago"],
                                 cuota_legacy["id"]))
                            existentes += 1
                            continue

                        sql =  "INSERT INTO cuotas "
                        sql += "(colegiado_id, fecha, fecha_emision, fecha_vencimiento, fecha_pago, "
                        sql += " concepto, monto, estado, tipo, curso_id, inscripcion_id) "
                        sql += "VALUES (%s, CURDATE(), CURDATE(), CURDATE(), %s, %s, %s, "
                        sql += " %s, 'curso', %s, %s)"
                        fecha_pago = date.today() if inscripcion["estado_pago"] == "Pagado" else None
                        cursor.execute(sql, (inscripcion["colegiado_id"],
                                            fecha_pago,
                                            concepto,
                                            precio_curso,
                                            inscripcion["estado_pago"],
                                            inscripcion["curso_id"],
                                            inscripcion["inscripcion_id"]))
                        generadas += 1
                        notificaciones.append({
                            "matricula": inscripcion["matricula"],
                            "nombre": inscripcion.get("nombre", ""),
                            "titulo": inscripcion["titulo"],
                            "monto": precio_curso,
                        })
                conn.commit()
            return {
                "ok": True,
                "generadas": generadas,
                "existentes": existentes,
                "total": len(inscripciones),
                "notificaciones": notificaciones,
            }
        return {"ok": False, "mensaje": "No se pudo conectar con la base de datos."}
    except Exception as e:
        print(repr(e))
        return {"ok": False, "mensaje": "No se pudieron procesar las cuotas de cursos."}

# ============================================================
# PAGOS DEMO Y COMPROBANTES
# ============================================================

def _pagos_demo_tablas_no_existen(error):
    texto = str(error).lower()
    return (
        "transacciones_pago" in texto
        or "comprobantes_pago" in texto
        or "doesn't exist" in texto
        or "no existe" in texto
    )


def _comprobantes_tiene_anulacion(cursor):
    cursor.execute("SHOW COLUMNS FROM comprobantes_pago LIKE 'anulado_por_matricula'")
    return cursor.fetchone() is not None


def _transacciones_tiene_evidencia(cursor):
    cursor.execute("SHOW COLUMNS FROM transacciones_pago LIKE 'evidencia_id'")
    return cursor.fetchone() is not None


def _comprobantes_tiene_evidencia(cursor):
    cursor.execute("SHOW COLUMNS FROM comprobantes_pago LIKE 'evidencia_id'")
    return cursor.fetchone() is not None


def _comprobante_emitido_por_cuota(cursor, p_cuota_id):
    cursor.execute(
        "SELECT id, serie, numero FROM comprobantes_pago "
        "WHERE cuota_id = %s AND estado = 'Emitido' "
        "LIMIT 1",
        (p_cuota_id,))
    return cursor.fetchone()


def _emitir_comprobante_desde_cuota(cursor, p_cuota, p_proveedor, p_metodo,
                                    p_respuesta, p_evidencia_id=None):
    existente = _comprobante_emitido_por_cuota(cursor, p_cuota["cuota_id"])
    if existente:
        numero = str(existente.get("serie") or "") + "-" + str(existente.get("numero") or 0).zfill(8)
        return {
            "ok": False,
            "mensaje": "No se puede generar otro comprobante. Ya existe " + numero + ".",
        }

    monto = p_cuota.get("monto")
    if p_cuota.get("evidencia_monto"):
        monto = p_cuota.get("evidencia_monto")

    codigo = "FAC-" + uuid4().hex[:12].upper()
    autorizacion = "AUT-" + uuid4().hex[:10].upper()

    if p_evidencia_id and _transacciones_tiene_evidencia(cursor):
        sql =  " INSERT INTO transacciones_pago "
        sql += " (cuota_id, colegiado_id, evidencia_id, proveedor, metodo, "
        sql += "  codigo_transaccion, codigo_autorizacion, monto, moneda, "
        sql += "  estado, respuesta_pasarela, pagado_en) "
        sql += " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'PEN', "
        sql += "         'Aprobado', %s, NOW()) "
        cursor.execute(sql, (p_cuota["cuota_id"], p_cuota["colegiado_id"],
                            p_evidencia_id, p_proveedor, p_metodo, codigo,
                            autorizacion, monto, p_respuesta))
    else:
        sql =  " INSERT INTO transacciones_pago "
        sql += " (cuota_id, colegiado_id, proveedor, metodo, "
        sql += "  codigo_transaccion, codigo_autorizacion, monto, moneda, "
        sql += "  estado, respuesta_pasarela, pagado_en) "
        sql += " VALUES (%s, %s, %s, %s, %s, %s, %s, 'PEN', "
        sql += "         'Aprobado', %s, NOW()) "
        cursor.execute(sql, (p_cuota["cuota_id"], p_cuota["colegiado_id"],
                            p_proveedor, p_metodo, codigo, autorizacion,
                            monto, p_respuesta))
    transaccion_id = cursor.lastrowid

    tipo = "Boleta Interna"
    serie = "B001"
    cursor.execute(
        "SELECT COALESCE(MAX(numero), 0) + 1 AS siguiente "
        "FROM comprobantes_pago "
        "WHERE tipo_comprobante = %s AND serie = %s ",
        (tipo, serie)
    )
    fila = cursor.fetchone() or {}
    numero = fila.get("siguiente") or 1
    hash_demo = uuid4().hex.upper()

    if p_evidencia_id and _comprobantes_tiene_evidencia(cursor):
        sql =  " INSERT INTO comprobantes_pago "
        sql += " (transaccion_id, cuota_id, colegiado_id, evidencia_id, "
        sql += "  tipo_comprobante, serie, numero, fecha_emision, concepto, "
        sql += "  subtotal, igv, total, moneda, estado, codigo_hash) "
        sql += " VALUES (%s, %s, %s, %s, %s, %s, %s, CURDATE(), "
        sql += "         %s, %s, 0.00, %s, 'PEN', 'Emitido', %s) "
        cursor.execute(sql, (transaccion_id, p_cuota["cuota_id"],
                            p_cuota["colegiado_id"], p_evidencia_id,
                            tipo, serie, numero, p_cuota["concepto"],
                            monto, monto, hash_demo))
    else:
        sql =  " INSERT INTO comprobantes_pago "
        sql += " (transaccion_id, cuota_id, colegiado_id, tipo_comprobante, "
        sql += "  serie, numero, fecha_emision, concepto, subtotal, igv, "
        sql += "  total, moneda, estado, codigo_hash) "
        sql += " VALUES (%s, %s, %s, %s, %s, %s, CURDATE(), "
        sql += "         %s, %s, 0.00, %s, 'PEN', 'Emitido', %s) "
        cursor.execute(sql, (transaccion_id, p_cuota["cuota_id"],
                            p_cuota["colegiado_id"], tipo, serie, numero,
                            p_cuota["concepto"], monto, monto, hash_demo))

    return {
        "ok": True,
        "transaccion_id": transaccion_id,
        "comprobante_id": cursor.lastrowid,
        "codigo_transaccion": codigo,
    }


def _filtros_pagos_demo(p_estado=None, p_busqueda=None):
    filtros = []
    params = []
    if p_estado:
        filtros.append("tp.estado = %s")
        params.append(p_estado)
    if p_busqueda:
        like = f"%{p_busqueda}%"
        filtros.append(
            "(c.nombre LIKE %s OR c.matricula LIKE %s OR "
            "q.concepto LIKE %s OR tp.codigo_transaccion LIKE %s)"
        )
        params.extend([like, like, like, like])
    return filtros, params


def _filtros_comprobantes_demo(p_estado=None, p_busqueda=None):
    filtros = []
    params = []
    if p_estado:
        filtros.append("cp.estado = %s")
        params.append(p_estado)
    if p_busqueda:
        like = f"%{p_busqueda}%"
        filtros.append(
            "(c.nombre LIKE %s OR c.matricula LIKE %s OR "
            "cp.concepto LIKE %s OR tp.codigo_transaccion LIKE %s OR "
            "CONCAT(cp.serie, '-', LPAD(cp.numero, 8, '0')) LIKE %s)"
        )
        params.extend([like, like, like, like, like])
    return filtros, params


def leer_transacciones_pago_demo(p_estado=None, p_busqueda=None,
                                 p_limite=None, p_offset=0):
    try:
        conn = obtenerconexion()
        result = []
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    tiene_evidencia = _transacciones_tiene_evidencia(cursor)
                    evidencia_sql = "tp.evidencia_id"
                    join_evidencia = ""
                    if not tiene_evidencia:
                        evidencia_sql = "NULL AS evidencia_id"
                    else:
                        join_evidencia = "   LEFT JOIN evidencias_pago ev ON ev.id = tp.evidencia_id "
                    sql =  " SELECT tp.id, tp.cuota_id, tp.proveedor, tp.metodo, "
                    sql += "        tp.codigo_transaccion, tp.codigo_autorizacion, "
                    sql += "        tp.monto, tp.moneda, tp.estado, tp.pagado_en, "
                    sql += "        tp.creado_en, " + evidencia_sql + ", "
                    sql += "        q.concepto, q.tipo, q.estado AS cuota_estado, "
                    sql += "        c.nombre, c.matricula, "
                    sql += "        cp.id AS comprobante_id, cp.serie, cp.numero, "
                    sql += "        cp.estado AS comprobante_estado "
                    sql += "   FROM transacciones_pago tp "
                    sql += "   JOIN cuotas q ON q.id = tp.cuota_id "
                    sql += "   JOIN colegiados c ON c.id = tp.colegiado_id "
                    sql += "   LEFT JOIN comprobantes_pago cp ON cp.transaccion_id = tp.id "
                    sql += join_evidencia
                    filtros, params = _filtros_pagos_demo(p_estado, p_busqueda)
                    if filtros:
                        sql += " WHERE " + " AND ".join(filtros)
                    sql += "  ORDER BY tp.creado_en DESC, tp.id DESC "
                    if p_limite:
                        limite = max(1, min(int(p_limite), 100))
                        offset = max(0, int(p_offset or 0))
                        sql += " LIMIT %s OFFSET %s "
                        params.extend([limite, offset])
                    cursor.execute(sql, tuple(params))
                    result = cursor.fetchall()
        return result
    except Exception as e:
        if _pagos_demo_tablas_no_existen(e):
            return []
        raise


def contar_transacciones_pago_demo(p_estado=None, p_busqueda=None):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT COUNT(*) AS total "
                    sql += "   FROM transacciones_pago tp "
                    sql += "   JOIN cuotas q ON q.id = tp.cuota_id "
                    sql += "   JOIN colegiados c ON c.id = tp.colegiado_id "
                    filtros, params = _filtros_pagos_demo(p_estado, p_busqueda)
                    if filtros:
                        sql += " WHERE " + " AND ".join(filtros)
                    cursor.execute(sql, tuple(params))
                    fila = cursor.fetchone() or {}
                    return fila.get("total", 0) or 0
        return 0
    except Exception as e:
        if _pagos_demo_tablas_no_existen(e):
            return 0
        raise


def leer_comprobantes_pago_demo_admin(p_estado=None, p_busqueda=None,
                                      p_limite=None, p_offset=0):
    try:
        conn = obtenerconexion()
        result = []
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    tiene_anulacion = _comprobantes_tiene_anulacion(cursor)
                    tiene_evidencia = _comprobantes_tiene_evidencia(cursor)
                    tiene_facturacion = _facturacion_tablas_existen(cursor)
                    anulacion_sql = (
                        "cp.anulado_por_matricula, cp.anulado_por_nombre, "
                        "cp.motivo_anulacion, cp.anulado_en"
                    )
                    if not tiene_anulacion:
                        anulacion_sql = (
                            "NULL AS anulado_por_matricula, NULL AS anulado_por_nombre, "
                            "NULL AS motivo_anulacion, NULL AS anulado_en"
                        )
                    evidencia_sql = "cp.evidencia_id"
                    if not tiene_evidencia:
                        evidencia_sql = "NULL AS evidencia_id"
                    fiscal_sql = (
                        "cf.id AS fiscal_id, cf.tipo_comprobante AS fiscal_tipo, "
                        "cf.serie AS fiscal_serie, cf.numero AS fiscal_numero, "
                        "cf.estado AS fiscal_estado"
                    )
                    join_fiscal = ""
                    if not tiene_facturacion:
                        fiscal_sql = (
                            "NULL AS fiscal_id, NULL AS fiscal_tipo, "
                            "NULL AS fiscal_serie, NULL AS fiscal_numero, "
                            "NULL AS fiscal_estado"
                        )
                    else:
                        join_fiscal = (
                            "   LEFT JOIN comprobantes_fiscales cf "
                            "     ON cf.comprobante_pago_id = cp.id "
                        )

                    sql =  " SELECT cp.id, cp.transaccion_id, cp.cuota_id, "
                    sql += "        cp.tipo_comprobante, cp.serie, cp.numero, "
                    sql += "        cp.fecha_emision, cp.concepto, cp.subtotal, "
                    sql += "        cp.igv, cp.total, cp.moneda, cp.estado, "
                    sql += "        cp.codigo_hash, cp.creado_en, " + evidencia_sql + ", "
                    sql += "        " + anulacion_sql + ", "
                    sql += "        tp.proveedor, tp.metodo, tp.codigo_transaccion, "
                    sql += "        tp.codigo_autorizacion, tp.pagado_en, "
                    sql += "        c.nombre, c.matricula, c.documento, c.correo, "
                    sql += "        " + fiscal_sql + " "
                    sql += "   FROM comprobantes_pago cp "
                    sql += "   JOIN transacciones_pago tp ON tp.id = cp.transaccion_id "
                    sql += "   JOIN colegiados c ON c.id = cp.colegiado_id "
                    sql += join_fiscal
                    filtros, params = _filtros_comprobantes_demo(p_estado, p_busqueda)
                    if filtros:
                        sql += " WHERE " + " AND ".join(filtros)
                    sql += "  ORDER BY cp.fecha_emision DESC, cp.id DESC "
                    if p_limite:
                        limite = max(1, min(int(p_limite), 100))
                        offset = max(0, int(p_offset or 0))
                        sql += " LIMIT %s OFFSET %s "
                        params.extend([limite, offset])
                    cursor.execute(sql, tuple(params))
                    result = cursor.fetchall()
        return result
    except Exception as e:
        if _pagos_demo_tablas_no_existen(e):
            return []
        raise


def contar_comprobantes_pago_demo_admin(p_estado=None, p_busqueda=None):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT COUNT(*) AS total "
                    sql += "   FROM comprobantes_pago cp "
                    sql += "   JOIN transacciones_pago tp ON tp.id = cp.transaccion_id "
                    sql += "   JOIN colegiados c ON c.id = cp.colegiado_id "
                    filtros, params = _filtros_comprobantes_demo(p_estado, p_busqueda)
                    if filtros:
                        sql += " WHERE " + " AND ".join(filtros)
                    cursor.execute(sql, tuple(params))
                    fila = cursor.fetchone() or {}
                    return fila.get("total", 0) or 0
        return 0
    except Exception as e:
        if _pagos_demo_tablas_no_existen(e):
            return 0
        raise


def leer_comprobante_pago_demo_admin(p_id):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    tiene_anulacion = _comprobantes_tiene_anulacion(cursor)
                    tiene_evidencia = _comprobantes_tiene_evidencia(cursor)
                    tiene_facturacion = _facturacion_tablas_existen(cursor)
                    anulacion_sql = (
                        "cp.anulado_por_matricula, cp.anulado_por_nombre, "
                        "cp.motivo_anulacion, cp.anulado_en"
                    )
                    if not tiene_anulacion:
                        anulacion_sql = (
                            "NULL AS anulado_por_matricula, NULL AS anulado_por_nombre, "
                            "NULL AS motivo_anulacion, NULL AS anulado_en"
                        )
                    evidencia_sql = "cp.evidencia_id"
                    if not tiene_evidencia:
                        evidencia_sql = "NULL AS evidencia_id"
                    fiscal_sql = (
                        "cf.id AS fiscal_id, cf.tipo_comprobante AS fiscal_tipo, "
                        "cf.serie AS fiscal_serie, cf.numero AS fiscal_numero, "
                        "cf.estado AS fiscal_estado"
                    )
                    join_fiscal = ""
                    if not tiene_facturacion:
                        fiscal_sql = (
                            "NULL AS fiscal_id, NULL AS fiscal_tipo, "
                            "NULL AS fiscal_serie, NULL AS fiscal_numero, "
                            "NULL AS fiscal_estado"
                        )
                    else:
                        join_fiscal = (
                            "   LEFT JOIN comprobantes_fiscales cf "
                            "     ON cf.comprobante_pago_id = cp.id "
                        )
                    sql =  " SELECT cp.id, cp.transaccion_id, cp.cuota_id, "
                    sql += "        cp.tipo_comprobante, cp.serie, cp.numero, "
                    sql += "        cp.fecha_emision, cp.concepto, cp.subtotal, "
                    sql += "        cp.igv, cp.total, cp.moneda, cp.estado, "
                    sql += "        cp.codigo_hash, " + evidencia_sql + ", "
                    sql += "        " + anulacion_sql + ", "
                    sql += "        tp.proveedor, tp.metodo, tp.codigo_transaccion, "
                    sql += "        tp.codigo_autorizacion, tp.pagado_en, "
                    sql += "        c.nombre, c.matricula, c.documento, c.correo, "
                    sql += "        " + fiscal_sql + " "
                    sql += "   FROM comprobantes_pago cp "
                    sql += "   JOIN transacciones_pago tp ON tp.id = cp.transaccion_id "
                    sql += "   JOIN colegiados c ON c.id = cp.colegiado_id "
                    sql += join_fiscal
                    sql += "  WHERE cp.id = %s "
                    cursor.execute(sql, (p_id,))
                    return cursor.fetchone()
        return None
    except Exception as e:
        if _pagos_demo_tablas_no_existen(e):
            return None
        raise


def resumir_pagos_demo():
    resumen = {
        "total_transacciones": 0,
        "transacciones_aprobadas": 0,
        "recaudado": 0,
        "comprobantes_emitidos": 0,
        "comprobantes_anulados": 0,
        "total_emitido": 0,
        "total_anulado": 0,
        "metodos": [],
    }
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT COUNT(*) AS total, "
                        "COALESCE(SUM(CASE WHEN estado = 'Aprobado' THEN 1 ELSE 0 END), 0) AS aprobadas, "
                        "COALESCE(SUM(CASE WHEN estado = 'Aprobado' THEN monto ELSE 0 END), 0) AS recaudado "
                        "FROM transacciones_pago"
                    )
                    fila = cursor.fetchone() or {}
                    resumen["total_transacciones"] = fila.get("total", 0) or 0
                    resumen["transacciones_aprobadas"] = fila.get("aprobadas", 0) or 0
                    resumen["recaudado"] = fila.get("recaudado", 0) or 0

                    cursor.execute(
                        "SELECT COALESCE(SUM(CASE WHEN estado = 'Emitido' THEN 1 ELSE 0 END), 0) AS emitidos, "
                        "COALESCE(SUM(CASE WHEN estado = 'Emitido' THEN total ELSE 0 END), 0) AS total_emitido, "
                        "COALESCE(SUM(CASE WHEN estado = 'Anulado' THEN 1 ELSE 0 END), 0) AS anulados, "
                        "COALESCE(SUM(CASE WHEN estado = 'Anulado' THEN total ELSE 0 END), 0) AS total_anulado "
                        "FROM comprobantes_pago"
                    )
                    fila = cursor.fetchone() or {}
                    resumen["comprobantes_emitidos"] = fila.get("emitidos", 0) or 0
                    resumen["comprobantes_anulados"] = fila.get("anulados", 0) or 0
                    resumen["total_emitido"] = fila.get("total_emitido", 0) or 0
                    resumen["total_anulado"] = fila.get("total_anulado", 0) or 0

                    cursor.execute(
                        "SELECT metodo, COUNT(*) AS total, "
                        "COALESCE(SUM(monto), 0) AS monto "
                        "FROM transacciones_pago "
                        "WHERE estado = 'Aprobado' "
                        "GROUP BY metodo "
                        "ORDER BY monto DESC, metodo ASC"
                    )
                    resumen["metodos"] = cursor.fetchall()
        return resumen
    except Exception as e:
        if _pagos_demo_tablas_no_existen(e):
            return resumen
        raise


def leer_reporte_contable_demo():
    data = {
        "por_metodo": [],
        "por_origen": [],
        "comprobantes_estado": [],
        "por_mes": [],
    }
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    tiene_evidencia = _transacciones_tiene_evidencia(cursor)
                    origen_expr = "'Pasarela / admin'"
                    if tiene_evidencia:
                        origen_expr = (
                            "CASE WHEN tp.evidencia_id IS NOT NULL "
                            "THEN 'Evidencia aprobada' "
                            "WHEN tp.proveedor IN ('Pasarela Interna CCPL', 'Pago Interno CCPL') "
                            "THEN 'Pago interno CCPL' "
                            "ELSE 'Registro administrativo' END"
                        )

                    cursor.execute(
                        "SELECT tp.metodo, COUNT(*) AS total, "
                        "COALESCE(SUM(tp.monto), 0) AS monto "
                        "FROM transacciones_pago tp "
                        "WHERE tp.estado = 'Aprobado' "
                        "GROUP BY tp.metodo "
                        "ORDER BY monto DESC, total DESC"
                    )
                    data["por_metodo"] = cursor.fetchall()

                    sql =  "SELECT " + origen_expr + " AS origen, "
                    sql += "COUNT(*) AS total, COALESCE(SUM(tp.monto), 0) AS monto "
                    sql += "FROM transacciones_pago tp "
                    sql += "WHERE tp.estado = 'Aprobado' "
                    sql += "GROUP BY " + origen_expr + " "
                    sql += "ORDER BY monto DESC, total DESC"
                    cursor.execute(sql)
                    data["por_origen"] = cursor.fetchall()

                    cursor.execute(
                        "SELECT estado, COUNT(*) AS total, "
                        "COALESCE(SUM(total), 0) AS monto "
                        "FROM comprobantes_pago "
                        "GROUP BY estado "
                        "ORDER BY total DESC"
                    )
                    data["comprobantes_estado"] = cursor.fetchall()

                    cursor.execute(
                        "SELECT YEAR(COALESCE(tp.pagado_en, tp.creado_en)) AS anio, "
                        "MONTH(COALESCE(tp.pagado_en, tp.creado_en)) AS mes, "
                        "COUNT(*) AS total, COALESCE(SUM(tp.monto), 0) AS monto "
                        "FROM transacciones_pago tp "
                        "WHERE tp.estado = 'Aprobado' "
                        "GROUP BY YEAR(COALESCE(tp.pagado_en, tp.creado_en)), "
                        "MONTH(COALESCE(tp.pagado_en, tp.creado_en)) "
                        "ORDER BY anio DESC, mes DESC "
                        "LIMIT 12"
                    )
                    data["por_mes"] = list(reversed(cursor.fetchall()))
        return data
    except Exception as e:
        if _pagos_demo_tablas_no_existen(e):
            return data
        raise


def anular_comprobante_pago_demo(p_id, p_usuario_matricula=None,
                                 p_usuario_nombre=None, p_motivo=None):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    tiene_anulacion = _comprobantes_tiene_anulacion(cursor)
                    cursor.execute(
                        "SELECT cp.id, cp.estado, cp.concepto, cp.colegiado_id, "
                        "       c.matricula, c.nombre "
                        "FROM comprobantes_pago cp "
                        "JOIN colegiados c ON c.id = cp.colegiado_id "
                        "WHERE cp.id = %s",
                        (p_id,))
                    comprobante = cursor.fetchone()
                    if not comprobante:
                        return {"ok": False, "mensaje": "No se encontró el comprobante."}
                    if comprobante["estado"] == "Anulado":
                        return {"ok": False, "mensaje": "El comprobante ya está anulado."}
                    if comprobante["estado"] != "Emitido":
                        return {"ok": False, "mensaje": "Solo se pueden anular comprobantes emitidos."}

                    usuario_matricula = p_usuario_matricula or "admin"
                    usuario_nombre = p_usuario_nombre or "Administrador CCPL"
                    motivo = (p_motivo or "").strip()
                    if len(motivo) < 5:
                        return {
                            "ok": False,
                            "mensaje": "Ingrese un motivo de anulación mas detallado.",
                        }

                    if tiene_anulacion:
                        sql =  " UPDATE comprobantes_pago "
                        sql += "    SET estado = 'Anulado', "
                        sql += "        anulado_por_matricula = %s, "
                        sql += "        anulado_por_nombre = %s, "
                        sql += "        motivo_anulacion = %s, "
                        sql += "        anulado_en = NOW() "
                        sql += "  WHERE id = %s "
                        cursor.execute(sql, (usuario_matricula, usuario_nombre,
                                            motivo, p_id))
                    else:
                        cursor.execute(
                            "UPDATE comprobantes_pago SET estado = 'Anulado' WHERE id = %s",
                            (p_id,))
                conn.commit()
            return {
                "ok": True,
                "mensaje": "Comprobante anulado correctamente.",
                "matricula": comprobante.get("matricula"),
                "nombre": comprobante.get("nombre"),
                "concepto": comprobante.get("concepto"),
            }
        return {"ok": False, "mensaje": "No se pudo conectar con la base de datos."}
    except Exception as e:
        print(repr(e))
        if _pagos_demo_tablas_no_existen(e):
            return {
                "ok": False,
                "mensaje": "Actualice la base con database/schema.sql.",
            }
        return {"ok": False, "mensaje": "No se pudo anular el comprobante."}

# ============================================================
# FUNCIONES CRUD - CUOTAS
# ============================================================

def leer_cuota_por_id(p_id):
    return _leer_registro_por_id("cuotas", p_id)


def actualizar_cuota(p_cuota):
    try:
        datos = {
            "id": p_cuota.id,
            "fecha": p_cuota.fecha,
            "fecha_vencimiento": p_cuota.fecha_vencimiento,
            "concepto": p_cuota.concepto,
            "monto": p_cuota.monto,
            "estado": p_cuota.estado,
            "tipo": p_cuota.tipo,
            "periodo_mes": p_cuota.periodo_mes,
            "periodo_anio": p_cuota.periodo_anio,
        }
        columnas = [
            "fecha", "fecha_vencimiento", "concepto", "monto", "estado",
            "tipo", "periodo_mes", "periodo_anio"
        ]
        return _actualizar_registro_crud("cuotas", datos, columnas)
    except Exception as e:
        print(repr(e))
        return False

# ============================================================
# FUNCIONES CRUD - TRANSACCIONES Y COMPROBANTES INTERNOS
# ============================================================

def leer_transacciones_pago_crud():
    return _leer_registros_crud("transacciones_pago")


def leer_transaccion_pago_por_id(p_id):
    return _leer_registro_por_id("transacciones_pago", p_id)


def insertar_transaccion_pago_crud(p_datos):
    columnas = [
        "cuota_id", "colegiado_id", "evidencia_id", "proveedor", "metodo",
        "codigo_transaccion", "codigo_autorizacion", "monto", "moneda",
        "estado", "respuesta_pasarela", "pagado_en"
    ]
    return _insertar_registro_crud("transacciones_pago", p_datos, columnas)


def actualizar_transaccion_pago_crud(p_datos):
    columnas = [
        "cuota_id", "colegiado_id", "evidencia_id", "proveedor", "metodo",
        "codigo_transaccion", "codigo_autorizacion", "monto", "moneda",
        "estado", "respuesta_pasarela", "pagado_en"
    ]
    return _actualizar_registro_crud("transacciones_pago", p_datos, columnas)


def eliminar_transaccion_pago(p_id):
    return _eliminar_registro_crud("transacciones_pago", p_id)


def leer_comprobantes_pago_crud():
    return _leer_registros_crud("comprobantes_pago")


def leer_comprobante_pago_por_id(p_id):
    return _leer_registro_por_id("comprobantes_pago", p_id)


def insertar_comprobante_pago_crud(p_datos):
    columnas = [
        "transaccion_id", "cuota_id", "colegiado_id", "evidencia_id",
        "tipo_comprobante", "serie", "numero", "fecha_emision", "concepto",
        "subtotal", "igv", "total", "moneda", "estado", "codigo_hash",
        "anulado_por_matricula", "anulado_por_nombre", "motivo_anulacion",
        "anulado_en"
    ]
    return _insertar_registro_crud("comprobantes_pago", p_datos, columnas)


def actualizar_comprobante_pago_crud(p_datos):
    columnas = [
        "transaccion_id", "cuota_id", "colegiado_id", "evidencia_id",
        "tipo_comprobante", "serie", "numero", "fecha_emision", "concepto",
        "subtotal", "igv", "total", "moneda", "estado", "codigo_hash",
        "anulado_por_matricula", "anulado_por_nombre", "motivo_anulacion",
        "anulado_en"
    ]
    return _actualizar_registro_crud("comprobantes_pago", p_datos, columnas)


def eliminar_comprobante_pago(p_id):
    return _eliminar_registro_crud("comprobantes_pago", p_id)
