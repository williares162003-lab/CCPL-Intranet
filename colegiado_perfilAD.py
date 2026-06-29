import json
import os
import re
import unicodedata
from datetime import date, datetime, timedelta
from urllib import error, request
from uuid import uuid4
from bd import obtenerconexion
from colegiado_modelosAD import clsColegiado
from colegiado_crudAD import (_leer_registro_por_id_colegiado, _insertar_registro_crud_colegiado, _actualizar_registro_crud_colegiado, _eliminar_registro_crud_colegiado)

# ============================================================
# COLEGIADOS - CRUD Y BUSQUEDA
# ============================================================

def _colegiados_tiene_direccion(cursor):
    cursor.execute("SHOW COLUMNS FROM colegiados LIKE 'direccion'")
    return cursor.fetchone() is not None


def _colegiados_tiene_especialidad_id(cursor):
    cursor.execute("SHOW COLUMNS FROM colegiados LIKE 'especialidad_id'")
    return cursor.fetchone() is not None


def _colegiados_tiene_fecha_colegiatura(cursor):
    cursor.execute("SHOW COLUMNS FROM colegiados LIKE 'fecha_colegiatura'")
    return cursor.fetchone() is not None


def _tabla_especialidades_existe(cursor):
    cursor.execute("SHOW TABLES LIKE 'especialidades_colegiado'")
    return cursor.fetchone() is not None


def _especialidad_por_id(cursor, p_especialidad_id):
    if not p_especialidad_id:
        return None
    try:
        especialidad_id = int(p_especialidad_id)
    except (TypeError, ValueError):
        return None

    cursor.execute(
        "SELECT id, nombre FROM especialidades_colegiado "
        "WHERE id = %s AND activo = 1",
        (especialidad_id,)
    )
    return cursor.fetchone()


def _filtros_colegiados(p_busqueda=None, p_especialidad=None, p_estado=None,
                        p_incluir_direccion=False,
                        p_usar_especialidad_id=False,
                        p_reconocimiento_30=False,
                        p_tiene_fecha_colegiatura=False):
    filtros = []
    params = []

    busqueda = (p_busqueda or "").strip()
    if busqueda:
        campos = [
            "nombre LIKE %s",
            "matricula LIKE %s",
            "documento LIKE %s",
            "c.especialidad LIKE %s",
            "correo LIKE %s",
        ]
        campos[0] = "c.nombre LIKE %s"
        campos[1] = "c.matricula LIKE %s"
        campos[2] = "c.documento LIKE %s"
        campos[4] = "c.correo LIKE %s"
        if p_usar_especialidad_id:
            campos[3] = "(c.especialidad LIKE %s OR e.nombre LIKE %s)"
        if p_incluir_direccion:
            campos.append("c.direccion LIKE %s")
        filtros.append("(" + " OR ".join(campos) + ")")
        like = f"%{busqueda}%"
        params.extend([like, like, like])
        if p_usar_especialidad_id:
            params.extend([like, like])
        else:
            params.append(like)
        params.append(like)
        if p_incluir_direccion:
            params.append(like)

    especialidad = (p_especialidad or "").strip()
    if especialidad:
        if p_usar_especialidad_id:
            filtros.append("c.especialidad_id = %s")
            params.append(especialidad)
        else:
            filtros.append("c.especialidad = %s")
            params.append(especialidad)

    estado = (p_estado or "").strip()
    if estado:
        filtros.append("c.estado = %s")
        params.append(estado)

    if p_reconocimiento_30 and p_tiene_fecha_colegiatura:
        filtros.append("c.estado = 'Vigente'")
        filtros.append("c.fecha_colegiatura IS NOT NULL")
        filtros.append(
            "DATE_ADD(c.fecha_colegiatura, INTERVAL 30 YEAR) "
            "BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 1 YEAR)"
        )

    return filtros, params


