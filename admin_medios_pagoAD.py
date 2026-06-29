import json
import re
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4
from bd import obtenerconexion
from admin_modelosAD import clsMedioPago
from admin_crudAD import (_leer_registro_por_id, _insertar_registro_crud, _actualizar_registro_crud, _eliminar_registro_crud)

# ============================================================
# MEDIOS DE PAGO
# ============================================================

def leer_medios_pago(p_solo_activos=False):
    try:
        conn = obtenerconexion()
        result = None
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT id, nombre, descripcion, numero_cuenta, "
                    sql += "        titular, activo, creado_en "
                    sql += "   FROM medios_pago "
                    params = ()
                    if p_solo_activos:
                        sql += " WHERE activo = 1 "
                    sql += "  ORDER BY activo DESC, nombre ASC "
                    cursor.execute(sql, params)
                    result = cursor.fetchall()
        return result
    except Exception:
        raise


def insertar_medio_pago(p_medio):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  "INSERT INTO medios_pago "
                    sql += "(nombre, descripcion, numero_cuenta, titular, activo) "
                    sql += "VALUES (%s, %s, %s, %s, %s)"
                    cursor.execute(sql, (p_medio.nombre, p_medio.descripcion,
                                        p_medio.numero_cuenta, p_medio.titular,
                                        p_medio.activo))
                conn.commit()
            return True
        return False
    except Exception as e:
        print(repr(e))
        return False


def actualizar_medio_pago(p_medio):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  "UPDATE medios_pago "
                    sql += "   SET nombre = %s, descripcion = %s, "
                    sql += "       numero_cuenta = %s, titular = %s, activo = %s "
                    sql += " WHERE id = %s "
                    cursor.execute(sql, (p_medio.nombre, p_medio.descripcion,
                                        p_medio.numero_cuenta, p_medio.titular,
                                        p_medio.activo, p_medio.id))
                conn.commit()
            return True
        return False
    except Exception as e:
        print(repr(e))
        return False


def eliminar_medio_pago(p_id):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM medios_pago WHERE id = %s", (p_id,))
                conn.commit()
            return True
        return False
    except Exception as e:
        print(repr(e))
        return False

# ============================================================
# EVIDENCIAS DE PAGO
# ============================================================

def _evidencias_tiene_auditoria(cursor):
    cursor.execute("SHOW COLUMNS FROM evidencias_pago LIKE 'revisado_por_matricula'")
    return cursor.fetchone() is not None


def leer_evidencias_pago(p_matricula=None, p_estado=None):
    try:
        conn = obtenerconexion()
        result = None
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    tiene_auditoria = _evidencias_tiene_auditoria(cursor)
                    auditoria_sql = (
                        "e.accion_revision, e.revisado_por_matricula, "
                        "e.revisado_por_nombre, e.detalle_revision, e.revisado_en"
                    )
                    if not tiene_auditoria:
                        auditoria_sql = (
                            "NULL AS accion_revision, NULL AS revisado_por_matricula, "
                            "NULL AS revisado_por_nombre, NULL AS detalle_revision, "
                            "NULL AS revisado_en"
                        )

                    sql =  " SELECT e.id, e.cuota_id, e.fecha_pago, e.numero_operacion, "
                    sql += "        e.monto, e.comentario, e.estado, e.creado_en, "
                    sql += "        e.archivo, " + auditoria_sql + ", "
                    sql += "        q.concepto, c.nombre, c.matricula, "
                    sql += "        mp.nombre AS medio_pago "
                    sql += "   FROM evidencias_pago e "
                    sql += "   JOIN cuotas q ON q.id = e.cuota_id "
                    sql += "   JOIN colegiados c ON c.id = e.colegiado_id "
                    sql += "   JOIN medios_pago mp ON mp.id = e.medio_pago_id "
                    condiciones = []
                    params = []
                    if p_matricula:
                        condiciones.append("c.matricula = %s")
                        params.append(p_matricula)
                    if p_estado:
                        condiciones.append("e.estado = %s")
                        params.append(p_estado)
                    if condiciones:
                        sql += " WHERE " + " AND ".join(condiciones)
                    sql += "  ORDER BY e.creado_en DESC, e.id DESC "
                    cursor.execute(sql, tuple(params))
                    result = cursor.fetchall()
        return result
    except Exception:
        raise


