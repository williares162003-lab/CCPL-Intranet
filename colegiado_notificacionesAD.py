import json
import os
import re
import unicodedata
from datetime import date, datetime, timedelta
from urllib import error, request
from uuid import uuid4
from bd import obtenerconexion
from colegiado_crudAD import (_leer_registro_por_id_colegiado, _leer_registros_crud_colegiado, _insertar_registro_crud_colegiado, _actualizar_registro_crud_colegiado, _eliminar_registro_crud_colegiado)

# ============================================================
# NOTIFICACIONES DEL COLEGIADO
# ============================================================

def leer_notificaciones_colegiado(p_matricula, p_solo_no_leidas=False, p_limite=None):
    try:
        conn = obtenerconexion()
        result = []
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT n.id, n.tipo, n.titulo, n.mensaje, "
                    sql += "        n.link_endpoint, n.link_url, n.link_text, "
                    sql += "        n.relacion_tipo, n.relacion_id, n.leido, "
                    sql += "        n.creado_en, n.leido_en "
                    sql += "   FROM notificaciones n "
                    sql += "   JOIN colegiados c ON c.id = n.colegiado_id "
                    sql += "  WHERE c.matricula = %s "
                    params = [p_matricula]
                    if p_solo_no_leidas:
                        sql += "    AND n.leido = 0 "
                    sql += "  ORDER BY n.leido ASC, n.creado_en DESC, n.id DESC "
                    if p_limite:
                        sql += " LIMIT %s "
                        params.append(int(p_limite))
                    cursor.execute(sql, tuple(params))
                    result = cursor.fetchall()
        return result
    except Exception:
        raise


def contar_notificaciones_no_leidas(p_matricula):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT COUNT(*) AS total "
                    sql += "   FROM notificaciones n "
                    sql += "   JOIN colegiados c ON c.id = n.colegiado_id "
                    sql += "  WHERE c.matricula = %s "
                    sql += "    AND n.leido = 0 "
                    cursor.execute(sql, (p_matricula,))
                    fila = cursor.fetchone() or {}
                    return fila.get("total", 0) or 0
        return 0
    except Exception:
        return 0


def insertar_notificacion_matricula(p_matricula, p_tipo, p_titulo, p_mensaje,
                                    p_link_endpoint=None, p_link_text=None,
                                    p_relacion_tipo=None, p_relacion_id=None,
                                    p_link_url=None):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT id FROM colegiados WHERE matricula = %s",
                        (p_matricula,))
                    colegiado = cursor.fetchone()
                    if not colegiado:
                        return False

                    sql =  " INSERT INTO notificaciones "
                    sql += " (colegiado_id, tipo, titulo, mensaje, link_endpoint, "
                    sql += "  link_url, link_text, relacion_tipo, relacion_id) "
                    sql += " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) "
                    cursor.execute(sql, (
                        colegiado["id"], p_tipo, p_titulo, p_mensaje,
                        p_link_endpoint, p_link_url, p_link_text,
                        p_relacion_tipo, p_relacion_id
                    ))
                conn.commit()
            return True
        return False
    except Exception as e:
        print(repr(e))
        return False


def marcar_notificacion_leida(p_id, p_matricula):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " UPDATE notificaciones n "
                    sql += "   JOIN colegiados c ON c.id = n.colegiado_id "
                    sql += "    SET n.leido = 1, n.leido_en = NOW() "
                    sql += "  WHERE n.id = %s "
                    sql += "    AND c.matricula = %s "
                    cursor.execute(sql, (p_id, p_matricula))
                conn.commit()
            return True
        return False
    except Exception as e:
        print(repr(e))
        return False


def eliminar_notificaciones_leidas(p_matricula):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " DELETE n "
                    sql += "   FROM notificaciones n "
                    sql += "   JOIN colegiados c ON c.id = n.colegiado_id "
                    sql += "  WHERE c.matricula = %s "
                    sql += "    AND n.leido = 1 "
                    cursor.execute(sql, (p_matricula,))
                conn.commit()
            return True
        return False
    except Exception as e:
        print(repr(e))
        return False

# ============================================================
# FUNCIONES CRUD - NOTIFICACIONES
# ============================================================

NOTIFICACION_CRUD_COLUMNAS = [
    "colegiado_id", "tipo", "titulo", "mensaje", "link_endpoint",
    "link_url", "link_text", "relacion_tipo", "relacion_id", "leido",
    "leido_en",
]


def leer_notificaciones_crud():
    return _leer_registros_crud_colegiado("notificaciones", "creado_en DESC, id DESC")


def leer_notificacion_por_id(p_id):
    return _leer_registro_por_id_colegiado("notificaciones", p_id)


def insertar_notificacion_crud(p_datos):
    return _insertar_registro_crud_colegiado(
        "notificaciones",
        p_datos,
        NOTIFICACION_CRUD_COLUMNAS
    )


def actualizar_notificacion_crud(p_datos):
    return _actualizar_registro_crud_colegiado(
        "notificaciones",
        p_datos,
        NOTIFICACION_CRUD_COLUMNAS
    )


def eliminar_notificacion(p_id):
    return _eliminar_registro_crud_colegiado("notificaciones", p_id)