def leer_colegiados(p_busqueda=None, p_especialidad=None, p_estado=None,
                    p_reconocimiento_30=False):
    try:
        conn = obtenerconexion()
        result = None
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    tiene_direccion = _colegiados_tiene_direccion(cursor)
                    tiene_especialidad_id = (
                        _tabla_especialidades_existe(cursor)
                        and _colegiados_tiene_especialidad_id(cursor)
                    )
                    tiene_fecha_colegiatura = _colegiados_tiene_fecha_colegiatura(cursor)
                    direccion_sql = "c.direccion"
                    if not tiene_direccion:
                        direccion_sql = "'' AS direccion"
                    if tiene_fecha_colegiatura:
                        fecha_colegiatura_sql = (
                            "c.fecha_colegiatura, "
                            "TIMESTAMPDIFF(YEAR, c.fecha_colegiatura, CURDATE()) "
                            "AS anios_colegiado, "
                            "DATE_ADD(c.fecha_colegiatura, INTERVAL 30 YEAR) "
                            "AS fecha_reconocimiento_30, "
                            "DATEDIFF(DATE_ADD(c.fecha_colegiatura, INTERVAL 30 YEAR), "
                            "CURDATE()) AS dias_para_30"
                        )
                    else:
                        fecha_colegiatura_sql = (
                            "NULL AS fecha_colegiatura, NULL AS anios_colegiado, "
                            "NULL AS fecha_reconocimiento_30, NULL AS dias_para_30"
                        )

                    if tiene_especialidad_id:
                        especialidad_sql = (
                            "c.especialidad_id, "
                            "COALESCE(e.nombre, c.especialidad) AS especialidad"
                        )
                        join_sql = (
                            " LEFT JOIN especialidades_colegiado e "
                            "   ON e.id = c.especialidad_id "
                        )
                    else:
                        especialidad_sql = "NULL AS especialidad_id, c.especialidad"
                        join_sql = ""

                    sql =  " SELECT c.id, c.nombre, c.matricula, c.documento, "
                    sql += "        " + especialidad_sql + ", "
                    sql += "        c.correo, c.telefono, " + direccion_sql + ", "
                    sql += "        c.vigencia, c.estado, c.epc_points, "
                    sql += "        " + fecha_colegiatura_sql + " "
                    sql += "   FROM colegiados c "
                    sql += join_sql
                    filtros, params = _filtros_colegiados(
                        p_busqueda,
                        p_especialidad,
                        p_estado,
                        tiene_direccion,
                        tiene_especialidad_id,
                        p_reconocimiento_30,
                        tiene_fecha_colegiatura
                    )
                    if filtros:
                        sql += " WHERE " + " AND ".join(filtros)
                    sql += "  ORDER BY nombre ASC "
                    cursor.execute(sql, tuple(params))
                    result = cursor.fetchall()
        return result
    except Exception:
        raise


def leer_especialidades_colegiados():
    try:
        conn = obtenerconexion()
        result = []
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    if _tabla_especialidades_existe(cursor):
                        sql =  " SELECT id, nombre, nombre AS especialidad "
                        sql += "   FROM especialidades_colegiado "
                        sql += "  WHERE activo = 1 "
                        sql += "  ORDER BY nombre ASC "
                    else:
                        sql =  " SELECT especialidad AS id, "
                        sql += "        especialidad AS nombre, especialidad "
                        sql += "   FROM colegiados "
                        sql += "  WHERE especialidad IS NOT NULL "
                        sql += "    AND TRIM(especialidad) <> '' "
                        sql += "  GROUP BY especialidad "
                        sql += "  ORDER BY especialidad ASC "
                    cursor.execute(sql)
                    result = cursor.fetchall()
        return result
    except Exception:
        raise


def _valor_importacion(fila, *claves):
    for clave in claves:
        valor = fila.get(clave)
        if valor is not None and str(valor).strip() != "":
            return str(valor).strip()
    return ""


def _fecha_importacion(valor):
    valor = (valor or "").strip()
    if not valor:
        return None
    formatos = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]
    for formato in formatos:
        try:
            return datetime.strptime(valor, formato).date()
        except ValueError:
            continue
    return None


