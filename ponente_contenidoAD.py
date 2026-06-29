from bd import obtenerconexion
from ponente_modelosAD import clsContenidoCurso
from ponente_crudAD import (_leer_registro_por_id_ponente, _leer_registros_crud_ponente, _insertar_registro_crud_ponente, _actualizar_registro_crud_ponente, _eliminar_registro_crud_ponente)

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
