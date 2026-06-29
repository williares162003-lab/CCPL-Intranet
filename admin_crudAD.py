import json
import re
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4
from bd import obtenerconexion

# ============================================================
# FUNCIONES CRUD - AYUDANTES ADMINISTRATIVOS
# ============================================================

def _columnas_presentes_crud(p_datos, p_columnas):
    datos = p_datos or {}
    return [col for col in p_columnas if col in datos]


def _insertar_registro_crud(p_tabla, p_datos, p_columnas):
    try:
        columnas = _columnas_presentes_crud(p_datos, p_columnas)
        if not columnas:
            return False
        campos = ", ".join([f"`{col}`" for col in columnas])
        marcas = ", ".join(["%s"] * len(columnas))
        valores = [p_datos.get(col) for col in columnas]
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        f"INSERT INTO `{p_tabla}` ({campos}) VALUES ({marcas})",
                        tuple(valores)
                    )
                conn.commit()
            return True
        return False
    except Exception as e:
        print(repr(e))
        return False


def _actualizar_registro_crud(p_tabla, p_datos, p_columnas):
    try:
        datos = p_datos or {}
        registro_id = datos.get("id")
        columnas = _columnas_presentes_crud(datos, p_columnas)
        if not registro_id or not columnas:
            return False
        campos = ", ".join([f"`{col}` = %s" for col in columnas])
        valores = [datos.get(col) for col in columnas]
        valores.append(registro_id)
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        f"UPDATE `{p_tabla}` SET {campos} WHERE `id` = %s",
                        tuple(valores)
                    )
                conn.commit()
            return True
        return False
    except Exception as e:
        print(repr(e))
        return False


def _eliminar_registro_crud(p_tabla, p_id):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"DELETE FROM `{p_tabla}` WHERE `id` = %s", (p_id,))
                conn.commit()
            return True
        return False
    except Exception as e:
        print(repr(e))
        return False


def _leer_registro_por_id(p_tabla, p_id):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"SELECT * FROM `{p_tabla}` WHERE `id` = %s", (p_id,))
                    return cursor.fetchone()
        return None
    except Exception:
        raise


def _leer_registros_crud(p_tabla):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"SELECT * FROM `{p_tabla}` ORDER BY `id` DESC")
                    return cursor.fetchall()
        return []
    except Exception:
        raise
