import json
import os
import re
import unicodedata
from datetime import date, datetime, timedelta
from urllib import error, request
from uuid import uuid4
from bd import obtenerconexion
from colegiado_modelosAD import clsTramite
from colegiado_crudAD import _actualizar_registro_crud_colegiado, _eliminar_registro_crud_colegiado

# ============================================================
# TRAMITES DEL COLEGIADO
# ============================================================

TIPOS_TRAMITE = {
    "certificado_habilidad": "Certificado de habilidad",
    "constancia_colegiatura": "Constancia de colegiatura",
    "baja_colegiatura": "Baja de colegiatura",
    "traslado_colegio": "Traslado a otro colegio",
    "actualizacion_datos": "Actualizacion de datos",
    "otro": "Otro tramite",
}

TRAMITES_REQUIEREN_SUSTENTO = {
    "baja_colegiatura",
    "traslado_colegio",
}

TRAMITES_ACTUALIZAN_BAJA = {
    "baja_colegiatura",
    "traslado_colegio",
}


def nombre_tipo_tramite(p_tipo):
    return TIPOS_TRAMITE.get(p_tipo, p_tipo or "Trámite")


def tramite_requiere_sustento(p_tipo):
    return p_tipo in TRAMITES_REQUIEREN_SUSTENTO


def tramite_actualiza_baja(p_tipo):
    return p_tipo in TRAMITES_ACTUALIZAN_BAJA


def leer_tipos_tramite():
    return [
        {
            "codigo": codigo,
            "nombre": nombre,
            "requiere_sustento": tramite_requiere_sustento(codigo),
        }
        for codigo, nombre in TIPOS_TRAMITE.items()
    ]


def _tabla_tramites_existe(cursor):
    cursor.execute("SHOW TABLES LIKE 'tramites'")
    return cursor.fetchone() is not None


def _tramites_tiene_columna(cursor, p_columna):
    cursor.execute("SHOW COLUMNS FROM tramites LIKE %s", (p_columna,))
    return cursor.fetchone() is not None


def _agregar_nombres_tramite(items):
    for item in items or []:
        tipo = item.get("tipo_tramite")
        item["tipo_nombre"] = nombre_tipo_tramite(tipo)
        item["requiere_sustento"] = tramite_requiere_sustento(tipo)
    return items


def leer_tramites(p_estado=None, p_matricula=None, p_tipo=None):
    try:
        conn = obtenerconexion()
        result = []
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    if not _tabla_tramites_existe(cursor):
                        return []
                    firma_campos = [
                        ("estado_firma", "'No registrado' AS estado_firma"),
                        ("tipo_firma", "NULL AS tipo_firma"),
                        ("firmado_por_matricula", "NULL AS firmado_por_matricula"),
                        ("firmado_por_nombre", "NULL AS firmado_por_nombre"),
                        ("firmado_en", "NULL AS firmado_en"),
                        ("detalle_firma", "NULL AS detalle_firma"),
                    ]

                    sql =  " SELECT t.id, t.matricula, t.nombre, t.tipo_tramite, "
                    sql += "        t.asunto, t.descripcion, t.archivo_solicitud, "
                    sql += "        t.archivo_respuesta, t.estado, t.accion_revision, "
                    sql += "        t.revisado_por_matricula, t.revisado_por_nombre, "
                    sql += "        t.detalle_revision, t.revisado_en, "
                    sql += "        t.fecha_solicitud, t.fecha_respuesta, "
                    for columna, valor_defecto in firma_campos:
                        if _tramites_tiene_columna(cursor, columna):
                            sql += "        t." + columna + ", "
                        else:
                            sql += "        " + valor_defecto + ", "
                    sql += "        COALESCE(( "
                    sql += "          SELECT COUNT(*) "
                    sql += "            FROM cuotas q "
                    sql += "            JOIN colegiados c ON c.id = q.colegiado_id "
                    sql += "           WHERE c.matricula = t.matricula "
                    sql += "             AND q.estado = 'Pendiente' "
                    sql += "        ), 0) AS cuotas_pendientes, "
                    sql += "        COALESCE(( "
                    sql += "          SELECT SUM(q.monto) "
                    sql += "            FROM cuotas q "
                    sql += "            JOIN colegiados c ON c.id = q.colegiado_id "
                    sql += "           WHERE c.matricula = t.matricula "
                    sql += "             AND q.estado = 'Pendiente' "
                    sql += "        ), 0) AS deuda_pendiente "
                    sql += "   FROM tramites t "
                    condiciones = []
                    params = []
                    if p_estado:
                        condiciones.append("t.estado = %s")
                        params.append(p_estado)
                    if p_matricula:
                        condiciones.append("t.matricula = %s")
                        params.append(p_matricula)
                    if p_tipo:
                        condiciones.append("t.tipo_tramite = %s")
                        params.append(p_tipo)
                    if condiciones:
                        sql += " WHERE " + " AND ".join(condiciones)
                    sql += "  ORDER BY t.fecha_solicitud DESC, t.id DESC "
                    cursor.execute(sql, tuple(params))
                    result = cursor.fetchall()
        return _agregar_nombres_tramite(result)
    except Exception:
        raise


