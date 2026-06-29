import json
import re
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4
from bd import obtenerconexion
from admin_modelosAD import clsCurso
from admin_crudAD import _leer_registro_por_id, _actualizar_registro_crud, _eliminar_registro_crud

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
                        return "No existe un colegiado con la matrícula indicada."

                    cursor.execute("SELECT id, cupos, estado FROM cursos WHERE id = %s",
                                   (p_curso_id,))
                    curso = cursor.fetchone()
                    if not curso:
                        return "El curso seleccionado no existe."
                    if curso["estado"] != "Activo":
                        return "El curso no está activo para nuevas inscripciones."

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
        return "No se pudo validar la inscripción del curso."


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
                        "Inscripción Curso: " + curso["titulo"] +
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
                            "Inscripción Curso: " + inscripcion["titulo"] +
                            " (colegiado " + condicion.lower() + ")"
                        )
                        concepto_base = "Inscripción Curso: " + inscripcion["titulo"] + "%"
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
# FUNCIONES CRUD - CURSOS E INSCRIPCIONES
# ============================================================

def leer_curso_admin_por_id(p_id):
    return _leer_registro_por_id("cursos", p_id)


def leer_inscripcion_curso_por_id(p_id):
    return _leer_registro_por_id("inscripciones_curso", p_id)


def actualizar_inscripcion_curso_crud(p_datos):
    columnas = ["curso_id", "colegiado_id", "progreso", "estado_pago", "certificado"]
    return _actualizar_registro_crud("inscripciones_curso", p_datos, columnas)


def eliminar_inscripcion_curso(p_id):
    return _eliminar_registro_crud("inscripciones_curso", p_id)
