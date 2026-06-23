import json
import re
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4
from bd import obtenerconexion
from sunat_beta import (SUNAT_BETA_ENDPOINT, SunatBetaError,
                        enviar_comprobante_sunat_beta)


# ============================================================
# MODELOS ADMINISTRATIVOS
# ============================================================

class clsUsuario:
    def __init__(self, p_id=None, p_matricula=None, p_password=None,
                 p_rol=None, p_activo=None):
        self.id = p_id
        self.matricula = p_matricula
        self.password = p_password
        self.rol = p_rol
        self.activo = p_activo


class clsCuota:
    def __init__(self, p_id=None, p_matricula=None, p_fecha=None,
                 p_concepto=None, p_monto=None, p_estado=None,
                 p_tipo="otro", p_periodo_mes=None, p_periodo_anio=None,
                 p_fecha_vencimiento=None):
        self.id = p_id
        self.matricula = p_matricula
        self.fecha = p_fecha
        self.concepto = p_concepto
        self.monto = p_monto
        self.estado = p_estado
        self.tipo = p_tipo
        self.periodo_mes = p_periodo_mes
        self.periodo_anio = p_periodo_anio
        self.fecha_vencimiento = p_fecha_vencimiento


class clsMedioPago:
    def __init__(self, p_id=None, p_nombre=None, p_descripcion=None,
                 p_numero_cuenta=None, p_titular=None, p_activo=1):
        self.id = p_id
        self.nombre = p_nombre
        self.descripcion = p_descripcion
        self.numero_cuenta = p_numero_cuenta
        self.titular = p_titular
        self.activo = p_activo


class clsCurso:
    def __init__(self, p_id=None, p_categoria=None, p_titulo=None,
                 p_descripcion=None, p_fecha_evento=None, p_estado=None,
                 p_monto=0, p_ponente=None, p_modalidad=None,
                 p_duracion_horas=0, p_fecha_inicio=None, p_fecha_fin=None,
                 p_cupos=0, p_monto_inhabil=None):
        self.id = p_id
        self.categoria = p_categoria
        self.titulo = p_titulo
        self.descripcion = p_descripcion
        self.fecha_evento = p_fecha_evento
        self.estado = p_estado
        self.monto = p_monto
        self.monto_inhabil = p_monto_inhabil
        self.ponente = p_ponente
        self.modalidad = p_modalidad
        self.duracion_horas = p_duracion_horas
        self.fecha_inicio = p_fecha_inicio
        self.fecha_fin = p_fecha_fin
        self.cupos = p_cupos


# ============================================================
# USUARIOS DEL SISTEMA
# ============================================================

def leer_usuarios():
    try:
        conn = obtenerconexion()
        result = None
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT u.id, u.matricula, u.password, u.rol, u.activo, "
                    sql += "        CASE "
                    sql += "          WHEN c.nombre IS NOT NULL THEN c.nombre "
                    sql += "          WHEN u.rol = 'admin' THEN 'Administrador CCPL' "
                    sql += "          ELSE u.matricula "
                    sql += "        END AS nombre "
                    sql += "   FROM usuarios u "
                    sql += "   LEFT JOIN colegiados c ON c.matricula = u.matricula "
                    sql += "  ORDER BY u.id DESC "
                    cursor.execute(sql)
                    result = cursor.fetchall()
        return result
    except Exception:
        raise


def insertar_usuario(p_usuario):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT id FROM usuarios WHERE matricula = %s",
                                   (p_usuario.matricula,))
                    if cursor.fetchone():
                        return False

                    if p_usuario.rol == "colegiado":
                        cursor.execute("SELECT id FROM colegiados WHERE matricula = %s",
                                       (p_usuario.matricula,))
                        if not cursor.fetchone():
                            return False

                    sql =  "INSERT INTO `usuarios` (`matricula`, `password`, `rol`, `activo`) "
                    sql += "VALUES (%s, %s, %s, %s)"
                    cursor.execute(sql, (p_usuario.matricula, p_usuario.password,
                                        p_usuario.rol, p_usuario.activo))
                conn.commit()
            return True
        return False
    except Exception as e:
        print(repr(e))
        return False


def actualizar_usuario(p_usuario):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    if p_usuario.rol == "colegiado":
                        cursor.execute("SELECT matricula FROM usuarios WHERE id = %s",
                                       (p_usuario.id,))
                        usuario_actual = cursor.fetchone()
                        if not usuario_actual:
                            return False
                        cursor.execute("SELECT id FROM colegiados WHERE matricula = %s",
                                       (usuario_actual["matricula"],))
                        if not cursor.fetchone():
                            return False

                    if p_usuario.password:
                        sql =  "UPDATE `usuarios` "
                        sql += "   SET `password` = %s, `rol` = %s, `activo` = %s "
                        sql += " WHERE `id` = %s "
                        cursor.execute(sql, (p_usuario.password, p_usuario.rol,
                                            p_usuario.activo, p_usuario.id))
                    else:
                        sql =  "UPDATE `usuarios` "
                        sql += "   SET `rol` = %s, `activo` = %s "
                        sql += " WHERE `id` = %s "
                        cursor.execute(sql, (p_usuario.rol, p_usuario.activo,
                                            p_usuario.id))
                conn.commit()
            return True
        return False
    except Exception as e:
        print(repr(e))
        return False


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
                        return {"ok": False, "mensaje": "No se encontro la cuota."}
                    if cuota["cuota_estado"] != "Pendiente":
                        return {"ok": False, "mensaje": "La cuota ya no esta pendiente."}

                    emision = _emitir_comprobante_desde_cuota(
                        cursor,
                        cuota,
                        "Registro administrativo",
                        "Pago administrativo",
                        "Pago marcado por administracion."
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
                    elif cuota and cuota["concepto"].startswith("Inscripcion Curso: "):
                        titulo = cuota["concepto"].replace("Inscripcion Curso: ", "", 1)
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
                "mensaje": "Ingrese un anio, monto y descuento validos."
            }

        if anio != hoy.year:
            return {
                "ok": False,
                "mensaje": "Solo se puede registrar el pago anual del anio actual."
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
                            "mensaje": "No se encontro el colegiado seleccionado."
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
                "mensaje": "Ingrese anio, mes, cantidad y monto validos."
            }

        if mes_inicio < 1 or mes_inicio > 12:
            return {"ok": False, "mensaje": "Seleccione un mes inicial valido."}
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
                            "mensaje": "No se encontro el colegiado seleccionado."
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
                            "Inscripcion Curso: " + inscripcion["titulo"] +
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
# REPORTES ADMINISTRATIVOS
# ============================================================

def _filtros_reporte_cuotas(p_tipo=None, p_estado=None, p_busqueda=None,
                            p_fecha_desde=None, p_fecha_hasta=None):
    filtros = []
    params = []
    if p_tipo:
        filtros.append("q.tipo = %s")
        params.append(p_tipo)
    if p_estado:
        if p_estado == "Vencida":
            filtros.append(
                "q.estado = 'Pendiente' AND COALESCE(q.fecha_vencimiento, q.fecha) < CURDATE()"
            )
        else:
            filtros.append("q.estado = %s")
            params.append(p_estado)
    if p_busqueda:
        filtros.append("(c.matricula LIKE %s OR c.nombre LIKE %s OR q.concepto LIKE %s)")
        like = f"%{p_busqueda}%"
        params.extend([like, like, like])
    if p_fecha_desde:
        filtros.append("q.fecha >= %s")
        params.append(p_fecha_desde)
    if p_fecha_hasta:
        filtros.append("q.fecha <= %s")
        params.append(p_fecha_hasta)
    return filtros, params


