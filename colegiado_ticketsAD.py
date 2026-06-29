import json
import os
import re
import unicodedata
from datetime import date, datetime, timedelta
from urllib import error, request
from uuid import uuid4
from bd import obtenerconexion
from colegiado_crudAD import _actualizar_registro_crud_colegiado, _eliminar_registro_crud_colegiado

# ============================================================
# TICKETS Y SOPORTE
# ============================================================

def insertar_ticket(p_matricula, p_categoria, p_asunto, p_descripcion):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql  = "INSERT INTO tickets (matricula, categoria, asunto, descripcion) "
                    sql += "VALUES (%s, %s, %s, %s)"
                    cursor.execute(sql, (p_matricula, p_categoria, p_asunto, p_descripcion))
                conn.commit()
            return True
        return False
    except Exception as e:
        print(repr(e))
        return False


def _tickets_tiene_respuesta(cursor):
    cursor.execute("SHOW COLUMNS FROM tickets LIKE 'respuesta_admin'")
    return cursor.fetchone() is not None


def leer_tickets(p_estado=None):
    try:
        conn = obtenerconexion()
        result = None
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    tiene_respuesta = _tickets_tiene_respuesta(cursor)
                    extras = " t.respuesta_admin, t.respondido_en, t.actualizado_en "
                    if not tiene_respuesta:
                        extras = " '' AS respuesta_admin, NULL AS respondido_en, t.creado_en AS actualizado_en "

                    sql =  " SELECT t.id, t.matricula, COALESCE(c.nombre, t.matricula) AS nombre, "
                    sql += "        t.categoria, t.asunto, t.descripcion, t.estado, "
                    sql += "        t.creado_en, " + extras
                    sql += "   FROM tickets t "
                    sql += "   LEFT JOIN colegiados c ON c.matricula = t.matricula "
                    params = []
                    if p_estado:
                        if p_estado == "En Revision":
                            sql += " WHERE t.estado IN ('En Revision', 'En atencion') "
                        else:
                            sql += " WHERE t.estado = %s "
                            params.append(p_estado)
                    sql += "  ORDER BY t.id DESC "
                    cursor.execute(sql, tuple(params))
                    result = cursor.fetchall()
        return result
    except Exception:
        raise


def leer_tickets_colegiado(p_matricula):
    try:
        conn = obtenerconexion()
        result = None
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    tiene_respuesta = _tickets_tiene_respuesta(cursor)
                    extras = " respuesta_admin, respondido_en, actualizado_en "
                    if not tiene_respuesta:
                        extras = " '' AS respuesta_admin, NULL AS respondido_en, creado_en AS actualizado_en "

                    sql =  " SELECT id, matricula, categoria, asunto, descripcion, "
                    sql += "        estado, creado_en, " + extras
                    sql += "   FROM tickets "
                    sql += "  WHERE matricula = %s "
                    sql += "  ORDER BY id DESC "
                    cursor.execute(sql, (p_matricula,))
                    result = cursor.fetchall()
        return result
    except Exception:
        raise


def leer_ticket_por_id(p_id):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    tiene_respuesta = _tickets_tiene_respuesta(cursor)
                    extras = " respuesta_admin, respondido_en, actualizado_en "
                    if not tiene_respuesta:
                        extras = " '' AS respuesta_admin, NULL AS respondido_en, creado_en AS actualizado_en "

                    sql =  " SELECT id, matricula, categoria, asunto, descripcion, "
                    sql += "        estado, creado_en, " + extras
                    sql += "   FROM tickets "
                    sql += "  WHERE id = %s "
                    cursor.execute(sql, (p_id,))
                    return cursor.fetchone()
        return None
    except Exception:
        return None


def actualizar_estado_ticket(p_id, p_estado, p_respuesta=None):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    tiene_respuesta = _tickets_tiene_respuesta(cursor)
                    if p_respuesta is not None:
                        if not tiene_respuesta:
                            return False
                        sql =  "UPDATE `tickets` "
                        sql += "   SET `estado` = %s, "
                        sql += "       `respuesta_admin` = %s, "
                        sql += "       `respondido_en` = NOW() "
                        sql += " WHERE `id` = %s "
                        cursor.execute(sql, (p_estado, p_respuesta, p_id))
                    else:
                        sql =  "UPDATE `tickets` "
                        sql += "   SET `estado` = %s "
                        sql += " WHERE `id` = %s "
                        cursor.execute(sql, (p_estado, p_id))
                conn.commit()
            return True
        return False
    except Exception as e:
        print(repr(e))
        return False

# ============================================================
# FUNCIONES CRUD - TICKETS
# ============================================================

TICKET_CRUD_COLUMNAS = [
    "matricula", "categoria", "asunto", "descripcion", "estado",
    "respuesta_admin",
]


def actualizar_ticket_crud(p_datos):
    return _actualizar_registro_crud_colegiado(
        "tickets",
        p_datos,
        TICKET_CRUD_COLUMNAS
    )


def eliminar_ticket(p_id):
    return _eliminar_registro_crud_colegiado("tickets", p_id)
