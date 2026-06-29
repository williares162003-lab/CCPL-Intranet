from bd import obtenerconexion

# ============================================================
# CURSOS DEL PONENTE
# ============================================================

def leer_cursos_ponente(p_ponente):
    try:
        conn = obtenerconexion()
        result = None
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT cu.id, cu.categoria, cu.titulo, cu.descripcion, "
                    sql += "        cu.monto, cu.ponente, cu.modalidad, cu.duracion_horas, "
                    sql += "        cu.fecha_inicio, cu.fecha_fin, cu.cupos, "
                    sql += "        cu.fecha_evento, "
                    sql += "        cu.estado, COUNT(i.id) AS inscritos, "
                    sql += "        COALESCE(AVG(i.progreso), 0) AS progreso_promedio, "
                    sql += "        (SELECT COUNT(*) "
                    sql += "           FROM contenido_curso cx "
                    sql += "          WHERE cx.curso_id = cu.id) AS total_materiales "
                    sql += "   FROM cursos cu "
                    sql += "   LEFT JOIN inscripciones_curso i ON i.curso_id = cu.id "
                    sql += "  WHERE cu.ponente = %s "
                    sql += "  GROUP BY cu.id, cu.categoria, cu.titulo, cu.descripcion, "
                    sql += "           cu.monto, cu.ponente, cu.modalidad, cu.duracion_horas, "
                    sql += "           cu.fecha_inicio, cu.fecha_fin, cu.cupos, "
                    sql += "           cu.fecha_evento, cu.estado "
                    sql += "  ORDER BY cu.fecha_inicio DESC, cu.id DESC "
                    cursor.execute(sql, (p_ponente,))
                    result = cursor.fetchall()
        return result
    except Exception:
        raise


def leer_curso_ponente(p_id, p_ponente):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT cu.id, cu.categoria, cu.titulo, cu.descripcion, "
                    sql += "        cu.monto, cu.ponente, cu.modalidad, cu.duracion_horas, "
                    sql += "        cu.fecha_inicio, cu.fecha_fin, cu.cupos, "
                    sql += "        cu.fecha_evento, "
                    sql += "        cu.estado, COUNT(i.id) AS inscritos, "
                    sql += "        COALESCE(AVG(i.progreso), 0) AS progreso_promedio "
                    sql += "   FROM cursos cu "
                    sql += "   LEFT JOIN inscripciones_curso i ON i.curso_id = cu.id "
                    sql += "  WHERE cu.id = %s AND cu.ponente = %s "
                    sql += "  GROUP BY cu.id, cu.categoria, cu.titulo, cu.descripcion, "
                    sql += "           cu.monto, cu.ponente, cu.modalidad, cu.duracion_horas, "
                    sql += "           cu.fecha_inicio, cu.fecha_fin, cu.cupos, "
                    sql += "           cu.fecha_evento, cu.estado "
                    cursor.execute(sql, (p_id, p_ponente))
                    return cursor.fetchone()
        return None
    except Exception:
        raise


def leer_curso_por_id(p_id):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT id, categoria, titulo, descripcion, monto, ponente, "
                    sql += "        modalidad, duracion_horas, fecha_inicio, fecha_fin, "
                    sql += "        cupos, fecha_evento, estado "
                    sql += "   FROM cursos "
                    sql += "  WHERE id = %s "
                    cursor.execute(sql, (p_id,))
                    return cursor.fetchone()
        return None
    except Exception:
        return None


def leer_inscripcion_detalle(p_id):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT i.id AS inscripcion_id, i.progreso, i.estado_pago, "
                    sql += "        i.certificado, c.nombre, c.matricula, "
                    sql += "        cu.id AS curso_id, cu.titulo, cu.fecha_inicio, "
                    sql += "        cu.fecha_fin, cu.fecha_evento, cu.monto "
                    sql += "   FROM inscripciones_curso i "
                    sql += "   JOIN colegiados c ON c.id = i.colegiado_id "
                    sql += "   JOIN cursos cu ON cu.id = i.curso_id "
                    sql += "  WHERE i.id = %s "
                    cursor.execute(sql, (p_id,))
                    return cursor.fetchone()
        return None
    except Exception:
        return None


def leer_matriculas_inscritos_curso(p_curso_id):
    try:
        conn = obtenerconexion()
        result = []
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT c.matricula, c.nombre, i.id AS inscripcion_id "
                    sql += "   FROM inscripciones_curso i "
                    sql += "   JOIN colegiados c ON c.id = i.colegiado_id "
                    sql += "  WHERE i.curso_id = %s "
                    sql += "  ORDER BY c.nombre ASC "
                    cursor.execute(sql, (p_curso_id,))
                    result = cursor.fetchall()
        return result
    except Exception:
        return []


def leer_inscritos_curso_ponente(p_id, p_ponente):
    try:
        conn = obtenerconexion()
        result = None
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT i.id, c.nombre, c.matricula, i.progreso, "
                    sql += "        i.estado_pago, i.certificado, i.creado_en "
                    sql += "   FROM inscripciones_curso i "
                    sql += "   JOIN colegiados c ON c.id = i.colegiado_id "
                    sql += "   JOIN cursos cu ON cu.id = i.curso_id "
                    sql += "  WHERE cu.id = %s AND cu.ponente = %s "
                    sql += "  ORDER BY c.nombre ASC "
                    cursor.execute(sql, (p_id, p_ponente))
                    result = cursor.fetchall()
        return result
    except Exception:
        raise