def leer_reporte_financiero(p_tipo=None, p_estado=None, p_busqueda=None,
                            p_fecha_desde=None, p_fecha_hasta=None,
                            p_limite=25, p_offset=0):
    try:
        conn = obtenerconexion()
        data = {
            "resumen": {
                "total_registros": 0,
                "total_general": 0,
                "total_pagado": 0,
                "total_pendiente": 0,
                "deuda_vencida": 0,
                "cuotas_pagadas": 0,
                "cuotas_pendientes": 0,
                "cuotas_vencidas": 0,
            },
            "por_tipo": [],
            "por_estado": [],
            "por_mes": [],
            "detalle": [],
        }
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    filtros, params = _filtros_reporte_cuotas(
                        p_tipo, p_estado, p_busqueda, p_fecha_desde, p_fecha_hasta
                    )
                    where = (" WHERE " + " AND ".join(filtros)) if filtros else ""

                    sql_resumen =  " SELECT COUNT(*) AS total_registros, "
                    sql_resumen += "        COALESCE(SUM(q.monto), 0) AS total_general, "
                    sql_resumen += "        COALESCE(SUM(CASE WHEN q.estado = 'Pagado' THEN q.monto ELSE 0 END), 0) AS total_pagado, "
                    sql_resumen += "        COALESCE(SUM(CASE WHEN q.estado = 'Pendiente' THEN q.monto ELSE 0 END), 0) AS total_pendiente, "
                    sql_resumen += "        COALESCE(SUM(CASE WHEN q.estado = 'Pendiente' AND COALESCE(q.fecha_vencimiento, q.fecha) < CURDATE() THEN q.monto ELSE 0 END), 0) AS deuda_vencida, "
                    sql_resumen += "        COALESCE(SUM(CASE WHEN q.estado = 'Pagado' THEN 1 ELSE 0 END), 0) AS cuotas_pagadas, "
                    sql_resumen += "        COALESCE(SUM(CASE WHEN q.estado = 'Pendiente' THEN 1 ELSE 0 END), 0) AS cuotas_pendientes, "
                    sql_resumen += "        COALESCE(SUM(CASE WHEN q.estado = 'Pendiente' AND COALESCE(q.fecha_vencimiento, q.fecha) < CURDATE() THEN 1 ELSE 0 END), 0) AS cuotas_vencidas "
                    sql_resumen += "   FROM cuotas q "
                    sql_resumen += "   JOIN colegiados c ON c.id = q.colegiado_id "
                    sql_resumen += where
                    cursor.execute(sql_resumen, tuple(params))
                    data["resumen"] = cursor.fetchone() or data["resumen"]

                    sql_tipo =  " SELECT COALESCE(NULLIF(q.tipo, ''), 'otro') AS tipo, "
                    sql_tipo += "        COUNT(*) AS total, "
                    sql_tipo += "        COALESCE(SUM(q.monto), 0) AS monto "
                    sql_tipo += "   FROM cuotas q "
                    sql_tipo += "   JOIN colegiados c ON c.id = q.colegiado_id "
                    sql_tipo += where
                    sql_tipo += "  GROUP BY COALESCE(NULLIF(q.tipo, ''), 'otro') "
                    sql_tipo += "  ORDER BY monto DESC, total DESC "
                    cursor.execute(sql_tipo, tuple(params))
                    data["por_tipo"] = cursor.fetchall()

                    estado_expr = (
                        "CASE WHEN q.estado = 'Pendiente' "
                        "AND COALESCE(q.fecha_vencimiento, q.fecha) < CURDATE() "
                        "THEN 'Vencida' ELSE q.estado END"
                    )
                    sql_estado =  " SELECT " + estado_expr + " AS estado_reporte, "
                    sql_estado += "        COUNT(*) AS total, "
                    sql_estado += "        COALESCE(SUM(q.monto), 0) AS monto "
                    sql_estado += "   FROM cuotas q "
                    sql_estado += "   JOIN colegiados c ON c.id = q.colegiado_id "
                    sql_estado += where
                    sql_estado += "  GROUP BY " + estado_expr + " "
                    sql_estado += "  ORDER BY monto DESC, total DESC "
                    cursor.execute(sql_estado, tuple(params))
                    data["por_estado"] = cursor.fetchall()

                    sql_mes =  " SELECT YEAR(q.fecha) AS anio, MONTH(q.fecha) AS mes, "
                    sql_mes += "        COALESCE(SUM(CASE WHEN q.estado = 'Pagado' THEN q.monto ELSE 0 END), 0) AS pagado, "
                    sql_mes += "        COALESCE(SUM(CASE WHEN q.estado = 'Pendiente' THEN q.monto ELSE 0 END), 0) AS pendiente "
                    sql_mes += "   FROM cuotas q "
                    sql_mes += "   JOIN colegiados c ON c.id = q.colegiado_id "
                    sql_mes += where
                    sql_mes += "  GROUP BY YEAR(q.fecha), MONTH(q.fecha) "
                    sql_mes += "  ORDER BY anio DESC, mes DESC "
                    sql_mes += "  LIMIT 12 "
                    cursor.execute(sql_mes, tuple(params))
                    data["por_mes"] = list(reversed(cursor.fetchall()))

                    limite = max(1, min(int(p_limite or 25), 100))
                    offset = max(0, int(p_offset or 0))
                    sql_detalle =  " SELECT q.id, q.fecha, q.fecha_emision, q.fecha_vencimiento, "
                    sql_detalle += "        q.fecha_pago, q.concepto, q.monto, q.estado, "
                    sql_detalle += "        q.tipo, q.periodo_mes, q.periodo_anio, "
                    sql_detalle += "        c.nombre, c.matricula, cu.titulo AS curso_titulo "
                    sql_detalle += "   FROM cuotas q "
                    sql_detalle += "   JOIN colegiados c ON c.id = q.colegiado_id "
                    sql_detalle += "   LEFT JOIN cursos cu ON cu.id = q.curso_id "
                    sql_detalle += where
                    sql_detalle += "  ORDER BY q.fecha DESC, q.id DESC "
                    sql_detalle += "  LIMIT %s OFFSET %s "
                    cursor.execute(sql_detalle, tuple(params + [limite, offset]))
                    data["detalle"] = cursor.fetchall()
        return data
    except Exception:
        raise


def _filtros_reporte_cursos(p_busqueda=None, p_estado=None):
    filtros = []
    params = []
    if p_estado:
        filtros.append("cu.estado = %s")
        params.append(p_estado)
    if p_busqueda:
        filtros.append(
            "(cu.titulo LIKE %s OR cu.categoria LIKE %s OR cu.ponente LIKE %s)"
        )
        like = f"%{p_busqueda}%"
        params.extend([like, like, like])
    return filtros, params


def leer_reporte_cursos(p_busqueda=None, p_estado=None, p_limite=20):
    try:
        conn = obtenerconexion()
        data = {
            "resumen": {
                "total_cursos": 0,
                "activos": 0,
                "inactivos": 0,
                "inscritos_total": 0,
                "cupos_total": 0,
                "pagos_pendientes": 0,
                "certificados_emitidos": 0,
                "ingreso_programado": 0,
                "ingreso_pagado": 0,
                "progreso_promedio": 0,
            },
            "por_categoria": [],
            "por_ponente": [],
            "detalle": [],
        }
        inscripciones_sql = (
            " SELECT curso_id, COUNT(*) AS inscritos, "
            "        COALESCE(SUM(CASE WHEN estado_pago = 'Pagado' THEN 1 ELSE 0 END), 0) AS pagados, "
            "        COALESCE(SUM(CASE WHEN estado_pago = 'Pendiente' THEN 1 ELSE 0 END), 0) AS pendientes, "
            "        COALESCE(SUM(CASE WHEN certificado IS NOT NULL AND certificado <> '' THEN 1 ELSE 0 END), 0) AS certificados, "
            "        COALESCE(AVG(progreso), 0) AS progreso_promedio "
            "   FROM inscripciones_curso "
            "  GROUP BY curso_id "
        )
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    filtros, params = _filtros_reporte_cursos(p_busqueda, p_estado)
                    where = (" WHERE " + " AND ".join(filtros)) if filtros else ""

                    sql_resumen =  " SELECT COUNT(*) AS total_cursos, "
                    sql_resumen += "        COALESCE(SUM(CASE WHEN cu.estado = 'Activo' THEN 1 ELSE 0 END), 0) AS activos, "
                    sql_resumen += "        COALESCE(SUM(CASE WHEN cu.estado <> 'Activo' THEN 1 ELSE 0 END), 0) AS inactivos, "
                    sql_resumen += "        COALESCE(SUM(i.inscritos), 0) AS inscritos_total, "
                    sql_resumen += "        COALESCE(SUM(cu.cupos), 0) AS cupos_total, "
                    sql_resumen += "        COALESCE(SUM(i.pendientes), 0) AS pagos_pendientes, "
                    sql_resumen += "        COALESCE(SUM(i.certificados), 0) AS certificados_emitidos, "
                    sql_resumen += "        COALESCE(SUM(cu.monto * COALESCE(i.inscritos, 0)), 0) AS ingreso_programado, "
                    sql_resumen += "        COALESCE(SUM(cu.monto * COALESCE(i.pagados, 0)), 0) AS ingreso_pagado, "
                    sql_resumen += "        COALESCE(AVG(COALESCE(i.progreso_promedio, 0)), 0) AS progreso_promedio "
                    sql_resumen += "   FROM cursos cu "
                    sql_resumen += "   LEFT JOIN (" + inscripciones_sql + ") i ON i.curso_id = cu.id "
                    sql_resumen += where
                    cursor.execute(sql_resumen, tuple(params))
                    data["resumen"] = cursor.fetchone() or data["resumen"]

                    sql_categoria =  " SELECT cu.categoria, COUNT(*) AS total, "
                    sql_categoria += "        COALESCE(SUM(i.inscritos), 0) AS inscritos, "
                    sql_categoria += "        COALESCE(SUM(cu.monto * COALESCE(i.pagados, 0)), 0) AS ingreso_pagado "
                    sql_categoria += "   FROM cursos cu "
                    sql_categoria += "   LEFT JOIN (" + inscripciones_sql + ") i ON i.curso_id = cu.id "
                    sql_categoria += where
                    sql_categoria += "  GROUP BY cu.categoria "
                    sql_categoria += "  ORDER BY inscritos DESC, total DESC "
                    cursor.execute(sql_categoria, tuple(params))
                    data["por_categoria"] = cursor.fetchall()

                    sql_ponente =  " SELECT cu.ponente, COUNT(*) AS total, "
                    sql_ponente += "        COALESCE(SUM(i.inscritos), 0) AS inscritos, "
                    sql_ponente += "        COALESCE(AVG(COALESCE(i.progreso_promedio, 0)), 0) AS progreso_promedio "
                    sql_ponente += "   FROM cursos cu "
                    sql_ponente += "   LEFT JOIN (" + inscripciones_sql + ") i ON i.curso_id = cu.id "
                    sql_ponente += where
                    sql_ponente += "  GROUP BY cu.ponente "
                    sql_ponente += "  ORDER BY inscritos DESC, total DESC "
                    sql_ponente += "  LIMIT 6 "
                    cursor.execute(sql_ponente, tuple(params))
                    data["por_ponente"] = cursor.fetchall()

                    limite = max(1, min(int(p_limite or 20), 100))
                    sql_detalle =  " SELECT cu.id, cu.titulo, cu.categoria, cu.ponente, cu.monto, "
                    sql_detalle += "        cu.modalidad, cu.duracion_horas, cu.fecha_inicio, "
                    sql_detalle += "        cu.fecha_fin, cu.cupos, cu.estado, "
                    sql_detalle += "        COALESCE(i.inscritos, 0) AS inscritos, "
                    sql_detalle += "        COALESCE(i.pagados, 0) AS pagados, "
                    sql_detalle += "        COALESCE(i.pendientes, 0) AS pendientes, "
                    sql_detalle += "        COALESCE(i.certificados, 0) AS certificados, "
                    sql_detalle += "        COALESCE(i.progreso_promedio, 0) AS progreso_promedio, "
                    sql_detalle += "        (cu.monto * COALESCE(i.inscritos, 0)) AS ingreso_programado, "
                    sql_detalle += "        (cu.monto * COALESCE(i.pagados, 0)) AS ingreso_pagado "
                    sql_detalle += "   FROM cursos cu "
                    sql_detalle += "   LEFT JOIN (" + inscripciones_sql + ") i ON i.curso_id = cu.id "
                    sql_detalle += where
                    sql_detalle += "  ORDER BY cu.fecha_inicio DESC, cu.id DESC "
                    sql_detalle += "  LIMIT %s "
                    cursor.execute(sql_detalle, tuple(params + [limite]))
                    data["detalle"] = cursor.fetchall()
        return data
    except Exception:
        raise