def _entero_importacion(valor, defecto=0):
    try:
        return int(str(valor or "").strip())
    except (TypeError, ValueError):
        return defecto


def _normalizar_texto_importacion(valor):
    texto = " ".join(str(valor or "").strip().lower().split())
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto if not unicodedata.combining(c))


def _resolver_especialidad_importacion(cursor, especialidad_id, especialidad_nombre):
    if especialidad_id:
        especialidad = _especialidad_por_id(cursor, especialidad_id)
        if especialidad:
            return especialidad

    nombre = _normalizar_texto_importacion(especialidad_nombre)
    if not nombre:
        return None

    cursor.execute("SELECT id, nombre FROM especialidades_colegiado WHERE activo = 1")
    for especialidad in cursor.fetchall() or []:
        if _normalizar_texto_importacion(especialidad.get("nombre")) == nombre:
            return especialidad
    return None


def _detalle_importacion(resumen, fila, matricula, documento, estado, observacion):
    resumen["detalles"].append({
        "fila": fila,
        "matricula": matricula or "",
        "documento": documento or "",
        "estado": estado,
        "observacion": observacion,
    })


def importar_colegiados_masivo(registros):
    resumen = {
        "total": len(registros or []),
        "insertados": 0,
        "omitidos": 0,
        "errores": [],
        "detalles": [],
    }
    if not registros:
        mensaje = "El archivo no contiene filas para importar."
        resumen["errores"].append(mensaje)
        _detalle_importacion(resumen, "", "", "", "Omitido", mensaje)
        return resumen

    try:
        conn = obtenerconexion()
        if not conn:
            mensaje = "No se pudo conectar con la base de datos."
            resumen["errores"].append(mensaje)
            _detalle_importacion(resumen, "", "", "", "Omitido", mensaje)
            return resumen

        with conn:
            with conn.cursor() as cursor:
                if not _tabla_especialidades_existe(cursor):
                    mensaje = "Debe existir la tabla de especialidades."
                    resumen["errores"].append(mensaje)
                    _detalle_importacion(resumen, "", "", "", "Omitido", mensaje)
                    return resumen

                for indice, fila in enumerate(registros, start=2):
                    nombre = _valor_importacion(fila, "nombre", "colegiado")
                    matricula = _valor_importacion(fila, "matricula").upper()
                    documento = re.sub(r"\D", "", _valor_importacion(fila, "documento", "dni"))
                    especialidad_id = _valor_importacion(fila, "especialidad_id")
                    especialidad_nombre = _valor_importacion(fila, "especialidad")
                    direccion = _valor_importacion(fila, "direccion")
                    correo = _valor_importacion(fila, "correo", "email")
                    telefono = re.sub(r"\D", "", _valor_importacion(fila, "telefono", "celular"))
                    fecha_colegiatura = _fecha_importacion(
                        _valor_importacion(fila, "fecha_colegiatura")
                    )
                    vigencia = _valor_importacion(fila, "vigencia") or "31 de Diciembre de 2025"
                    estado = _valor_importacion(fila, "estado") or "Vigente"
                    epc_points = _entero_importacion(
                        _valor_importacion(fila, "epc_points", "epc"),
                        0
                    )
                    password = _valor_importacion(fila, "password", "contrasena", "clave") or "cpc123"

                    if not all([nombre, matricula, documento, direccion, correo]) or not (especialidad_id or especialidad_nombre):
                        mensaje = "Faltan nombre, matricula, DNI, especialidad, direccion o correo."
                        resumen["omitidos"] += 1
                        resumen["errores"].append(f"Fila {indice}: {mensaje}")
                        _detalle_importacion(resumen, indice, matricula, documento, "Omitido", mensaje)
                        continue
                    if not re.fullmatch(r"\d{8}", documento):
                        mensaje = "DNI inválido."
                        resumen["omitidos"] += 1
                        resumen["errores"].append(f"Fila {indice}: {mensaje}")
                        _detalle_importacion(resumen, indice, matricula, documento, "Omitido", mensaje)
                        continue
                    if telefono and not re.fullmatch(r"9\d{8}", telefono):
                        mensaje = "Teléfono inválido."
                        resumen["omitidos"] += 1
                        resumen["errores"].append(f"Fila {indice}: {mensaje}")
                        _detalle_importacion(resumen, indice, matricula, documento, "Omitido", mensaje)
                        continue
                    if estado not in ["Vigente", "Inactivo"]:
                        estado = "Vigente"

                    especialidad = _resolver_especialidad_importacion(
                        cursor,
                        especialidad_id,
                        especialidad_nombre
                    )
                    if not especialidad:
                        mensaje = f"Especialidad no encontrada ({especialidad_nombre or especialidad_id})."
                        resumen["omitidos"] += 1
                        resumen["errores"].append(f"Fila {indice}: {mensaje}")
                        _detalle_importacion(resumen, indice, matricula, documento, "Omitido", mensaje)
                        continue

                    cursor.execute(
                        "SELECT id FROM colegiados WHERE matricula = %s OR documento = %s",
                        (matricula, documento)
                    )
                    if cursor.fetchone():
                        mensaje = "Matrícula o DNI ya registrado."
                        resumen["omitidos"] += 1
                        resumen["errores"].append(f"Fila {indice}: {mensaje}")
                        _detalle_importacion(resumen, indice, matricula, documento, "Omitido", mensaje)
                        continue

                    cursor.execute(
                        "SELECT id FROM usuarios WHERE matricula = %s",
                        (matricula,)
                    )
                    if cursor.fetchone():
                        mensaje = "Ya existe un usuario con esa matrícula."
                        resumen["omitidos"] += 1
                        resumen["errores"].append(f"Fila {indice}: {mensaje}")
                        _detalle_importacion(resumen, indice, matricula, documento, "Omitido", mensaje)
                        continue

                    sql =  "INSERT INTO colegiados "
                    sql += "(nombre, matricula, documento, especialidad_id, especialidad, "
                    sql += " correo, telefono, direccion, fecha_colegiatura, vigencia, "
                    sql += " estado, epc_points) "
                    sql += "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                    cursor.execute(sql, (
                        nombre,
                        matricula,
                        documento,
                        especialidad["id"],
                        especialidad["nombre"],
                        correo,
                        telefono,
                        direccion,
                        fecha_colegiatura,
                        vigencia,
                        estado,
                        epc_points,
                    ))
                    cursor.execute(
                        "INSERT INTO usuarios (matricula, password, rol, activo) "
                        "VALUES (%s, %s, 'colegiado', 1)",
                        (matricula, password)
                    )
                    resumen["insertados"] += 1
                    _detalle_importacion(resumen, indice, matricula, documento, "Importado", "Correcto")
            conn.commit()
        return resumen
    except Exception as e:
        print("Error importar_colegiados_masivo:", repr(e))
        mensaje = "Error general al importar colegiados: " + repr(e)
        resumen["errores"].append(mensaje)
        _detalle_importacion(resumen, "", "", "", "Omitido", mensaje)
        return resumen


