from bd import obtenerconexion


# ============================================================
# MODELOS DEL AULA
# ============================================================

class clsContenidoCurso:
    def __init__(self, p_id=None, p_curso_id=None, p_titulo=None,
                 p_descripcion=None, p_enlace=None, p_archivo=None):
        self.id = p_id
        self.curso_id = p_curso_id
        self.titulo = p_titulo
        self.descripcion = p_descripcion
        self.enlace = p_enlace
        self.archivo = p_archivo


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


# ============================================================
# CONTENIDO DEL CURSO
# ============================================================

def actualizar_contenido_curso_ponente(p_id, p_ponente, p_descripcion):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT id FROM cursos WHERE id = %s AND ponente = %s",
                        (p_id, p_ponente))
                    if not cursor.fetchone():
                        return False

                    sql =  "UPDATE cursos "
                    sql += "   SET descripcion = %s "
                    sql += " WHERE id = %s AND ponente = %s "
                    cursor.execute(sql, (p_descripcion, p_id, p_ponente))
                conn.commit()
            return True
        return False
    except Exception as e:
        print(repr(e))
        return False


def leer_contenidos_curso(p_curso_id):
    try:
        conn = obtenerconexion()
        result = []
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT cc.id, cc.curso_id, cc.titulo, "
                    sql += "        cc.descripcion, cc.enlace, cc.archivo, cc.creado_en "
                    sql += "   FROM contenido_curso cc "
                    sql += "  WHERE cc.curso_id = %s "
                    sql += "  ORDER BY cc.id ASC "
                    cursor.execute(sql, (p_curso_id,))
                    result = cursor.fetchall()
        return result
    except Exception as e:
        print(repr(e))
        return []


def insertar_contenido_curso_ponente(p_curso_id, p_ponente, p_contenido):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT id FROM cursos WHERE id = %s AND ponente = %s",
                        (p_curso_id, p_ponente))
                    if not cursor.fetchone():
                        return False
                    sql =  "INSERT INTO contenido_curso "
                    sql += "(curso_id, titulo, descripcion, enlace, archivo) "
                    sql += "VALUES (%s, %s, %s, %s, %s)"
                    cursor.execute(sql, (p_curso_id, p_contenido.titulo,
                                        p_contenido.descripcion,
                                        p_contenido.enlace,
                                        p_contenido.archivo))
                conn.commit()
            return True
        return False
    except Exception as e:
        print(repr(e))
        return False


def eliminar_contenido_curso_ponente(p_id, p_ponente):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  "DELETE cc FROM contenido_curso cc "
                    sql += "JOIN cursos cu ON cu.id = cc.curso_id "
                    sql += "WHERE cc.id = %s AND cu.ponente = %s "
                    cursor.execute(sql, (p_id, p_ponente))
                    afectados = cursor.rowcount
                conn.commit()
            return afectados > 0
        return False
    except Exception as e:
        print(repr(e))
        return False


def actualizar_progreso_curso_ponente(p_id, p_ponente, p_progreso):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  "UPDATE inscripciones_curso i "
                    sql += "  JOIN cursos cu ON cu.id = i.curso_id "
                    sql += "   SET i.progreso = %s "
                    sql += " WHERE i.id = %s AND cu.ponente = %s "
                    cursor.execute(sql, (p_progreso, p_id, p_ponente))
                    afectados = cursor.rowcount
                conn.commit()
            return afectados > 0
        return False
    except Exception as e:
        print(repr(e))
        return False


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


# ============================================================
# NOTIFICACIONES DEL PONENTE
# ============================================================

def leer_notificaciones_ponente(p_ponente, p_limite=8):
    avisos = []
    try:
        resumen_seguimiento = resumir_seguimiento_ponente(p_ponente) or {}

        bajo = int(resumen_seguimiento.get("bajo_progreso") or 0)
        if bajo:
            avisos.append({
                "tipo": "curso",
                "titulo": "Bajo progreso",
                "mensaje": str(bajo) + " inscrito(s) tienen progreso menor a 50%.",
                "link_endpoint": "ponente_seguimiento",
                "link_text": "Ver seguimiento",
                "relacion_tipo": "seguimiento",
                "relacion_id": None,
                "leido": 0,
                "creado_en": "",
            })

        pagos = int(resumen_seguimiento.get("pagos_pendientes") or 0)
        if pagos:
            avisos.append({
                "tipo": "cuota",
                "titulo": "Pagos pendientes",
                "mensaje": str(pagos) + " inscrito(s) aún figuran con pago pendiente.",
                "link_endpoint": "ponente_seguimiento",
                "link_text": "Ver inscritos",
                "relacion_tipo": "pagos",
                "relacion_id": None,
                "leido": 0,
                "creado_en": "",
            })

        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT cu.id, cu.titulo, cu.fecha_fin "
                    sql += "   FROM cursos cu "
                    sql += "  WHERE cu.ponente = %s "
                    sql += "    AND cu.estado = 'Activo' "
                    sql += "    AND cu.fecha_fin IS NOT NULL "
                    sql += "    AND cu.fecha_fin BETWEEN CURDATE() "
                    sql += "        AND DATE_ADD(CURDATE(), INTERVAL 7 DAY) "
                    sql += "  ORDER BY cu.fecha_fin ASC "
                    sql += "  LIMIT 3 "
                    cursor.execute(sql, (p_ponente,))
                    for curso in cursor.fetchall():
                        avisos.append({
                            "tipo": "curso",
                            "titulo": "Curso por finalizar",
                            "mensaje": str(curso["titulo"]) + " finaliza el " +
                                       str(curso["fecha_fin"]) + ".",
                            "link_endpoint": "ponente_curso",
                            "link_text": "Ver curso",
                            "relacion_tipo": "curso",
                            "relacion_id": curso["id"],
                            "leido": 0,
                            "creado_en": "",
                        })

        return avisos[:int(p_limite)]
    except Exception as e:
        print(repr(e))
        return avisos[:int(p_limite)]