def _filtros_reporte_colegiados(p_busqueda=None, p_estado=None):
    filtros = []
    params = []
    if p_estado:
        filtros.append("c.estado = %s")
        params.append(p_estado)
    if p_busqueda:
        filtros.append(
            "(c.nombre LIKE %s OR c.matricula LIKE %s OR c.documento LIKE %s OR c.especialidad LIKE %s)"
        )
        like = f"%{p_busqueda}%"
        params.extend([like, like, like, like])
    return filtros, params


def leer_reporte_colegiados(p_busqueda=None, p_estado=None, p_limite=20):
    try:
        conn = obtenerconexion()
        data = {
            "resumen": {
                "total_colegiados": 0,
                "vigentes": 0,
                "inactivos": 0,
                "con_deuda": 0,
                "deuda_total": 0,
                "cuotas_pendientes": 0,
                "cursos_inscritos": 0,
                "certificados_emitidos": 0,
            },
            "por_estado": [],
            "top_deudores": [],
            "detalle": [],
        }
        cuotas_sql = (
            " SELECT colegiado_id, "
            "        COALESCE(SUM(CASE WHEN estado = 'Pendiente' THEN monto ELSE 0 END), 0) AS deuda_pendiente, "
            "        COALESCE(SUM(CASE WHEN estado = 'Pendiente' THEN 1 ELSE 0 END), 0) AS cuotas_pendientes, "
            "        COALESCE(SUM(CASE WHEN estado = 'Pendiente' AND COALESCE(fecha_vencimiento, fecha) < CURDATE() THEN 1 ELSE 0 END), 0) AS cuotas_vencidas "
            "   FROM cuotas "
            "  GROUP BY colegiado_id "
        )
        inscripciones_sql = (
            " SELECT colegiado_id, COUNT(*) AS cursos_inscritos, "
            "        COALESCE(SUM(CASE WHEN estado_pago = 'Pagado' THEN 1 ELSE 0 END), 0) AS cursos_pagados, "
            "        COALESCE(SUM(CASE WHEN certificado IS NOT NULL AND certificado <> '' THEN 1 ELSE 0 END), 0) AS certificados_emitidos "
            "   FROM inscripciones_curso "
            "  GROUP BY colegiado_id "
        )
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    filtros, params = _filtros_reporte_colegiados(p_busqueda, p_estado)
                    where = (" WHERE " + " AND ".join(filtros)) if filtros else ""

                    joins =  "   LEFT JOIN (" + cuotas_sql + ") q ON q.colegiado_id = c.id "
                    joins += "   LEFT JOIN (" + inscripciones_sql + ") i ON i.colegiado_id = c.id "

                    sql_resumen =  " SELECT COUNT(*) AS total_colegiados, "
                    sql_resumen += "        COALESCE(SUM(CASE WHEN c.estado = 'Vigente' THEN 1 ELSE 0 END), 0) AS vigentes, "
                    sql_resumen += "        COALESCE(SUM(CASE WHEN c.estado <> 'Vigente' THEN 1 ELSE 0 END), 0) AS inactivos, "
                    sql_resumen += "        COALESCE(SUM(CASE WHEN COALESCE(q.deuda_pendiente, 0) > 0 THEN 1 ELSE 0 END), 0) AS con_deuda, "
                    sql_resumen += "        COALESCE(SUM(q.deuda_pendiente), 0) AS deuda_total, "
                    sql_resumen += "        COALESCE(SUM(q.cuotas_pendientes), 0) AS cuotas_pendientes, "
                    sql_resumen += "        COALESCE(SUM(i.cursos_inscritos), 0) AS cursos_inscritos, "
                    sql_resumen += "        COALESCE(SUM(i.certificados_emitidos), 0) AS certificados_emitidos "
                    sql_resumen += "   FROM colegiados c "
                    sql_resumen += joins
                    sql_resumen += where
                    cursor.execute(sql_resumen, tuple(params))
                    data["resumen"] = cursor.fetchone() or data["resumen"]

                    sql_estado =  " SELECT c.estado, COUNT(*) AS total, "
                    sql_estado += "        COALESCE(SUM(q.deuda_pendiente), 0) AS deuda_total "
                    sql_estado += "   FROM colegiados c "
                    sql_estado += joins
                    sql_estado += where
                    sql_estado += "  GROUP BY c.estado "
                    sql_estado += "  ORDER BY total DESC "
                    cursor.execute(sql_estado, tuple(params))
                    data["por_estado"] = cursor.fetchall()

                    sql_top =  " SELECT c.nombre, c.matricula, c.estado, "
                    sql_top += "        COALESCE(q.deuda_pendiente, 0) AS deuda_pendiente, "
                    sql_top += "        COALESCE(q.cuotas_pendientes, 0) AS cuotas_pendientes "
                    sql_top += "   FROM colegiados c "
                    sql_top += joins
                    sql_top += where
                    sql_top += "  ORDER BY deuda_pendiente DESC, cuotas_pendientes DESC, c.nombre ASC "
                    sql_top += "  LIMIT 6 "
                    cursor.execute(sql_top, tuple(params))
                    data["top_deudores"] = cursor.fetchall()

                    limite = max(1, min(int(p_limite or 20), 100))
                    sql_detalle =  " SELECT c.id, c.nombre, c.matricula, c.documento, "
                    sql_detalle += "        c.especialidad, c.correo, c.telefono, c.vigencia, "
                    sql_detalle += "        c.estado, c.epc_points, "
                    sql_detalle += "        COALESCE(q.deuda_pendiente, 0) AS deuda_pendiente, "
                    sql_detalle += "        COALESCE(q.cuotas_pendientes, 0) AS cuotas_pendientes, "
                    sql_detalle += "        COALESCE(q.cuotas_vencidas, 0) AS cuotas_vencidas, "
                    sql_detalle += "        COALESCE(i.cursos_inscritos, 0) AS cursos_inscritos, "
                    sql_detalle += "        COALESCE(i.certificados_emitidos, 0) AS certificados_emitidos "
                    sql_detalle += "   FROM colegiados c "
                    sql_detalle += joins
                    sql_detalle += where
                    sql_detalle += "  ORDER BY deuda_pendiente DESC, c.nombre ASC "
                    sql_detalle += "  LIMIT %s "
                    cursor.execute(sql_detalle, tuple(params + [limite]))
                    data["detalle"] = cursor.fetchall()
        return data
    except Exception:
        raise