def buscar_colegiados(p_busqueda, p_limite=15):
    try:
        busqueda = (p_busqueda or "").strip()
        if len(busqueda) < 2:
            return []

        limite = max(1, min(int(p_limite or 15), 30))
        conn = obtenerconexion()
        result = []
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT id, nombre, matricula, estado "
                    sql += "   FROM colegiados "
                    sql += "  WHERE nombre LIKE %s OR matricula LIKE %s "
                    sql += "  ORDER BY nombre ASC "
                    sql += "  LIMIT %s "
                    like = f"%{busqueda}%"
                    cursor.execute(sql, (like, like, limite))
                    result = cursor.fetchall()
        return result
    except Exception:
        raise


def insertar_colegiado(p_colegiado, p_password):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    tiene_direccion = _colegiados_tiene_direccion(cursor)
                    tabla_especialidades = _tabla_especialidades_existe(cursor)
                    tiene_especialidad_id = (
                        tabla_especialidades
                        and _colegiados_tiene_especialidad_id(cursor)
                    )
                    tiene_fecha_colegiatura = _colegiados_tiene_fecha_colegiatura(cursor)
                    especialidad_id = None
                    especialidad_nombre = p_colegiado.especialidad
                    if tabla_especialidades:
                        especialidad = _especialidad_por_id(
                            cursor,
                            p_colegiado.especialidad_id
                        )
                        if not especialidad:
                            return False
                        especialidad_id = especialidad["id"]
                        especialidad_nombre = especialidad["nombre"]

                    if tiene_direccion and tiene_especialidad_id:
                        sql  = "INSERT INTO `colegiados` (`nombre`, `matricula`, `documento`, "
                        sql += "  `especialidad_id`, `especialidad`, `correo`, `telefono`, `direccion`"
                        params = [p_colegiado.nombre, p_colegiado.matricula,
                                  p_colegiado.documento, especialidad_id,
                                  especialidad_nombre, p_colegiado.correo,
                                  p_colegiado.telefono, p_colegiado.direccion]
                        if tiene_fecha_colegiatura:
                            sql += ", `fecha_colegiatura`"
                            params.append(p_colegiado.fecha_colegiatura)
                        sql += ") VALUES (" + ", ".join(["%s"] * len(params)) + ")"
                        cursor.execute(sql, tuple(params))
                    elif tiene_direccion:
                        sql  = "INSERT INTO `colegiados` (`nombre`, `matricula`, `documento`, "
                        sql += "  `especialidad`, `correo`, `telefono`, `direccion`"
                        params = [p_colegiado.nombre, p_colegiado.matricula,
                                  p_colegiado.documento, especialidad_nombre,
                                  p_colegiado.correo, p_colegiado.telefono,
                                  p_colegiado.direccion]
                        if tiene_fecha_colegiatura:
                            sql += ", `fecha_colegiatura`"
                            params.append(p_colegiado.fecha_colegiatura)
                        sql += ") VALUES (" + ", ".join(["%s"] * len(params)) + ")"
                        cursor.execute(sql, tuple(params))
                    else:
                        sql  = "INSERT INTO `colegiados` (`nombre`, `matricula`, `documento`, "
                        sql += "  `especialidad`, `correo`, `telefono`"
                        params = [p_colegiado.nombre, p_colegiado.matricula,
                                  p_colegiado.documento, especialidad_nombre,
                                  p_colegiado.correo, p_colegiado.telefono]
                        if tiene_fecha_colegiatura:
                            sql += ", `fecha_colegiatura`"
                            params.append(p_colegiado.fecha_colegiatura)
                        sql += ") VALUES (" + ", ".join(["%s"] * len(params)) + ")"
                        cursor.execute(sql, tuple(params))
                    sql2  = "INSERT INTO `usuarios` (`matricula`, `password`, `rol`) "
                    sql2 += "VALUES (%s, %s, 'colegiado')"
                    cursor.execute(sql2, (p_colegiado.matricula, p_password))
                conn.commit()
            return True
        return False
    except Exception as e:
        print(repr(e))
        return False


