import json
import re
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4
from bd import obtenerconexion
from admin_modelosAD import clsUsuario
from admin_crudAD import _leer_registro_por_id, _eliminar_registro_crud

# ============================================================
# USUARIOS DEL SISTEMA
# ============================================================

def leer_usuarios():
    try:
        conn = obtenerconexion()
        result = None
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT u.id, u.matricula, u.password, u.rol, u.activo, "
                    sql += "        CASE "
                    sql += "          WHEN c.nombre IS NOT NULL THEN c.nombre "
                    sql += "          WHEN u.rol = 'admin' THEN 'Administrador CCPL' "
                    sql += "          ELSE u.matricula "
                    sql += "        END AS nombre "
                    sql += "   FROM usuarios u "
                    sql += "   LEFT JOIN colegiados c ON c.matricula = u.matricula "
                    sql += "  ORDER BY u.id DESC "
                    cursor.execute(sql)
                    result = cursor.fetchall()
        return result
    except Exception:
        raise


def insertar_usuario(p_usuario):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT id FROM usuarios WHERE matricula = %s",
                                   (p_usuario.matricula,))
                    if cursor.fetchone():
                        return False

                    if p_usuario.rol == "colegiado":
                        cursor.execute("SELECT id FROM colegiados WHERE matricula = %s",
                                       (p_usuario.matricula,))
                        if not cursor.fetchone():
                            return False

                    sql =  "INSERT INTO `usuarios` (`matricula`, `password`, `rol`, `activo`) "
                    sql += "VALUES (%s, %s, %s, %s)"
                    cursor.execute(sql, (p_usuario.matricula, p_usuario.password,
                                        p_usuario.rol, p_usuario.activo))
                conn.commit()
            return True
        return False
    except Exception as e:
        print(repr(e))
        return False


def actualizar_usuario(p_usuario):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    if p_usuario.rol == "colegiado":
                        cursor.execute("SELECT matricula FROM usuarios WHERE id = %s",
                                       (p_usuario.id,))
                        usuario_actual = cursor.fetchone()
                        if not usuario_actual:
                            return False
                        cursor.execute("SELECT id FROM colegiados WHERE matricula = %s",
                                       (usuario_actual["matricula"],))
                        if not cursor.fetchone():
                            return False

                    if p_usuario.password:
                        sql =  "UPDATE `usuarios` "
                        sql += "   SET `password` = %s, `rol` = %s, `activo` = %s "
                        sql += " WHERE `id` = %s "
                        cursor.execute(sql, (p_usuario.password, p_usuario.rol,
                                            p_usuario.activo, p_usuario.id))
                    else:
                        sql =  "UPDATE `usuarios` "
                        sql += "   SET `rol` = %s, `activo` = %s "
                        sql += " WHERE `id` = %s "
                        cursor.execute(sql, (p_usuario.rol, p_usuario.activo,
                                            p_usuario.id))
                conn.commit()
            return True
        return False
    except Exception as e:
        print(repr(e))
        return False

# ============================================================
# FUNCIONES CRUD - USUARIOS
# ============================================================

def leer_usuario_por_id(p_id):
    return _leer_registro_por_id("usuarios", p_id)


def eliminar_usuario(p_id):
    return _eliminar_registro_crud("usuarios", p_id)
