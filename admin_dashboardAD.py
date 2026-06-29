import json
import re
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4
from bd import obtenerconexion

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