def actualizar_colegiado(p_colegiado):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    tiene_direccion = _colegiados_tiene_direccion(cursor)
                    tabla_especialidades = _tabla_especialidades_existe(cursor)
                    tiene_especialidad_id = (
                        tabla_especialidades
                        and _colegiados_tiene_especialidad_id(cursor)
                    )
                    tiene_fecha_colegiatura = _colegiados_tiene_fecha_colegiatura(cursor)
                    especialidad_id = None
                    especialidad_nombre = p_colegiado.especialidad
                    if tabla_especialidades:
                        especialidad = _especialidad_por_id(
                            cursor,
                            p_colegiado.especialidad_id
                        )
                        if not especialidad:
                            return False
                        especialidad_id = especialidad["id"]
                        especialidad_nombre = especialidad["nombre"]

                    if tiene_direccion and tiene_especialidad_id:
                        sql  = "UPDATE `colegiados` "
                        sql += "   SET `nombre` = %s, `especialidad_id` = %s, "
                        sql += "       `especialidad` = %s, `correo` = %s, "
                        sql += "       `telefono` = %s, `direccion` = %s, "
                        sql += "       `epc_points` = %s, `vigencia` = %s "
                        params = [p_colegiado.nombre, especialidad_id,
                                  especialidad_nombre, p_colegiado.correo,
                                  p_colegiado.telefono, p_colegiado.direccion,
                                  p_colegiado.epc_points, p_colegiado.vigencia]
                        if tiene_fecha_colegiatura:
                            sql += "     , `fecha_colegiatura` = %s "
                            params.append(p_colegiado.fecha_colegiatura)
                        sql += " WHERE `id` = %s "
                        params.append(p_colegiado.id)
                        cursor.execute(sql, tuple(params))
                    elif tiene_direccion:
                        sql  = "UPDATE `colegiados` "
                        sql += "   SET `nombre` = %s, `especialidad` = %s, `correo` = %s, "
                        sql += "       `telefono` = %s, `direccion` = %s, "
                        sql += "       `epc_points` = %s, `vigencia` = %s "
                        params = [p_colegiado.nombre, especialidad_nombre,
                                  p_colegiado.correo, p_colegiado.telefono,
                                  p_colegiado.direccion, p_colegiado.epc_points,
                                  p_colegiado.vigencia]
                        if tiene_fecha_colegiatura:
                            sql += "     , `fecha_colegiatura` = %s "
                            params.append(p_colegiado.fecha_colegiatura)
                        sql += " WHERE `id` = %s "
                        params.append(p_colegiado.id)
                        cursor.execute(sql, tuple(params))
                    else:
                        sql  = "UPDATE `colegiados` "
                        sql += "   SET `nombre` = %s, `especialidad` = %s, `correo` = %s, "
                        sql += "       `telefono` = %s, `epc_points` = %s, `vigencia` = %s "
                        params = [p_colegiado.nombre, especialidad_nombre,
                                  p_colegiado.correo, p_colegiado.telefono,
                                  p_colegiado.epc_points, p_colegiado.vigencia]
                        if tiene_fecha_colegiatura:
                            sql += "     , `fecha_colegiatura` = %s "
                            params.append(p_colegiado.fecha_colegiatura)
                        sql += " WHERE `id` = %s "
                        params.append(p_colegiado.id)
                        cursor.execute(sql, tuple(params))
                conn.commit()
            return True
        return False
    except Exception as e:
        print(repr(e))
        return False


