import json
import os
import re
import unicodedata
from datetime import date, datetime, timedelta
from urllib import error, request
from uuid import uuid4
from bd import obtenerconexion

# ============================================================
# CURSOS DEL COLEGIADO
# ============================================================

def _cursos_tiene_monto_inhabil(cursor):
    cursor.execute("SHOW COLUMNS FROM cursos LIKE 'monto_inhabil'")
    return cursor.fetchone() is not None


def _curso_monto_inhabil_sql(cursor):
    if _cursos_tiene_monto_inhabil(cursor):
        return "cu.monto_inhabil"
    return "cu.monto AS monto_inhabil"


def _condicion_habilidad_colegiado(cursor, p_matricula):
    cursor.execute(
        "SELECT c.id, COUNT(q.id) AS cuotas_vencidas "
        "FROM colegiados c "
        "LEFT JOIN cuotas q ON q.colegiado_id = c.id "
        " AND q.tipo = 'mensual' "
        " AND q.estado = 'Pendiente' "
        " AND COALESCE(q.fecha_vencimiento, q.fecha) < CURDATE() "
        "WHERE c.matricula = %s "
        "GROUP BY c.id",
        (p_matricula,))
    fila = cursor.fetchone() or {}
    vencidas = int(fila.get("cuotas_vencidas") or 0)
    return {
        "condicion": "Inhabil" if vencidas >= 3 else "Habil",
        "cuotas_vencidas": vencidas,
    }


def _aplicar_precio_curso_por_condicion(p_curso, p_condicion):
    monto_habil = float(p_curso.get("monto") or 0)
    monto_inhabil = float(p_curso.get("monto_inhabil") or 0)
    precio = monto_habil
    if p_condicion == "Inhabil" and monto_inhabil > 0:
        precio = monto_inhabil
    p_curso["precio_aplicado"] = precio
    p_curso["condicion_precio"] = p_condicion
    return p_curso


def leer_cursos_colegiado(p_matricula):
    try:
        conn = obtenerconexion()
        result = None
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT i.id AS inscripcion_id, cu.id, cu.categoria, cu.titulo, cu.descripcion, "
                    sql += "        COALESCE(q.monto, cu.monto) AS monto, "
                    sql += "        cu.ponente, cu.modalidad, "
                    sql += "        cu.duracion_horas, cu.fecha_inicio, cu.fecha_fin, "
                    sql += "        cu.cupos, cu.fecha_evento, "
                    sql += "        i.progreso, i.estado_pago, "
                    sql += "        i.certificado "
                    sql += "   FROM inscripciones_curso i "
                    sql += "   JOIN cursos cu ON cu.id = i.curso_id "
                    sql += "   JOIN colegiados c ON c.id = i.colegiado_id "
                    sql += "   LEFT JOIN cuotas q ON q.inscripcion_id = i.id "
                    sql += "  WHERE c.matricula = %s "
                    sql += "  ORDER BY i.id DESC "
                    cursor.execute(sql, (p_matricula,))
                    result = cursor.fetchall()
        return result
    except Exception:
        raise


def leer_curso_inscrito_colegiado(p_inscripcion_id, p_matricula):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT i.id AS inscripcion_id, cu.id, cu.categoria, "
                    sql += "        cu.titulo, cu.descripcion, "
                    sql += "        COALESCE(q.monto, cu.monto) AS monto, "
                    sql += "        cu.ponente, "
                    sql += "        cu.modalidad, cu.duracion_horas, cu.fecha_inicio, "
                    sql += "        cu.fecha_fin, cu.cupos, "
                    sql += "        cu.fecha_evento, i.progreso, i.estado_pago, "
                    sql += "        i.certificado "
                    sql += "   FROM inscripciones_curso i "
                    sql += "   JOIN cursos cu ON cu.id = i.curso_id "
                    sql += "   JOIN colegiados c ON c.id = i.colegiado_id "
                    sql += "   LEFT JOIN cuotas q ON q.inscripcion_id = i.id "
                    sql += "  WHERE i.id = %s AND c.matricula = %s "
                    cursor.execute(sql, (p_inscripcion_id, p_matricula))
                    return cursor.fetchone()
        return None
    except Exception:
        raise