def registrar_evidencia_pago(p_matricula, p_cuota_id, p_medio_pago_id,
                             p_numero_operacion, p_fecha_pago, p_monto,
                             p_comentario, p_archivo=""):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT q.id, q.estado, q.monto, q.colegiado_id "
                        "FROM cuotas q "
                        "JOIN colegiados c ON c.id = q.colegiado_id "
                        "WHERE q.id = %s AND c.matricula = %s",
                        (p_cuota_id, p_matricula))
                    cuota = cursor.fetchone()
                    if not cuota:
                        return "No se encontró la cuota seleccionada."
                    if cuota["estado"] != "Pendiente":
                        return "Solo se puede registrar evidencia de cuotas pendientes."

                    cursor.execute(
                        "SELECT id FROM medios_pago WHERE id = %s AND activo = 1",
                        (p_medio_pago_id,))
                    if not cursor.fetchone():
                        return "Seleccione un medio de pago activo."

                    cursor.execute(
                        "SELECT id FROM evidencias_pago "
                        "WHERE cuota_id = %s AND estado = 'Pendiente'",
                        (p_cuota_id,))
                    if cursor.fetchone():
                        return "Ya existe una evidencia pendiente para esta cuota."

                    sql =  "INSERT INTO evidencias_pago "
                    sql += "(cuota_id, colegiado_id, medio_pago_id, fecha_pago, "
                    sql += " numero_operacion, monto, comentario, archivo, estado) "
                    sql += "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Pendiente')"
                    cursor.execute(sql, (p_cuota_id, cuota["colegiado_id"],
                                        p_medio_pago_id, p_fecha_pago,
                                        p_numero_operacion, p_monto,
                                        p_comentario, p_archivo))
                conn.commit()
            return "ok"
        return "No se pudo conectar con la base de datos."
    except Exception as e:
        print(repr(e))
        return "No se pudo registrar la evidencia de pago."