def toggle_estado_colegiado(p_id):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql  = "UPDATE `colegiados` "
                    sql += "   SET `estado` = IF(`estado`='Vigente','Inactivo','Vigente') "
                    sql += " WHERE `id` = %s "
                    cursor.execute(sql, (p_id,))
                conn.commit()
            return True
        return False
    except Exception as e:
        print(repr(e))
        return False


def colegiado_vigente_con_deuda_pendiente(p_id):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT c.id "
                    sql += "   FROM colegiados c "
                    sql += "   JOIN cuotas q ON q.colegiado_id = c.id "
                    sql += "  WHERE c.id = %s "
                    sql += "    AND c.estado = 'Vigente' "
                    sql += "    AND q.estado = 'Pendiente' "
                    sql += "  LIMIT 1 "
                    cursor.execute(sql, (p_id,))
                    return cursor.fetchone() is not None
        return False
    except Exception as e:
        print(repr(e))
        return False


def colegiado_tiene_deuda_pendiente_matricula(p_matricula):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT COUNT(*) AS total "
                    sql += "   FROM cuotas q "
                    sql += "   JOIN colegiados c ON c.id = q.colegiado_id "
                    sql += "  WHERE c.matricula = %s "
                    sql += "    AND q.estado = 'Pendiente' "
                    cursor.execute(sql, (p_matricula,))
                    fila = cursor.fetchone() or {}
                    return (fila.get("total") or 0) > 0
        return False
    except Exception as e:
        print(repr(e))
        return False