def leer_cursos_disponibles_colegiado(p_matricula):
    try:
        conn = obtenerconexion()
        result = None
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    habilidad = _condicion_habilidad_colegiado(
                        cursor, p_matricula
                    )
                    monto_inhabil_sql = _curso_monto_inhabil_sql(cursor)
                    sql =  " SELECT cu.id, cu.categoria, cu.titulo, cu.descripcion, "
                    sql += "        cu.monto, " + monto_inhabil_sql + ", "
                    sql += "        cu.ponente, cu.modalidad, cu.duracion_horas, "
                    sql += "        cu.fecha_inicio, cu.fecha_fin, cu.cupos, "
                    sql += "        cu.fecha_evento, "
                    sql += "        cu.estado, COUNT(i.id) AS inscritos "
                    sql += "   FROM cursos cu "
                    sql += "   LEFT JOIN inscripciones_curso i ON i.curso_id = cu.id "
                    sql += "  WHERE cu.estado = 'Activo' "
                    sql += "    AND NOT EXISTS ( "
                    sql += "        SELECT 1 "
                    sql += "          FROM inscripciones_curso ix "
                    sql += "          JOIN colegiados cx ON cx.id = ix.colegiado_id "
                    sql += "         WHERE ix.curso_id = cu.id AND cx.matricula = %s "
                    sql += "    ) "
                    sql += "  GROUP BY cu.id, cu.categoria, cu.titulo, cu.descripcion, "
                    sql += "           cu.monto, "
                    if _cursos_tiene_monto_inhabil(cursor):
                        sql += "           cu.monto_inhabil, "
                    sql += "           cu.ponente, cu.modalidad, cu.duracion_horas, "
                    sql += "           cu.fecha_inicio, cu.fecha_fin, cu.cupos, "
                    sql += "           cu.fecha_evento, cu.estado "
                    sql += "  ORDER BY cu.fecha_inicio ASC, cu.id DESC "
                    cursor.execute(sql, (p_matricula,))
                    result = cursor.fetchall()
                    result = [
                        _aplicar_precio_curso_por_condicion(
                            dict(curso), habilidad["condicion"]
                        )
                        for curso in result
                    ]
        return result
    except Exception:
        raise


def leer_certificado_curso_colegiado(p_inscripcion_id, p_matricula):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT i.id AS inscripcion_id, i.progreso, "
                    sql += "        i.estado_pago, i.certificado, "
                    sql += "        c.nombre, c.matricula, c.documento, c.especialidad, "
                    sql += "        cu.titulo, cu.categoria, cu.ponente, cu.modalidad, "
                    sql += "        cu.duracion_horas, cu.fecha_evento "
                    sql += "   FROM inscripciones_curso i "
                    sql += "   JOIN colegiados c ON c.id = i.colegiado_id "
                    sql += "   JOIN cursos cu ON cu.id = i.curso_id "
                    sql += "  WHERE i.id = %s AND c.matricula = %s "
                    cursor.execute(sql, (p_inscripcion_id, p_matricula))
                    return cursor.fetchone()
        return None
    except Exception:
        raise


def finalizar_inscripcion_curso(p_id, p_matricula=None):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  "SELECT i.id, i.progreso, i.estado_pago "
                    sql += "  FROM inscripciones_curso i "
                    sql += "  JOIN colegiados c ON c.id = i.colegiado_id "
                    sql += " WHERE i.id = %s "
                    params = [p_id]
                    if p_matricula:
                        sql += " AND c.matricula = %s "
                        params.append(p_matricula)
                    cursor.execute(sql, tuple(params))
                    inscripcion = cursor.fetchone()

                    if not inscripcion:
                        return "No se encontró la inscripción del curso."
                    if inscripcion["estado_pago"] != "Pagado":
                        return "No se puede finalizar el curso porque el pago está pendiente."
                    if inscripcion["progreso"] >= 100:
                        return "El curso ya se encuentra finalizado."

                    cursor.execute(
                        "UPDATE inscripciones_curso SET progreso = 100 WHERE id = %s",
                        (p_id,))
                conn.commit()
            return "ok"
        return "No se pudo conectar con la base de datos."
    except Exception as e:
        print(repr(e))
        return "No se pudo finalizar el curso."