# ============================================================
# MEDIOS DE PAGO
# ============================================================

def leer_medios_pago(p_solo_activos=False):
    try:
        conn = obtenerconexion()
        result = None
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT id, nombre, descripcion, numero_cuenta, "
                    sql += "        titular, activo, creado_en "
                    sql += "   FROM medios_pago "
                    params = ()
                    if p_solo_activos:
                        sql += " WHERE activo = 1 "
                    sql += "  ORDER BY activo DESC, nombre ASC "
                    cursor.execute(sql, params)
                    result = cursor.fetchall()
        return result
    except Exception:
        raise


def insertar_medio_pago(p_medio):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  "INSERT INTO medios_pago "
                    sql += "(nombre, descripcion, numero_cuenta, titular, activo) "
                    sql += "VALUES (%s, %s, %s, %s, %s)"
                    cursor.execute(sql, (p_medio.nombre, p_medio.descripcion,
                                        p_medio.numero_cuenta, p_medio.titular,
                                        p_medio.activo))
                conn.commit()
            return True
        return False
    except Exception as e:
        print(repr(e))
        return False


def actualizar_medio_pago(p_medio):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  "UPDATE medios_pago "
                    sql += "   SET nombre = %s, descripcion = %s, "
                    sql += "       numero_cuenta = %s, titular = %s, activo = %s "
                    sql += " WHERE id = %s "
                    cursor.execute(sql, (p_medio.nombre, p_medio.descripcion,
                                        p_medio.numero_cuenta, p_medio.titular,
                                        p_medio.activo, p_medio.id))
                conn.commit()
            return True
        return False
    except Exception as e:
        print(repr(e))
        return False


def eliminar_medio_pago(p_id):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM medios_pago WHERE id = %s", (p_id,))
                conn.commit()
            return True
        return False
    except Exception as e:
        print(repr(e))
        return False


# ============================================================
# EVIDENCIAS DE PAGO
# ============================================================

def _evidencias_tiene_auditoria(cursor):
    cursor.execute("SHOW COLUMNS FROM evidencias_pago LIKE 'revisado_por_matricula'")
    return cursor.fetchone() is not None


def leer_evidencias_pago(p_matricula=None, p_estado=None):
    try:
        conn = obtenerconexion()
        result = None
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    tiene_auditoria = _evidencias_tiene_auditoria(cursor)
                    auditoria_sql = (
                        "e.accion_revision, e.revisado_por_matricula, "
                        "e.revisado_por_nombre, e.detalle_revision, e.revisado_en"
                    )
                    if not tiene_auditoria:
                        auditoria_sql = (
                            "NULL AS accion_revision, NULL AS revisado_por_matricula, "
                            "NULL AS revisado_por_nombre, NULL AS detalle_revision, "
                            "NULL AS revisado_en"
                        )

                    sql =  " SELECT e.id, e.cuota_id, e.fecha_pago, e.numero_operacion, "
                    sql += "        e.monto, e.comentario, e.estado, e.creado_en, "
                    sql += "        e.archivo, " + auditoria_sql + ", "
                    sql += "        q.concepto, c.nombre, c.matricula, "
                    sql += "        mp.nombre AS medio_pago "
                    sql += "   FROM evidencias_pago e "
                    sql += "   JOIN cuotas q ON q.id = e.cuota_id "
                    sql += "   JOIN colegiados c ON c.id = e.colegiado_id "
                    sql += "   JOIN medios_pago mp ON mp.id = e.medio_pago_id "
                    condiciones = []
                    params = []
                    if p_matricula:
                        condiciones.append("c.matricula = %s")
                        params.append(p_matricula)
                    if p_estado:
                        condiciones.append("e.estado = %s")
                        params.append(p_estado)
                    if condiciones:
                        sql += " WHERE " + " AND ".join(condiciones)
                    sql += "  ORDER BY e.creado_en DESC, e.id DESC "
                    cursor.execute(sql, tuple(params))
                    result = cursor.fetchall()
        return result
    except Exception:
        raise


def registrar_evidencia_pago(p_matricula, p_cuota_id, p_medio_pago_id,
                             p_numero_operacion, p_fecha_pago, p_monto,
                             p_comentario, p_archivo=""):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT q.id, q.estado, q.monto, q.colegiado_id "
                        "FROM cuotas q "
                        "JOIN colegiados c ON c.id = q.colegiado_id "
                        "WHERE q.id = %s AND c.matricula = %s",
                        (p_cuota_id, p_matricula))
                    cuota = cursor.fetchone()
                    if not cuota:
                        return "No se encontro la cuota seleccionada."
                    if cuota["estado"] != "Pendiente":
                        return "Solo se puede registrar evidencia de cuotas pendientes."

                    cursor.execute(
                        "SELECT id FROM medios_pago WHERE id = %s AND activo = 1",
                        (p_medio_pago_id,))
                    if not cursor.fetchone():
                        return "Seleccione un medio de pago activo."

                    cursor.execute(
                        "SELECT id FROM evidencias_pago "
                        "WHERE cuota_id = %s AND estado = 'Pendiente'",
                        (p_cuota_id,))
                    if cursor.fetchone():
                        return "Ya existe una evidencia pendiente para esta cuota."

                    sql =  "INSERT INTO evidencias_pago "
                    sql += "(cuota_id, colegiado_id, medio_pago_id, fecha_pago, "
                    sql += " numero_operacion, monto, comentario, archivo, estado) "
                    sql += "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Pendiente')"
                    cursor.execute(sql, (p_cuota_id, cuota["colegiado_id"],
                                        p_medio_pago_id, p_fecha_pago,
                                        p_numero_operacion, p_monto,
                                        p_comentario, p_archivo))
                conn.commit()
            return "ok"
        return "No se pudo conectar con la base de datos."
    except Exception as e:
        print(repr(e))
        return "No se pudo registrar la evidencia de pago."