def contar_notificaciones_ponente(p_ponente):
    return len(leer_notificaciones_ponente(p_ponente, p_limite=20))


# ============================================================
# FUNCIONES CRUD - AYUDANTES PONENTE
# ============================================================

def _columnas_presentes_crud_ponente(p_datos, p_columnas):
    datos = p_datos or {}
    return {
        columna: datos[columna]
        for columna in p_columnas
        if columna in datos and columna != "id"
    }


def _insertar_registro_crud_ponente(p_tabla, p_datos, p_columnas):
    valores = _columnas_presentes_crud_ponente(p_datos, p_columnas)
    if not valores:
        return False

    columnas_sql = ", ".join(valores.keys())
    marcas_sql = ", ".join(["%s"] * len(valores))
    sql = f"INSERT INTO {p_tabla} ({columnas_sql}) VALUES ({marcas_sql})"

    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, tuple(valores.values()))
                conn.commit()
            return True
        return False
    except Exception as e:
        print(repr(e))
        return False


def _actualizar_registro_crud_ponente(p_tabla, p_datos, p_columnas, p_id=None):
    registro_id = p_id or (p_datos or {}).get("id")
    if not registro_id:
        return False

    valores = _columnas_presentes_crud_ponente(p_datos, p_columnas)
    if not valores:
        return False

    set_sql = ", ".join([f"{columna} = %s" for columna in valores.keys()])
    sql = f"UPDATE {p_tabla} SET {set_sql} WHERE id = %s"
    parametros = list(valores.values())
    parametros.append(registro_id)

    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, tuple(parametros))
                    filas = cursor.rowcount
                conn.commit()
            return filas > 0
        return False
    except Exception as e:
        print(repr(e))
        return False


def _eliminar_registro_crud_ponente(p_tabla, p_id):
    if not p_id:
        return False

    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"DELETE FROM {p_tabla} WHERE id = %s", (p_id,))
                    filas = cursor.rowcount
                conn.commit()
            return filas > 0
        return False
    except Exception as e:
        print(repr(e))
        return False


def _leer_registro_por_id_ponente(p_tabla, p_id):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"SELECT * FROM {p_tabla} WHERE id = %s", (p_id,))
                    return cursor.fetchone()
        return None
    except Exception:
        raise


def _leer_registros_crud_ponente(p_tabla, p_orden="id DESC"):
    try:
        conn = obtenerconexion()
        result = []
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"SELECT * FROM {p_tabla} ORDER BY {p_orden}")
                    result = cursor.fetchall()
        return result
    except Exception:
        raise


# ============================================================
# FUNCIONES CRUD - CONTENIDO DEL CURSO
# ============================================================

CONTENIDO_CURSO_CRUD_COLUMNAS = [
    "curso_id", "titulo", "descripcion", "enlace", "archivo",
]


def leer_contenidos_curso_crud():
    return _leer_registros_crud_ponente("contenido_curso", "curso_id ASC, id ASC")


def leer_contenido_curso_por_id(p_id):
    return _leer_registro_por_id_ponente("contenido_curso", p_id)


def insertar_contenido_curso_crud(p_datos):
    return _insertar_registro_crud_ponente(
        "contenido_curso",
        p_datos,
        CONTENIDO_CURSO_CRUD_COLUMNAS
    )


def actualizar_contenido_curso_crud(p_datos):
    return _actualizar_registro_crud_ponente(
        "contenido_curso",
        p_datos,
        CONTENIDO_CURSO_CRUD_COLUMNAS
    )


def eliminar_contenido_curso(p_id):
    return _eliminar_registro_crud_ponente("contenido_curso", p_id)
