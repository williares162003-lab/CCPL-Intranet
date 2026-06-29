from bd import obtenerconexion

# ============================================================
# SEGUIMIENTO DEL PONENTE
# ============================================================

def _aplicar_filtros_seguimiento_ponente(sql, params, p_curso_id=None,
                                          p_estado_pago=None, p_progreso=None,
                                          p_busqueda=None):
    if p_curso_id:
        sql += "    AND cu.id = %s "
        params.append(p_curso_id)

    if p_estado_pago:
        sql += "    AND i.estado_pago = %s "
        params.append(p_estado_pago)

    if p_progreso == "bajo":
        sql += "    AND i.progreso < 50 "
    elif p_progreso == "en_proceso":
        sql += "    AND i.progreso >= 50 AND i.progreso < 100 "
    elif p_progreso == "finalizado":
        sql += "    AND i.progreso >= 100 "

    if p_busqueda:
        like = "%" + p_busqueda + "%"
        sql += "    AND (c.nombre LIKE %s OR c.matricula LIKE %s "
        sql += "     OR cu.titulo LIKE %s) "
        params.extend([like, like, like])

    return sql, params


def leer_seguimiento_ponente(p_ponente, p_curso_id=None, p_estado_pago=None,
                             p_progreso=None, p_busqueda=None, p_limite=20,
                             p_offset=0):
    try:
        conn = obtenerconexion()
        result = []
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT i.id AS inscripcion_id, i.progreso, "
                    sql += "        i.estado_pago, i.certificado, i.creado_en, "
                    sql += "        c.nombre, c.matricula, c.correo, c.telefono, "
                    sql += "        cu.id AS curso_id, cu.titulo AS curso_titulo, "
                    sql += "        cu.categoria, cu.estado AS curso_estado, "
                    sql += "        cu.fecha_inicio, cu.fecha_fin, "
                    sql += "        (SELECT COUNT(*) "
                    sql += "           FROM contenido_curso cx "
                    sql += "          WHERE cx.curso_id = cu.id) AS total_materiales "
                    sql += "   FROM inscripciones_curso i "
                    sql += "   JOIN colegiados c ON c.id = i.colegiado_id "
                    sql += "   JOIN cursos cu ON cu.id = i.curso_id "
                    sql += "  WHERE cu.ponente = %s "
                    params = [p_ponente]
                    sql, params = _aplicar_filtros_seguimiento_ponente(
                        sql, params, p_curso_id, p_estado_pago, p_progreso,
                        p_busqueda
                    )
                    sql += "  ORDER BY CASE "
                    sql += "             WHEN i.estado_pago = 'Pendiente' THEN 0 "
                    sql += "             WHEN i.progreso < 50 THEN 1 "
                    sql += "             ELSE 2 "
                    sql += "           END, cu.fecha_inicio DESC, c.nombre ASC "
                    sql += " LIMIT %s OFFSET %s "
                    params.extend([int(p_limite), int(p_offset)])
                    cursor.execute(sql, tuple(params))
                    result = cursor.fetchall()
        return result
    except Exception as e:
        print(repr(e))
        return []


def contar_seguimiento_ponente(p_ponente, p_curso_id=None, p_estado_pago=None,
                               p_progreso=None, p_busqueda=None):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT COUNT(*) AS total "
                    sql += "   FROM inscripciones_curso i "
                    sql += "   JOIN colegiados c ON c.id = i.colegiado_id "
                    sql += "   JOIN cursos cu ON cu.id = i.curso_id "
                    sql += "  WHERE cu.ponente = %s "
                    params = [p_ponente]
                    sql, params = _aplicar_filtros_seguimiento_ponente(
                        sql, params, p_curso_id, p_estado_pago, p_progreso,
                        p_busqueda
                    )
                    cursor.execute(sql, tuple(params))
                    fila = cursor.fetchone() or {}
                    return fila.get("total", 0) or 0
        return 0
    except Exception as e:
        print(repr(e))
        return 0


def resumir_seguimiento_ponente(p_ponente):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT COUNT(*) AS total_inscritos, "
                    sql += "        COALESCE(AVG(i.progreso), 0) AS progreso_promedio, "
                    sql += "        COALESCE(SUM(CASE WHEN i.estado_pago = 'Pendiente' THEN 1 ELSE 0 END), 0) AS pagos_pendientes, "
                    sql += "        COALESCE(SUM(CASE WHEN i.progreso < 50 THEN 1 ELSE 0 END), 0) AS bajo_progreso, "
                    sql += "        COALESCE(SUM(CASE WHEN i.progreso >= 100 THEN 1 ELSE 0 END), 0) AS finalizados, "
                    sql += "        COALESCE(SUM(CASE WHEN i.certificado IS NOT NULL AND i.certificado <> '' THEN 1 ELSE 0 END), 0) AS certificados "
                    sql += "   FROM inscripciones_curso i "
                    sql += "   JOIN cursos cu ON cu.id = i.curso_id "
                    sql += "  WHERE cu.ponente = %s "
                    cursor.execute(sql, (p_ponente,))
                    return cursor.fetchone()
        return {}
    except Exception as e:
        print(repr(e))
        return {}