def actualizar_estado_evidencia_pago(p_id, p_estado, p_usuario_matricula=None,
                                     p_usuario_nombre=None, p_detalle=None):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    tiene_auditoria = _evidencias_tiene_auditoria(cursor)
                    cursor.execute(
                        "SELECT e.id, e.cuota_id, e.estado, e.monto AS evidencia_monto, "
                        "       q.concepto, q.colegiado_id, q.estado AS cuota_estado, "
                        "       q.monto, q.inscripcion_id, mp.nombre AS medio_pago "
                        "FROM evidencias_pago e "
                        "JOIN cuotas q ON q.id = e.cuota_id "
                        "JOIN medios_pago mp ON mp.id = e.medio_pago_id "
                        "WHERE e.id = %s",
                        (p_id,))
                    evidencia = cursor.fetchone()
                    if not evidencia:
                        return {"ok": False, "mensaje": "No se encontro la evidencia."}
                    if evidencia["estado"] != "Pendiente":
                        return {"ok": False, "mensaje": "La evidencia ya fue revisada."}
                    if p_estado == "Aprobado" and evidencia["cuota_estado"] != "Pendiente":
                        return {
                            "ok": False,
                            "mensaje": "No se puede aprobar: la cuota ya no esta pendiente."
                        }

                    accion = "Aprobado" if p_estado == "Aprobado" else "Anulado"
                    detalle = p_detalle or (
                        "Comprobante aprobado por administracion."
                        if p_estado == "Aprobado"
                        else "Comprobante anulado por administracion."
                    )
                    usuario_matricula = p_usuario_matricula or "admin"
                    usuario_nombre = p_usuario_nombre or "Administrador CCPL"

                    if tiene_auditoria:
                        sql =  "UPDATE evidencias_pago "
                        sql += "   SET estado = %s, accion_revision = %s, "
                        sql += "       revisado_por_matricula = %s, "
                        sql += "       revisado_por_nombre = %s, "
                        sql += "       detalle_revision = %s, revisado_en = NOW() "
                        sql += " WHERE id = %s "
                        cursor.execute(sql, (p_estado, accion, usuario_matricula,
                                            usuario_nombre, detalle, p_id))
                    else:
                        cursor.execute(
                            "UPDATE evidencias_pago SET estado = %s WHERE id = %s",
                            (p_estado, p_id))

                    if p_estado == "Aprobado":
                        emision = _emitir_comprobante_desde_cuota(
                            cursor,
                            evidencia,
                            "Revision administrativa",
                            "Evidencia: " + str(evidencia.get("medio_pago") or "Pago manual"),
                            "Pago aprobado desde evidencias por " + usuario_nombre + ".",
                            p_evidencia_id=evidencia["id"]
                        )
                        if not emision.get("ok"):
                            conn.rollback()
                            return emision

                        cursor.execute(
                            "UPDATE cuotas SET estado = 'Pagado', fecha_pago = CURDATE() WHERE id = %s",
                            (evidencia["cuota_id"],))
                        if tiene_auditoria:
                            sql =  "UPDATE evidencias_pago "
                            sql += "   SET estado = 'Rechazado', "
                            sql += "       accion_revision = 'Anulado', "
                            sql += "       revisado_por_matricula = %s, "
                            sql += "       revisado_por_nombre = %s, "
                            sql += "       detalle_revision = %s, "
                            sql += "       revisado_en = NOW() "
                            sql += " WHERE cuota_id = %s AND id <> %s "
                            sql += "   AND estado = 'Pendiente' "
                            cursor.execute(sql, (
                                usuario_matricula,
                                usuario_nombre,
                                "Anulado automaticamente porque otro comprobante fue aprobado.",
                                evidencia["cuota_id"],
                                p_id
                            ))
                        else:
                            cursor.execute(
                                "UPDATE evidencias_pago "
                                "SET estado = 'Rechazado' "
                                "WHERE cuota_id = %s AND id <> %s AND estado = 'Pendiente'",
                                (evidencia["cuota_id"], p_id))

                        if evidencia["concepto"].startswith("Inscripcion Curso: "):
                            titulo = evidencia["concepto"].replace("Inscripcion Curso: ", "", 1)
                            sql =  "UPDATE inscripciones_curso i "
                            sql += "  JOIN cursos cu ON cu.id = i.curso_id "
                            sql += "   SET i.estado_pago = 'Pagado' "
                            sql += " WHERE i.colegiado_id = %s AND cu.titulo = %s "
                            cursor.execute(sql, (evidencia["colegiado_id"], titulo))
                conn.commit()
            return {"ok": True, "mensaje": "La evidencia fue actualizada correctamente."}
        return {"ok": False, "mensaje": "No se pudo conectar con la base de datos."}
    except Exception as e:
        print(repr(e))
        if _pagos_demo_tablas_no_existen(e):
            return {
                "ok": False,
                "mensaje": "Actualice la base con database/schema.sql para emitir comprobantes."
            }
        return {"ok": False, "mensaje": "No se pudo actualizar la evidencia."}


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
                        return {"ok": False, "mensaje": "No se encontro el comprobante."}
                    if comprobante["estado"] == "Anulado":
                        return {"ok": False, "mensaje": "El comprobante ya esta anulado."}
                    if comprobante["estado"] != "Emitido":
                        return {"ok": False, "mensaje": "Solo se pueden anular comprobantes emitidos."}

                    usuario_matricula = p_usuario_matricula or "admin"
                    usuario_nombre = p_usuario_nombre or "Administrador CCPL"
                    motivo = (p_motivo or "").strip()
                    if len(motivo) < 5:
                        return {
                            "ok": False,
                            "mensaje": "Ingrese un motivo de anulacion mas detallado.",
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
                "mensaje": "No se encontro el certificado digital guardado.",
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
                        return {"ok": False, "mensaje": "No se encontro el comprobante interno."}
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
                        return {"ok": False, "mensaje": "No se encontro el comprobante fiscal."}
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
                        return {"ok": False, "mensaje": "No se encontro el comprobante fiscal."}
                    if comprobante["estado"] == "Anulado":
                        return {"ok": False, "mensaje": "El comprobante fiscal ya esta anulado."}
                    motivo = (p_motivo or "").strip()
                    if len(motivo) < 5:
                        return {
                            "ok": False,
                            "mensaje": "Ingrese un motivo de anulacion mas detallado.",
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
                    sql += "        cdr_descripcion = 'Anulacion registrada localmente. Baja SUNAT pendiente.', "
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
# CURSOS - ADMINISTRACION
# ============================================================

def _cursos_tiene_monto_inhabil(cursor):
    cursor.execute("SHOW COLUMNS FROM cursos LIKE 'monto_inhabil'")
    return cursor.fetchone() is not None


def _curso_monto_inhabil_sql(cursor):
    if _cursos_tiene_monto_inhabil(cursor):
        return "cu.monto_inhabil"
    return "cu.monto AS monto_inhabil"


def _condicion_habilidad_colegiado(cursor, p_colegiado_id):
    cursor.execute(
        "SELECT COUNT(*) AS total "
        "FROM cuotas "
        "WHERE colegiado_id = %s "
        "AND tipo = 'mensual' "
        "AND estado = 'Pendiente' "
        "AND COALESCE(fecha_vencimiento, fecha) < CURDATE()",
        (p_colegiado_id,))
    fila = cursor.fetchone() or {}
    vencidas = int(fila.get("total") or 0)
    return {
        "condicion": "Inhabil" if vencidas >= 3 else "Habil",
        "cuotas_vencidas": vencidas,
    }


def _precio_curso_por_condicion(p_curso, p_condicion):
    monto_habil = float(p_curso.get("monto") or 0)
    monto_inhabil = float(p_curso.get("monto_inhabil") or 0)
    if p_condicion == "Inhabil" and monto_inhabil > 0:
        return monto_inhabil
    return monto_habil


def leer_cursos(p_estado=None):
    try:
        conn = obtenerconexion()
        result = None
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    monto_inhabil_sql = _curso_monto_inhabil_sql(cursor)
                    sql =  " SELECT cu.id, cu.categoria, cu.titulo, cu.descripcion, "
                    sql += "        cu.monto, " + monto_inhabil_sql + ", "
                    sql += "        cu.ponente, cu.modalidad, cu.duracion_horas, "
                    sql += "        cu.fecha_inicio, cu.fecha_fin, cu.cupos, "
                    sql += "        cu.fecha_evento, cu.estado, "
                    sql += "        COUNT(i.id) AS inscritos "
                    sql += "   FROM cursos cu "
                    sql += "   LEFT JOIN inscripciones_curso i ON i.curso_id = cu.id "
                    params = ()
                    if p_estado:
                        sql += " WHERE cu.estado = %s "
                        params = (p_estado,)
                    sql += "  GROUP BY cu.id, cu.categoria, cu.titulo, cu.descripcion, "
                    sql += "           cu.monto, "
                    if _cursos_tiene_monto_inhabil(cursor):
                        sql += "           cu.monto_inhabil, "
                    sql += "           cu.ponente, cu.modalidad, cu.duracion_horas, "
                    sql += "           cu.fecha_inicio, cu.fecha_fin, cu.cupos, "
                    sql += "           cu.fecha_evento, cu.estado "
                    sql += "  ORDER BY cu.id DESC "
                    cursor.execute(sql, params)
                    result = cursor.fetchall()
        return result
    except Exception:
        raise


def insertar_curso(p_curso):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    tiene_inhabil = _cursos_tiene_monto_inhabil(cursor)
                    campos_extra = ", `monto_inhabil`" if tiene_inhabil else ""
                    valores_extra = ", %s" if tiene_inhabil else ""
                    params = [
                        p_curso.categoria, p_curso.titulo,
                        p_curso.descripcion, p_curso.monto,
                        p_curso.ponente, p_curso.modalidad,
                        p_curso.duracion_horas, p_curso.fecha_inicio,
                        p_curso.fecha_fin, p_curso.cupos,
                        p_curso.fecha_evento,
                        p_curso.estado
                    ]
                    if tiene_inhabil:
                        params.append(p_curso.monto_inhabil or p_curso.monto)

                    sql =  "INSERT INTO `cursos` (`categoria`, `titulo`, "
                    sql += "  `descripcion`, `monto`, `ponente`, `modalidad`, "
                    sql += "  `duracion_horas`, `fecha_inicio`, `fecha_fin`, "
                    sql += "  `cupos`, `fecha_evento`, "
                    sql += "  `estado`" + campos_extra + ") "
                    sql += "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s"
                    sql += valores_extra + ")"
                    cursor.execute(sql, tuple(params))
                conn.commit()
            return True
        return False
    except Exception as e:
        print(repr(e))
        return False


def actualizar_curso(p_curso):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT COUNT(*) AS total FROM inscripciones_curso WHERE curso_id = %s",
                        (p_curso.id,))
                    inscritos = cursor.fetchone()
                    total_inscritos = inscritos["total"] if inscritos else 0
                    if int(p_curso.cupos) < total_inscritos:
                        return False

                    tiene_inhabil = _cursos_tiene_monto_inhabil(cursor)
                    sql =  "UPDATE `cursos` "
                    sql += "   SET `categoria` = %s, `titulo` = %s, "
                    sql += "       `descripcion` = %s, `monto` = %s, "
                    sql += "       `ponente` = %s, `modalidad` = %s, "
                    sql += "       `duracion_horas` = %s, `fecha_inicio` = %s, "
                    sql += "       `fecha_fin` = %s, `cupos` = %s, "
                    sql += "       `fecha_evento` = %s, `estado` = %s "
                    if tiene_inhabil:
                        sql += "       , `monto_inhabil` = %s "
                    sql += " WHERE `id` = %s "
                    params = [
                        p_curso.categoria, p_curso.titulo,
                        p_curso.descripcion, p_curso.monto,
                        p_curso.ponente, p_curso.modalidad,
                        p_curso.duracion_horas, p_curso.fecha_inicio,
                        p_curso.fecha_fin, p_curso.cupos,
                        p_curso.fecha_evento, p_curso.estado
                    ]
                    if tiene_inhabil:
                        params.append(p_curso.monto_inhabil or p_curso.monto)
                    params.append(p_curso.id)
                    cursor.execute(sql, tuple(params))
                conn.commit()
            return True
        return False
    except Exception as e:
        print(repr(e))
        return False


def eliminar_curso(p_id):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM `cursos` WHERE `id` = %s", (p_id,))
                conn.commit()
            return True
        return False
    except Exception as e:
        print(repr(e))
        return False


def curso_tiene_inscripciones(p_id):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT id "
                    sql += "   FROM inscripciones_curso "
                    sql += "  WHERE curso_id = %s "
                    sql += "  LIMIT 1 "
                    cursor.execute(sql, (p_id,))
                    return cursor.fetchone() is not None
        return False
    except Exception as e:
        print(repr(e))
        return False


def curso_ya_finalizo(p_id):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT id FROM cursos WHERE id = %s AND fecha_fin < CURDATE()",
                        (p_id,))
                    return cursor.fetchone() is not None
        return False
    except Exception as e:
        print(repr(e))
        return False