def leer_tramite_por_id(p_id):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    if not _tabla_tramites_existe(cursor):
                        return None
                    firma_campos = [
                        ("estado_firma", "'No registrado' AS estado_firma"),
                        ("tipo_firma", "NULL AS tipo_firma"),
                        ("firmado_por_matricula", "NULL AS firmado_por_matricula"),
                        ("firmado_por_nombre", "NULL AS firmado_por_nombre"),
                        ("firmado_en", "NULL AS firmado_en"),
                        ("detalle_firma", "NULL AS detalle_firma"),
                    ]
                    sql =  " SELECT id, matricula, nombre, tipo_tramite, asunto, "
                    sql += "        descripcion, archivo_solicitud, archivo_respuesta, "
                    sql += "        estado, accion_revision, revisado_por_matricula, "
                    sql += "        revisado_por_nombre, detalle_revision, revisado_en, "
                    sql += "        fecha_solicitud, fecha_respuesta, "
                    for columna, valor_defecto in firma_campos:
                        if _tramites_tiene_columna(cursor, columna):
                            sql += "        " + columna + ", "
                        else:
                            sql += "        " + valor_defecto + ", "
                    sql = sql.rstrip(", ")
                    sql += "   FROM tramites "
                    sql += "  WHERE id = %s "
                    cursor.execute(sql, (p_id,))
                    tramite = cursor.fetchone()
                    if tramite:
                        tipo = tramite.get("tipo_tramite")
                        tramite["tipo_nombre"] = nombre_tipo_tramite(tipo)
                        tramite["requiere_sustento"] = tramite_requiere_sustento(tipo)
                    return tramite
        return None
    except Exception:
        return None


def insertar_tramite(p_tramite):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    if not _tabla_tramites_existe(cursor):
                        return False
                    sql =  "INSERT INTO tramites "
                    sql += "(matricula, nombre, tipo_tramite, asunto, descripcion, "
                    sql += " archivo_solicitud, estado, fecha_solicitud) "
                    sql += "VALUES (%s, %s, %s, %s, %s, %s, 'Pendiente', %s)"
                    cursor.execute(sql, (
                        p_tramite.matricula,
                        p_tramite.nombre,
                        p_tramite.tipo_tramite,
                        p_tramite.asunto,
                        p_tramite.descripcion,
                        p_tramite.archivo_solicitud,
                        p_tramite.fecha_solicitud,
                    ))
                conn.commit()
            return True
        return False
    except Exception as e:
        print(repr(e))
        return False


