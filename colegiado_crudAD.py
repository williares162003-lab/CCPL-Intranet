import json
import os
import re
import unicodedata
from datetime import date, datetime, timedelta
from urllib import error, request
from uuid import uuid4
from bd import obtenerconexion

# ============================================================
# FUNCIONES CRUD - AYUDANTES COLEGIADO
# ============================================================

def _columnas_presentes_crud_colegiado(p_datos, p_columnas):
    datos = p_datos or {}
    return {
        columna: datos[columna]
        for columna in p_columnas
        if columna in datos and columna != "id"
    }


def _insertar_registro_crud_colegiado(p_tabla, p_datos, p_columnas):
    valores = _columnas_presentes_crud_colegiado(p_datos, p_columnas)
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


def _actualizar_registro_crud_colegiado(p_tabla, p_datos, p_columnas, p_id=None):
    registro_id = p_id or (p_datos or {}).get("id")
    if not registro_id:
        return False

    valores = _columnas_presentes_crud_colegiado(p_datos, p_columnas)
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


def _eliminar_registro_crud_colegiado(p_tabla, p_id):
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


def _leer_registro_por_id_colegiado(p_tabla, p_id):
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


def _leer_registros_crud_colegiado(p_tabla, p_orden="id DESC"):
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
