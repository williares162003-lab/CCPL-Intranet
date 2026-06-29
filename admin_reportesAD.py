import json
import re
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4
from bd import obtenerconexion

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