def leer_colegiado_por_matricula(p_matricula):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    tiene_direccion = _colegiados_tiene_direccion(cursor)
                    tiene_especialidad_id = (
                        _tabla_especialidades_existe(cursor)
                        and _colegiados_tiene_especialidad_id(cursor)
                    )
                    tiene_fecha_colegiatura = _colegiados_tiene_fecha_colegiatura(cursor)
                    direccion_sql = "c.direccion"
                    if not tiene_direccion:
                        direccion_sql = "'' AS direccion"
                    if tiene_fecha_colegiatura:
                        fecha_sql = "c.fecha_colegiatura"
                    else:
                        fecha_sql = "NULL AS fecha_colegiatura"

                    if tiene_especialidad_id:
                        especialidad_sql = (
                            "c.especialidad_id, "
                            "COALESCE(e.nombre, c.especialidad) AS especialidad"
                        )
                        join_sql = (
                            " LEFT JOIN especialidades_colegiado e "
                            "   ON e.id = c.especialidad_id "
                        )
                    else:
                        especialidad_sql = "NULL AS especialidad_id, c.especialidad"
                        join_sql = ""

                    sql  = " SELECT c.id, c.nombre, c.matricula, c.documento, "
                    sql += "        " + especialidad_sql + ", "
                    sql += "        c.correo, c.telefono, " + direccion_sql + ", "
                    sql += "        c.vigencia, c.estado, c.epc_points, "
                    sql += "        " + fecha_sql + " "
                    sql += "   FROM colegiados c "
                    sql += join_sql
                    sql += "  WHERE c.matricula = %s "
                    cursor.execute(sql, (p_matricula,))
                    return cursor.fetchone()
        return None
    except Exception:
        return None


def actualizar_perfil_colegiado(p_matricula, p_correo, p_telefono, p_especialidad):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql  = "UPDATE colegiados SET correo = %s, telefono = %s, "
                    sql += "  especialidad = %s WHERE matricula = %s "
                    cursor.execute(sql, (p_correo, p_telefono, p_especialidad, p_matricula))
                conn.commit()
            return True
        return False
    except Exception as e:
        print(repr(e))
        return False

# ============================================================
# FUNCIONES CRUD - ESPECIALIDADES DEL COLEGIADO
# ============================================================

ESPECIALIDAD_COLEGIADO_CRUD_COLUMNAS = [
    "nombre", "activo",
]


def leer_especialidad_colegiado_por_id(p_id):
    return _leer_registro_por_id_colegiado("especialidades_colegiado", p_id)


def insertar_especialidad_colegiado_crud(p_datos):
    return _insertar_registro_crud_colegiado(
        "especialidades_colegiado",
        p_datos,
        ESPECIALIDAD_COLEGIADO_CRUD_COLUMNAS
    )


def actualizar_especialidad_colegiado_crud(p_datos):
    return _actualizar_registro_crud_colegiado(
        "especialidades_colegiado",
        p_datos,
        ESPECIALIDAD_COLEGIADO_CRUD_COLUMNAS
    )


def eliminar_especialidad_colegiado(p_id):
    return _eliminar_registro_crud_colegiado("especialidades_colegiado", p_id)

# ============================================================
# FUNCIONES CRUD - COLEGIADOS
# ============================================================

COLEGIADO_CRUD_COLUMNAS = [
    "nombre", "matricula", "documento", "especialidad_id", "especialidad",
    "correo", "telefono", "direccion", "fecha_colegiatura", "vigencia",
    "estado", "epc_points",
]


def leer_colegiado_por_id(p_id):
    return _leer_registro_por_id_colegiado("colegiados", p_id)


def eliminar_colegiado(p_id):
    return _eliminar_registro_crud_colegiado("colegiados", p_id)