def actualizar_estado_tramite(p_id, p_estado, p_usuario_matricula=None,
                              p_usuario_nombre=None, p_detalle=None,
                              p_archivo_respuesta=None,
                              p_tipo_firma=None, p_estado_firma=None,
                              p_detalle_firma=None):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    if not _tabla_tramites_existe(cursor):
                        return {"ok": False, "mensaje": "No existe la tabla de tramites."}
                    cursor.execute(
                        "SELECT matricula, tipo_tramite FROM tramites WHERE id = %s",
                        (p_id,))
                    tramite = cursor.fetchone()
                    if not tramite:
                        return {"ok": False, "mensaje": "No se encontró el trámite."}

                    usuario_matricula = p_usuario_matricula or "admin"
                    usuario_nombre = p_usuario_nombre or "Administrador CCPL"
                    detalle = (p_detalle or "").strip()
                    if not detalle:
                        detalle = "Trámite actualizado a estado " + p_estado + "."

                    sql =  "UPDATE tramites "
                    sql += "   SET estado = %s, accion_revision = %s, "
                    sql += "       revisado_por_matricula = %s, "
                    sql += "       revisado_por_nombre = %s, "
                    sql += "       detalle_revision = %s, revisado_en = NOW() "
                    params = [p_estado, p_estado, usuario_matricula,
                              usuario_nombre, detalle]
                    if p_archivo_respuesta:
                        sql += "     , archivo_respuesta = %s, fecha_respuesta = CURDATE() "
                        params.append(p_archivo_respuesta)
                    if (
                        p_estado == "Aprobado"
                        and tramite.get("tipo_tramite") == "certificado_habilidad"
                    ):
                        tipo_firma = (p_tipo_firma or "eDNI").strip()
                        if tipo_firma != "eDNI":
                            tipo_firma = "eDNI"
                        estado_firma = (p_estado_firma or "Firmado").strip() or "Firmado"
                        detalle_firma = (p_detalle_firma or "").strip()
                        if not detalle_firma:
                            detalle_firma = "Certificado firmado con eDNI desde el sistema."
                        if _tramites_tiene_columna(cursor, "estado_firma"):
                            sql += "     , estado_firma = %s "
                            params.append(estado_firma)
                        if _tramites_tiene_columna(cursor, "tipo_firma"):
                            sql += "     , tipo_firma = %s "
                            params.append(tipo_firma)
                        if _tramites_tiene_columna(cursor, "firmado_por_matricula"):
                            sql += "     , firmado_por_matricula = %s "
                            params.append(usuario_matricula)
                        if _tramites_tiene_columna(cursor, "firmado_por_nombre"):
                            sql += "     , firmado_por_nombre = %s "
                            params.append(usuario_nombre)
                        if _tramites_tiene_columna(cursor, "firmado_en"):
                            sql += "     , firmado_en = NOW() "
                        if _tramites_tiene_columna(cursor, "detalle_firma"):
                            sql += "     , detalle_firma = %s "
                            params.append(detalle_firma)
                    sql += " WHERE id = %s "
                    params.append(p_id)
                    cursor.execute(sql, tuple(params))

                    if (
                        p_estado == "Aprobado"
                        and tramite_actualiza_baja(tramite.get("tipo_tramite"))
                    ):
                        cursor.execute(
                            "UPDATE colegiados SET estado = 'Inactivo' WHERE matricula = %s",
                            (tramite["matricula"],))
                conn.commit()
            return {"ok": True, "mensaje": "El estado del trámite fue actualizado."}
        return {"ok": False, "mensaje": "No se pudo conectar con la base de datos."}
    except Exception as e:
        print(repr(e))
        return {"ok": False, "mensaje": "No se pudo actualizar el trámite."}

# ============================================================
# FUNCIONES CRUD - TRAMITES
# ============================================================

TRAMITE_CRUD_COLUMNAS = [
    "matricula", "nombre", "tipo_tramite", "asunto", "descripcion",
    "archivo_solicitud", "archivo_respuesta", "estado", "accion_revision",
    "revisado_por_matricula", "revisado_por_nombre", "detalle_revision",
    "fecha_solicitud", "fecha_respuesta", "estado_firma", "tipo_firma",
    "firmado_por_matricula", "firmado_por_nombre", "detalle_firma",
]


def actualizar_tramite_crud(p_datos):
    return _actualizar_registro_crud_colegiado(
        "tramites",
        p_datos,
        TRAMITE_CRUD_COLUMNAS
    )


def eliminar_tramite(p_id):
    return _eliminar_registro_crud_colegiado("tramites", p_id)
