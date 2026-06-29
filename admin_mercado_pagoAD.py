import json
import re
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4
from bd import obtenerconexion
from admin_crudAD import (_leer_registro_por_id, _leer_registros_crud, _insertar_registro_crud, _actualizar_registro_crud, _eliminar_registro_crud)

# ============================================================
# FUNCIONES CRUD - MERCADO PAGO
# ============================================================

def leer_configuraciones_mercado_pago_crud():
    return _leer_registros_crud("configuracion_mercado_pago")


def leer_configuracion_mercado_pago_por_id(p_id):
    return _leer_registro_por_id("configuracion_mercado_pago", p_id)


def insertar_configuracion_mercado_pago_crud(p_datos):
    columnas = ["access_token", "public_key", "modo", "activo", "actualizado_en"]
    return _insertar_registro_crud("configuracion_mercado_pago", p_datos, columnas)


def actualizar_configuracion_mercado_pago_crud(p_datos):
    columnas = ["access_token", "public_key", "modo", "activo", "actualizado_en"]
    return _actualizar_registro_crud("configuracion_mercado_pago", p_datos, columnas)


def eliminar_configuracion_mercado_pago(p_id):
    return _eliminar_registro_crud("configuracion_mercado_pago", p_id)


def leer_ordenes_mercado_pago_crud():
    return _leer_registros_crud("ordenes_mercado_pago")


def leer_orden_mercado_pago_por_id(p_id):
    return _leer_registro_por_id("ordenes_mercado_pago", p_id)


def insertar_orden_mercado_pago_crud(p_datos):
    columnas = [
        "cuota_id", "colegiado_id", "external_reference", "preference_id",
        "init_point", "sandbox_init_point", "estado", "mp_payment_id",
        "mp_status", "mp_status_detail", "merchant_order_id",
        "respuesta_preferencia", "respuesta_pago", "actualizado_en"
    ]
    return _insertar_registro_crud("ordenes_mercado_pago", p_datos, columnas)


def actualizar_orden_mercado_pago_crud(p_datos):
    columnas = [
        "cuota_id", "colegiado_id", "external_reference", "preference_id",
        "init_point", "sandbox_init_point", "estado", "mp_payment_id",
        "mp_status", "mp_status_detail", "merchant_order_id",
        "respuesta_preferencia", "respuesta_pago", "actualizado_en"
    ]
    return _actualizar_registro_crud("ordenes_mercado_pago", p_datos, columnas)


def eliminar_orden_mercado_pago(p_id):
    return _eliminar_registro_crud("ordenes_mercado_pago", p_id)