# ============================================================
# INSCRIPCIONES Y CERTIFICADOS
# ============================================================

def _filtros_inscripciones_curso(p_matricula=None, p_busqueda=None):
    filtros = []
    params = []
    if p_matricula:
        filtros.append("c.matricula = %s")
        params.append(p_matricula)
    if p_busqueda:
        filtros.append("(c.matricula LIKE %s OR c.nombre LIKE %s OR cu.titulo LIKE %s)")
        like = f"%{p_busqueda}%"
        params.extend([like, like, like])
    return filtros, params


def leer_inscripciones_curso(p_matricula=None, p_busqueda=None,
                             p_limite=None, p_offset=0):
    try:
        conn = obtenerconexion()
        result = None
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT i.id, c.nombre, c.matricula, cu.titulo, "
                    sql += "        cu.categoria, COALESCE(q.monto, cu.monto) AS monto, "
                    sql += "        cu.ponente, cu.modalidad, "
                    sql += "        cu.duracion_horas, cu.fecha_inicio, cu.fecha_fin, "
                    sql += "        cu.cupos, cu.fecha_evento, cu.estado, "
                    sql += "        (SELECT COUNT(*) FROM inscripciones_curso ix "
                    sql += "          WHERE ix.curso_id = cu.id) AS inscritos, "
                    sql += "        i.progreso, i.estado_pago, i.certificado "
                    sql += "   FROM inscripciones_curso i "
                    sql += "   JOIN cursos cu ON cu.id = i.curso_id "
                    sql += "   JOIN colegiados c ON c.id = i.colegiado_id "
                    sql += "   LEFT JOIN cuotas q ON q.inscripcion_id = i.id "
                    filtros, params = _filtros_inscripciones_curso(
                        p_matricula,
                        p_busqueda
                    )
                    if filtros:
                        sql += " WHERE " + " AND ".join(filtros) + " "
                    sql += "  ORDER BY i.id DESC "
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


def contar_inscripciones_curso(p_matricula=None, p_busqueda=None):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT COUNT(*) AS total "
                    sql += "   FROM inscripciones_curso i "
                    sql += "   JOIN cursos cu ON cu.id = i.curso_id "
                    sql += "   JOIN colegiados c ON c.id = i.colegiado_id "
                    filtros, params = _filtros_inscripciones_curso(
                        p_matricula,
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


def resumir_inscripciones_curso(p_matricula=None, p_busqueda=None):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT COUNT(*) AS total, "
                    sql += "        COALESCE(SUM(CASE WHEN i.estado_pago = 'Pagado' THEN 1 ELSE 0 END), 0) AS total_pagados, "
                    sql += "        COALESCE(SUM(CASE WHEN i.estado_pago = 'Pendiente' THEN 1 ELSE 0 END), 0) AS total_pendientes, "
                    sql += "        COALESCE(SUM(CASE WHEN i.certificado IS NOT NULL AND i.certificado <> '' THEN 1 ELSE 0 END), 0) AS total_certificados "
                    sql += "   FROM inscripciones_curso i "
                    sql += "   JOIN cursos cu ON cu.id = i.curso_id "
                    sql += "   JOIN colegiados c ON c.id = i.colegiado_id "
                    filtros, params = _filtros_inscripciones_curso(
                        p_matricula,
                        p_busqueda
                    )
                    if filtros:
                        sql += " WHERE " + " AND ".join(filtros) + " "
                    cursor.execute(sql, tuple(params))
                    return cursor.fetchone() or {
                        "total": 0,
                        "total_pagados": 0,
                        "total_pendientes": 0,
                        "total_certificados": 0
                    }
        return {
            "total": 0,
            "total_pagados": 0,
            "total_pendientes": 0,
            "total_certificados": 0
        }
    except Exception:
        raise


def contar_inscritos_curso(p_curso_id):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql = "SELECT COUNT(*) AS total FROM inscripciones_curso WHERE curso_id = %s"
                    cursor.execute(sql, (p_curso_id,))
                    row = cursor.fetchone()
                    return row["total"] if row else 0
        return 0
    except Exception as e:
        print(repr(e))
        return 0


def validar_inscripcion_curso(p_matricula, p_curso_id):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT id FROM colegiados WHERE matricula = %s",
                                   (p_matricula,))
                    colegiado = cursor.fetchone()
                    if not colegiado:
                        return "No existe un colegiado con la matricula indicada."

                    cursor.execute("SELECT id, cupos, estado FROM cursos WHERE id = %s",
                                   (p_curso_id,))
                    curso = cursor.fetchone()
                    if not curso:
                        return "El curso seleccionado no existe."
                    if curso["estado"] != "Activo":
                        return "El curso no esta activo para nuevas inscripciones."

                    cursor.execute(
                        "SELECT id FROM inscripciones_curso "
                        "WHERE curso_id = %s AND colegiado_id = %s",
                        (p_curso_id, colegiado["id"]))
                    if cursor.fetchone():
                        return "El colegiado ya esta inscrito en este curso."

                    cursor.execute(
                        "SELECT COUNT(*) AS total FROM inscripciones_curso "
                        "WHERE curso_id = %s",
                        (p_curso_id,))
                    inscritos = cursor.fetchone()
                    total_inscritos = inscritos["total"] if inscritos else 0
                    if total_inscritos >= (curso["cupos"] or 0):
                        return "El curso ya no tiene cupos disponibles."

        return ""
    except Exception as e:
        print(repr(e))
        return "No se pudo validar la inscripcion del curso."