def actualizar_estado_evidencia_pago(p_id, p_estado, p_usuario_matricula=None,
                                     p_usuario_nombre=None, p_detalle=None):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    tiene_auditoria = _evidencias_tiene_auditoria(cursor)
                    cursor.execute(
                        "SELECT e.id, e.cuota_id, e.estado, e.monto AS evidencia_monto, "
                        "       q.concepto, q.colegiado_id, q.estado AS cuota_estado, "
                        "       q.monto, q.inscripcion_id, mp.nombre AS medio_pago "
                        "FROM evidencias_pago e "
                        "JOIN cuotas q ON q.id = e.cuota_id "
                        "JOIN medios_pago mp ON mp.id = e.medio_pago_id "
                        "WHERE e.id = %s",
                        (p_id,))
                    evidencia = cursor.fetchone()
                    if not evidencia:
                        return {"ok": False, "mensaje": "No se encontró la evidencia."}
                    if evidencia["estado"] != "Pendiente":
                        return {"ok": False, "mensaje": "La evidencia ya fue revisada."}
                    if p_estado == "Aprobado" and evidencia["cuota_estado"] != "Pendiente":
                        return {
                            "ok": False,
                            "mensaje": "No se puede aprobar: la cuota ya no está pendiente."
                        }

                    accion = "Aprobado" if p_estado == "Aprobado" else "Anulado"
                    detalle = p_detalle or (
                        "Comprobante aprobado por administración."
                        if p_estado == "Aprobado"
                        else "Comprobante anulado por administración."
                    )
                    usuario_matricula = p_usuario_matricula or "admin"
                    usuario_nombre = p_usuario_nombre or "Administrador CCPL"

                    if tiene_auditoria:
                        sql =  "UPDATE evidencias_pago "
                        sql += "   SET estado = %s, accion_revision = %s, "
                        sql += "       revisado_por_matricula = %s, "
                        sql += "       revisado_por_nombre = %s, "
                        sql += "       detalle_revision = %s, revisado_en = NOW() "
                        sql += " WHERE id = %s "
                        cursor.execute(sql, (p_estado, accion, usuario_matricula,
                                            usuario_nombre, detalle, p_id))
                    else:
                        cursor.execute(
                            "UPDATE evidencias_pago SET estado = %s WHERE id = %s",
                            (p_estado, p_id))

                    if p_estado == "Aprobado":
                        emision = _emitir_comprobante_desde_cuota(
                            cursor,
                            evidencia,
                            "Revision administrativa",
                            "Evidencia: " + str(evidencia.get("medio_pago") or "Pago manual"),
                            "Pago aprobado desde evidencias por " + usuario_nombre + ".",
                            p_evidencia_id=evidencia["id"]
                        )
                        if not emision.get("ok"):
                            conn.rollback()
                            return emision

                        cursor.execute(
                            "UPDATE cuotas SET estado = 'Pagado', fecha_pago = CURDATE() WHERE id = %s",
                            (evidencia["cuota_id"],))
                        if tiene_auditoria:
                            sql =  "UPDATE evidencias_pago "
                            sql += "   SET estado = 'Rechazado', "
                            sql += "       accion_revision = 'Anulado', "
                            sql += "       revisado_por_matricula = %s, "
                            sql += "       revisado_por_nombre = %s, "
                            sql += "       detalle_revision = %s, "
                            sql += "       revisado_en = NOW() "
                            sql += " WHERE cuota_id = %s AND id <> %s "
                            sql += "   AND estado = 'Pendiente' "
                            cursor.execute(sql, (
                                usuario_matricula,
                                usuario_nombre,
                                "Anulado automaticamente porque otro comprobante fue aprobado.",
                                evidencia["cuota_id"],
                                p_id
                            ))
                        else:
                            cursor.execute(
                                "UPDATE evidencias_pago "
                                "SET estado = 'Rechazado' "
                                "WHERE cuota_id = %s AND id <> %s AND estado = 'Pendiente'",
                                (evidencia["cuota_id"], p_id))

                        if evidencia["concepto"].startswith("Inscripción Curso: "):
                            titulo = evidencia["concepto"].replace("Inscripción Curso: ", "", 1)
                            sql =  "UPDATE inscripciones_curso i "
                            sql += "  JOIN cursos cu ON cu.id = i.curso_id "
                            sql += "   SET i.estado_pago = 'Pagado' "
                            sql += " WHERE i.colegiado_id = %s AND cu.titulo = %s "
                            cursor.execute(sql, (evidencia["colegiado_id"], titulo))
                conn.commit()
            return {"ok": True, "mensaje": "La evidencia fue actualizada correctamente."}
        return {"ok": False, "mensaje": "No se pudo conectar con la base de datos."}
    except Exception as e:
        print(repr(e))
        if _pagos_demo_tablas_no_existen(e):
            return {
                "ok": False,
                "mensaje": "Actualice la base con database/schema.sql para emitir comprobantes."
            }
        return {"ok": False, "mensaje": "No se pudo actualizar la evidencia."}

# ============================================================
# FUNCIONES CRUD - MEDIOS Y EVIDENCIAS DE PAGO
# ============================================================

def leer_medio_pago_por_id(p_id):
    return _leer_registro_por_id("medios_pago", p_id)


def leer_evidencia_pago_por_id(p_id):
    return _leer_registro_por_id("evidencias_pago", p_id)


def insertar_evidencia_pago_crud(p_datos):
    columnas = [
        "cuota_id", "colegiado_id", "medio_pago_id", "fecha_pago",
        "numero_operacion", "monto", "comentario", "archivo", "estado",
        "accion_revision", "revisado_por_matricula", "revisado_por_nombre",
        "detalle_revision", "revisado_en"
    ]
    return _insertar_registro_crud("evidencias_pago", p_datos, columnas)


def actualizar_evidencia_pago_crud(p_datos):
    columnas = [
        "cuota_id", "colegiado_id", "medio_pago_id", "fecha_pago",
        "numero_operacion", "monto", "comentario", "archivo", "estado",
        "accion_revision", "revisado_por_matricula", "revisado_por_nombre",
        "detalle_revision", "revisado_en"
    ]
    return _actualizar_registro_crud("evidencias_pago", p_datos, columnas)


def eliminar_evidencia_pago(p_id):
    return _eliminar_registro_crud("evidencias_pago", p_id)