def insertar_inscripcion_curso(p_matricula, p_curso_id, p_estado_pago="Pendiente"):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT id FROM colegiados WHERE matricula = %s",
                                   (p_matricula,))
                    colegiado = cursor.fetchone()
                    if not colegiado:
                        return False

                    monto_inhabil_sql = _curso_monto_inhabil_sql(cursor)
                    sql_curso =  "SELECT id, cupos, estado, titulo, monto, "
                    sql_curso += monto_inhabil_sql + " "
                    sql_curso += "FROM cursos WHERE id = %s FOR UPDATE"
                    cursor.execute(sql_curso, (p_curso_id,))
                    curso = cursor.fetchone()
                    if not curso or curso["estado"] != "Activo":
                        return False

                    cursor.execute(
                        "SELECT id FROM inscripciones_curso "
                        "WHERE curso_id = %s AND colegiado_id = %s",
                        (p_curso_id, colegiado["id"]))
                    if cursor.fetchone():
                        return False

                    cursor.execute(
                        "SELECT COUNT(*) AS total FROM inscripciones_curso "
                        "WHERE curso_id = %s",
                        (p_curso_id,))
                    inscritos = cursor.fetchone()
                    total_inscritos = inscritos["total"] if inscritos else 0
                    cupos = curso["cupos"] or 0
                    if total_inscritos >= cupos:
                        return False

                    habilidad = _condicion_habilidad_colegiado(
                        cursor, colegiado["id"]
                    )
                    condicion = habilidad["condicion"]
                    precio_curso = _precio_curso_por_condicion(curso, condicion)

                    sql =  "INSERT INTO inscripciones_curso "
                    sql += "(curso_id, colegiado_id, progreso, estado_pago) "
                    sql += "VALUES (%s, %s, 0, %s)"
                    cursor.execute(sql, (p_curso_id, colegiado["id"], p_estado_pago))
                    inscripcion_id = cursor.lastrowid

                    concepto = (
                        "Inscripcion Curso: " + curso["titulo"] +
                        " (colegiado " + condicion.lower() + ")"
                    )
                    fecha_pago = date.today() if p_estado_pago == "Pagado" else None
                    sql_cuota =  "INSERT INTO cuotas "
                    sql_cuota += "(colegiado_id, fecha, fecha_emision, fecha_vencimiento, fecha_pago, "
                    sql_cuota += " concepto, monto, estado, tipo, curso_id, inscripcion_id) "
                    sql_cuota += "VALUES (%s, CURDATE(), CURDATE(), CURDATE(), %s, "
                    sql_cuota += " %s, %s, %s, 'curso', %s, %s)"
                    cursor.execute(sql_cuota, (colegiado["id"], fecha_pago, concepto,
                                               precio_curso, p_estado_pago,
                                               p_curso_id, inscripcion_id))
                conn.commit()
            return True
        return False
    except Exception as e:
        print(repr(e))
        return False


def actualizar_pago_inscripcion_curso(p_id, p_estado_pago):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    monto_inhabil_sql = _curso_monto_inhabil_sql(cursor)
                    sql_inscripcion =  "SELECT i.colegiado_id, i.curso_id, "
                    sql_inscripcion += "cu.titulo, cu.monto, "
                    sql_inscripcion += monto_inhabil_sql + " "
                    sql_inscripcion += "FROM inscripciones_curso i "
                    sql_inscripcion += "JOIN cursos cu ON cu.id = i.curso_id "
                    sql_inscripcion += "WHERE i.id = %s"
                    cursor.execute(sql_inscripcion, (p_id,))
                    inscripcion = cursor.fetchone()
                    if not inscripcion:
                        return False

                    habilidad = _condicion_habilidad_colegiado(
                        cursor, inscripcion["colegiado_id"]
                    )
                    condicion = habilidad["condicion"]
                    precio_curso = _precio_curso_por_condicion(
                        inscripcion, condicion
                    )

                    sql =  "UPDATE `inscripciones_curso` "
                    sql += "   SET `estado_pago` = %s "
                    sql += " WHERE `id` = %s "
                    cursor.execute(sql, (p_estado_pago, p_id))

                    if inscripcion:
                        concepto = (
                            "Inscripcion Curso: " + inscripcion["titulo"] +
                            " (colegiado " + condicion.lower() + ")"
                        )
                        concepto_base = "Inscripcion Curso: " + inscripcion["titulo"] + "%"
                        fecha_pago = date.today() if p_estado_pago == "Pagado" else None
                        cursor.execute(
                            "UPDATE cuotas "
                            "SET estado = %s, tipo = 'curso', curso_id = %s, "
                            "    inscripcion_id = %s, fecha_pago = %s, "
                            "    monto = %s, concepto = %s "
                            "WHERE inscripcion_id = %s",
                            (p_estado_pago, inscripcion["curso_id"], p_id,
                             fecha_pago, precio_curso, concepto, p_id))
                        if cursor.rowcount == 0:
                            cursor.execute(
                                "UPDATE cuotas "
                                "SET estado = %s, tipo = 'curso', curso_id = %s, "
                                "    inscripcion_id = %s, fecha_pago = %s, "
                                "    monto = %s, concepto = %s "
                                "WHERE colegiado_id = %s "
                                "AND (curso_id = %s OR concepto LIKE %s)",
                                (p_estado_pago, inscripcion["curso_id"], p_id,
                                 fecha_pago, precio_curso, concepto,
                                 inscripcion["colegiado_id"],
                                 inscripcion["curso_id"], concepto_base))
                        if cursor.rowcount == 0:
                            cursor.execute(
                                "INSERT INTO cuotas "
                                "(colegiado_id, fecha, fecha_emision, "
                                " fecha_vencimiento, fecha_pago, concepto, monto, estado, "
                                " tipo, curso_id, inscripcion_id) "
                                "VALUES (%s, CURDATE(), CURDATE(), CURDATE(), %s, "
                                " %s, %s, %s, 'curso', %s, %s)",
                                (inscripcion["colegiado_id"], fecha_pago, concepto,
                                 precio_curso, p_estado_pago,
                                 inscripcion["curso_id"], p_id))
                conn.commit()
            return True
        return False
    except Exception as e:
        print(repr(e))
        return False


def actualizar_certificado_curso(p_id, p_certificado):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  "UPDATE `inscripciones_curso` "
                    sql += "   SET `certificado` = %s "
                    sql += " WHERE `id` = %s "
                    sql += "   AND `estado_pago` = 'Pagado' "
                    sql += "   AND `progreso` >= 100 "
                    cursor.execute(sql, (p_certificado, p_id))
                    afectados = cursor.rowcount
                conn.commit()
            return afectados > 0
        return False
    except Exception as e:
        print(repr(e))
        return False


def leer_estado_certificado_curso(p_id):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT id, progreso, estado_pago, certificado "
                    sql += "   FROM inscripciones_curso "
                    sql += "  WHERE id = %s "
                    cursor.execute(sql, (p_id,))
                    return cursor.fetchone()
        return None
    except Exception as e:
        print(repr(e))
        return None


# ============================================================
# DASHBOARD ADMINISTRATIVO
# ============================================================

def _tabla_existe(cursor, tabla):
    cursor.execute("SHOW TABLES LIKE %s", (tabla,))
    return cursor.fetchone() is not None


def _columna_existe(cursor, tabla, columna):
    cursor.execute("SHOW COLUMNS FROM " + tabla + " LIKE %s", (columna,))
    return cursor.fetchone() is not None


def leer_dashboard_admin():
    try:
        conn = obtenerconexion()
        data = {
            "stats": {},
            "serie_financiera": [],
            "tramites_recientes": [],
            "tickets_recientes": [],
            "evidencias_pendientes": [],
            "cuotas_vencidas": [],
            "cursos_top": [],
            "cursos_proximos": [],
        }
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT COUNT(*) AS total, "
                        "COALESCE(SUM(CASE WHEN estado = 'Vigente' THEN 1 ELSE 0 END), 0) AS vigentes, "
                        "COALESCE(SUM(CASE WHEN estado <> 'Vigente' THEN 1 ELSE 0 END), 0) AS inactivos "
                        "FROM colegiados"
                    )
                    colegiados = cursor.fetchone() or {}
                    reconocimientos = {"total": 0}
                    if _columna_existe(cursor, "colegiados", "fecha_colegiatura"):
                        cursor.execute(
                            "SELECT COUNT(*) AS total "
                            "FROM colegiados "
                            "WHERE estado = 'Vigente' "
                            "  AND fecha_colegiatura IS NOT NULL "
                            "  AND DATE_ADD(fecha_colegiatura, INTERVAL 30 YEAR) "
                            "      BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 1 YEAR)"
                        )
                        reconocimientos = cursor.fetchone() or {}

                    cursor.execute(
                        "SELECT COUNT(*) AS total_cuotas, "
                        "COALESCE(SUM(CASE WHEN estado = 'Pendiente' THEN monto ELSE 0 END), 0) AS deuda_total, "
                        "COALESCE(SUM(CASE WHEN estado = 'Pendiente' THEN 1 ELSE 0 END), 0) AS cuotas_pendientes, "
                        "COALESCE(SUM(CASE WHEN estado = 'Pendiente' AND COALESCE(fecha_vencimiento, fecha) < CURDATE() THEN monto ELSE 0 END), 0) AS deuda_vencida, "
                        "COALESCE(SUM(CASE WHEN estado = 'Pendiente' AND COALESCE(fecha_vencimiento, fecha) < CURDATE() THEN 1 ELSE 0 END), 0) AS cuotas_vencidas, "
                        "COALESCE(SUM(CASE WHEN estado = 'Pagado' THEN monto ELSE 0 END), 0) AS total_pagado, "
                        "COALESCE(SUM(CASE WHEN estado = 'Pagado' AND fecha_pago >= DATE_FORMAT(CURDATE(), '%Y-%m-01') THEN monto ELSE 0 END), 0) AS pagado_mes "
                        "FROM cuotas"
                    )
                    cuotas = cursor.fetchone() or {}

                    cursor.execute(
                        "SELECT COUNT(*) AS total, "
                        "COALESCE(SUM(CASE WHEN estado = 'Pendiente' THEN 1 ELSE 0 END), 0) AS pendientes "
                        "FROM evidencias_pago"
                    )
                    evidencias = cursor.fetchone() or {}

                    cursor.execute(
                        "SELECT COUNT(*) AS total, "
                        "COALESCE(SUM(CASE WHEN estado = 'Activo' THEN 1 ELSE 0 END), 0) AS activos, "
                        "COALESCE(SUM(CASE WHEN estado = 'Activo' AND (ponente = '' OR ponente = 'Por definir') THEN 1 ELSE 0 END), 0) AS sin_ponente, "
                        "COALESCE(SUM(CASE WHEN estado = 'Activo' AND fecha_inicio BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 30 DAY) THEN 1 ELSE 0 END), 0) AS proximos "
                        "FROM cursos"
                    )
                    cursos = cursor.fetchone() or {}

                    cursor.execute(
                        "SELECT COUNT(*) AS total, "
                        "COALESCE(SUM(CASE WHEN estado_pago = 'Pagado' THEN 1 ELSE 0 END), 0) AS pagados, "
                        "COALESCE(SUM(CASE WHEN estado_pago = 'Pendiente' THEN 1 ELSE 0 END), 0) AS pagos_pendientes, "
                        "COALESCE(SUM(CASE WHEN progreso >= 100 AND estado_pago = 'Pagado' AND (certificado IS NULL OR certificado = '') THEN 1 ELSE 0 END), 0) AS certificados_pendientes "
                        "FROM inscripciones_curso"
                    )
                    inscripciones = cursor.fetchone() or {}

                    cursor.execute(
                        "SELECT COUNT(*) AS abiertos "
                        "FROM tickets WHERE estado <> 'Cerrado'"
                    )
                    tickets = cursor.fetchone() or {}

                    tramites = {"pendientes": 0}
                    tabla_tramites = _tabla_existe(cursor, "tramites")
                    if tabla_tramites:
                        cursor.execute(
                            "SELECT COUNT(*) AS pendientes "
                            "FROM tramites WHERE estado = 'Pendiente'"
                        )
                        tramites = cursor.fetchone() or {}

                    data["stats"] = {
                        "colegiados_total": colegiados.get("total", 0) or 0,
                        "colegiados_activos": colegiados.get("vigentes", 0) or 0,
                        "colegiados_inactivos": colegiados.get("inactivos", 0) or 0,
                        "deuda_total": cuotas.get("deuda_total", 0) or 0,
                        "deuda_vencida": cuotas.get("deuda_vencida", 0) or 0,
                        "cuotas_pendientes": cuotas.get("cuotas_pendientes", 0) or 0,
                        "cuotas_vencidas": cuotas.get("cuotas_vencidas", 0) or 0,
                        "recaudado_mes": cuotas.get("pagado_mes", 0) or 0,
                        "total_pagado": cuotas.get("total_pagado", 0) or 0,
                        "evidencias_pendientes": evidencias.get("pendientes", 0) or 0,
                        "cursos_activos": cursos.get("activos", 0) or 0,
                        "cursos_sin_ponente": cursos.get("sin_ponente", 0) or 0,
                        "cursos_proximos": cursos.get("proximos", 0) or 0,
                        "inscripciones_total": inscripciones.get("total", 0) or 0,
                        "pagos_curso_pendientes": inscripciones.get("pagos_pendientes", 0) or 0,
                        "certificados_pendientes": inscripciones.get("certificados_pendientes", 0) or 0,
                        "tickets_abiertos": tickets.get("abiertos", 0) or 0,
                        "tramites_pendientes": tramites.get("pendientes", 0) or 0,
                        "reconocimientos_30": reconocimientos.get("total", 0) or 0,
                    }

                    hoy = date.today()
                    inicio_mes = date(hoy.year, hoy.month, 1)
                    meses = []
                    anio = inicio_mes.year
                    mes = inicio_mes.month
                    for _ in range(5):
                        if mes == 1:
                            anio -= 1
                            mes = 12
                        else:
                            mes -= 1
                    for _ in range(6):
                        meses.append((anio, mes))
                        anio, mes = _sumar_un_mes(anio, mes)

                    cursor.execute(
                        "SELECT YEAR(fecha) AS anio, MONTH(fecha) AS mes, "
                        "       COALESCE(SUM(CASE WHEN estado = 'Pagado' THEN monto ELSE 0 END), 0) AS pagado, "
                        "       COALESCE(SUM(CASE WHEN estado = 'Pendiente' THEN monto ELSE 0 END), 0) AS pendiente "
                        "FROM cuotas "
                        "WHERE fecha >= %s "
                        "GROUP BY YEAR(fecha), MONTH(fecha) "
                        "ORDER BY anio ASC, mes ASC",
                        (date(meses[0][0], meses[0][1], 1),)
                    )
                    por_periodo = {
                        (int(fila["anio"]), int(fila["mes"])): fila
                        for fila in cursor.fetchall()
                    }
                    serie = []
                    maximo = 1
                    for anio_item, mes_item in meses:
                        fila = por_periodo.get((anio_item, mes_item), {})
                        pagado = float(fila.get("pagado", 0) or 0)
                        pendiente = float(fila.get("pendiente", 0) or 0)
                        maximo = max(maximo, pagado, pendiente)
                        serie.append({
                            "periodo": f"{anio_item}-{mes_item:02d}",
                            "etiqueta": _nombre_mes(mes_item)[:3],
                            "pagado": pagado,
                            "pendiente": pendiente,
                        })
                    for item in serie:
                        item["pagado_pct"] = round((item["pagado"] / maximo) * 100, 1)
                        item["pendiente_pct"] = round((item["pendiente"] / maximo) * 100, 1)
                    data["serie_financiera"] = serie

                    if tabla_tramites:
                        cursor.execute(
                            "SELECT id, matricula, nombre, tipo_tramite, asunto, "
                            "       estado, fecha_solicitud "
                            "FROM tramites "
                            "ORDER BY fecha_solicitud DESC, id DESC LIMIT 5"
                        )
                        data["tramites_recientes"] = cursor.fetchall()

                    cursor.execute(
                        "SELECT id, matricula, categoria, asunto, estado, creado_en "
                        "FROM tickets ORDER BY id DESC LIMIT 5"
                    )
                    data["tickets_recientes"] = cursor.fetchall()

                    cursor.execute(
                        "SELECT e.id, e.fecha_pago, e.monto, e.estado, q.concepto, "
                        "       c.nombre, c.matricula, mp.nombre AS medio_pago "
                        "FROM evidencias_pago e "
                        "JOIN cuotas q ON q.id = e.cuota_id "
                        "JOIN colegiados c ON c.id = e.colegiado_id "
                        "JOIN medios_pago mp ON mp.id = e.medio_pago_id "
                        "WHERE e.estado = 'Pendiente' "
                        "ORDER BY e.creado_en DESC, e.id DESC LIMIT 5"
                    )
                    data["evidencias_pendientes"] = cursor.fetchall()

                    cursor.execute(
                        "SELECT q.id, q.concepto, q.monto, "
                        "       COALESCE(q.fecha_vencimiento, q.fecha) AS fecha_vencimiento, "
                        "       c.nombre, c.matricula "
                        "FROM cuotas q "
                        "JOIN colegiados c ON c.id = q.colegiado_id "
                        "WHERE q.estado = 'Pendiente' "
                        "  AND COALESCE(q.fecha_vencimiento, q.fecha) < CURDATE() "
                        "ORDER BY COALESCE(q.fecha_vencimiento, q.fecha) ASC, q.id DESC LIMIT 5"
                    )
                    data["cuotas_vencidas"] = cursor.fetchall()

                    cursor.execute(
                        "SELECT cu.id, cu.titulo, cu.cupos, cu.monto, "
                        "       COUNT(i.id) AS inscritos, "
                        "       COALESCE(SUM(CASE WHEN i.estado_pago = 'Pagado' THEN cu.monto ELSE 0 END), 0) AS pagado "
                        "FROM cursos cu "
                        "LEFT JOIN inscripciones_curso i ON i.curso_id = cu.id "
                        "GROUP BY cu.id, cu.titulo, cu.cupos, cu.monto "
                        "ORDER BY inscritos DESC, cu.id DESC LIMIT 5"
                    )
                    data["cursos_top"] = cursor.fetchall()

                    cursor.execute(
                        "SELECT id, titulo, ponente, fecha_inicio, cupos "
                        "FROM cursos "
                        "WHERE estado = 'Activo' AND fecha_inicio >= CURDATE() "
                        "ORDER BY fecha_inicio ASC, id DESC LIMIT 5"
                    )
                    data["cursos_proximos"] = cursor.fetchall()
        return data
    except Exception:
        raise
