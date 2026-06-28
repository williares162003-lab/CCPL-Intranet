import json
import os
import re
import unicodedata
from datetime import date, datetime, timedelta
from urllib import error, request
from uuid import uuid4

from bd import obtenerconexion


# ============================================================
# MODELOS DEL COLEGIADO
# ============================================================

class clsColegiado:
    def __init__(self, p_id=None, p_nombre=None, p_matricula=None, p_documento=None,
                 p_especialidad=None, p_correo=None, p_telefono=None,
                 p_vigencia=None, p_estado=None, p_epc_points=None,
                 p_direccion=None, p_especialidad_id=None,
                 p_fecha_colegiatura=None):
        self.id = p_id
        self.nombre = p_nombre
        self.matricula = p_matricula
        self.documento = p_documento
        self.especialidad_id = p_especialidad_id
        self.especialidad = p_especialidad
        self.correo = p_correo
        self.telefono = p_telefono
        self.vigencia = p_vigencia
        self.estado = p_estado
        self.epc_points = p_epc_points
        self.direccion = p_direccion
        self.fecha_colegiatura = p_fecha_colegiatura


class clsTramite:
    def __init__(self, p_id=None, p_matricula=None, p_nombre=None,
                 p_tipo_tramite=None, p_asunto=None, p_descripcion=None,
                 p_archivo_solicitud=None, p_estado=None,
                 p_fecha_solicitud=None):
        self.id = p_id
        self.matricula = p_matricula
        self.nombre = p_nombre
        self.tipo_tramite = p_tipo_tramite
        self.asunto = p_asunto
        self.descripcion = p_descripcion
        self.archivo_solicitud = p_archivo_solicitud
        self.estado = p_estado
        self.fecha_solicitud = p_fecha_solicitud


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
                        mensaje = "DNI invalido."
                        resumen["omitidos"] += 1
                        resumen["errores"].append(f"Fila {indice}: {mensaje}")
                        _detalle_importacion(resumen, indice, matricula, documento, "Omitido", mensaje)
                        continue
                    if telefono and not re.fullmatch(r"9\d{8}", telefono):
                        mensaje = "Telefono invalido."
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
                        mensaje = "Matricula o DNI ya registrado."
                        resumen["omitidos"] += 1
                        resumen["errores"].append(f"Fila {indice}: {mensaje}")
                        _detalle_importacion(resumen, indice, matricula, documento, "Omitido", mensaje)
                        continue

                    cursor.execute(
                        "SELECT id FROM usuarios WHERE matricula = %s",
                        (matricula,)
                    )
                    if cursor.fetchone():
                        mensaje = "Ya existe un usuario con esa matricula."
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


# ============================================================
# PAGOS DEMO Y COMPROBANTES INTERNOS
# ============================================================

MONTO_CUOTA_ORDINARIA = 80.00
DESCUENTO_CUOTA_ANUAL = 10.00


def _ultimo_dia_mes(p_anio, p_mes):
    if p_mes == 12:
        siguiente = date(p_anio + 1, 1, 1)
    else:
        siguiente = date(p_anio, p_mes + 1, 1)
    return siguiente - timedelta(days=1)


def _nombre_mes(p_mes):
    meses = [
        "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    return meses[int(p_mes)] if p_mes else ""


def obtener_configuracion_cuotas_colegiado():
    hoy = date.today()
    return {
        "anio": hoy.year,
        "mes_inicio": hoy.month,
        "cantidad_meses": 3,
        "monto_mensual": MONTO_CUOTA_ORDINARIA,
        "mensaje": (
            "Puedes generar cuotas futuras para pagarlas por adelantado. "
            "Las cuotas vencidas se muestran directamente en la tabla."
        ),
    }


def obtener_configuracion_pago_anual_colegiado():
    hoy = date.today()
    habilitado = hoy.month in [1, 2, 3]
    monto_base = MONTO_CUOTA_ORDINARIA * 12
    monto_descuento = monto_base * (DESCUENTO_CUOTA_ANUAL / 100)
    return {
        "anio": hoy.year,
        "habilitado": habilitado,
        "ventana_label": "Enero a marzo " + str(hoy.year),
        "monto_mensual": MONTO_CUOTA_ORDINARIA,
        "descuento": DESCUENTO_CUOTA_ANUAL,
        "monto_total": monto_base - monto_descuento,
        "mensaje": (
            "Disponible para pago anual con descuento."
            if habilitado else
            "El pago anual con descuento se habilita automaticamente de enero a marzo."
        ),
    }


def generar_cuotas_adelantadas_colegiado(p_matricula, p_anio, p_mes_inicio,
                                         p_cantidad_meses):
    try:
        try:
            anio = int(p_anio)
            mes_inicio = int(p_mes_inicio)
            cantidad_meses = int(p_cantidad_meses)
        except ValueError:
            return {
                "ok": False,
                "mensaje": "Ingrese un anio, mes y cantidad validos."
            }

        hoy = date.today()
        if mes_inicio < 1 or mes_inicio > 12:
            return {"ok": False, "mensaje": "Seleccione un mes inicial valido."}
        if cantidad_meses < 1 or cantidad_meses > 12:
            return {
                "ok": False,
                "mensaje": "La cantidad de meses debe estar entre 1 y 12."
            }
        if mes_inicio + cantidad_meses - 1 > 12:
            return {
                "ok": False,
                "mensaje": "El rango de meses no puede pasar de diciembre."
            }
        if anio < hoy.year or (anio == hoy.year and mes_inicio < hoy.month):
            return {
                "ok": False,
                "mensaje": "Para periodos vencidos usa las cuotas pendientes ya generadas."
            }

        conn = obtenerconexion()
        generadas = 0
        existentes = 0
        ya_pagadas = 0
        periodos = []
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT id, matricula, nombre, estado "
                        "FROM colegiados WHERE matricula = %s",
                        (p_matricula,))
                    colegiado = cursor.fetchone()
                    if not colegiado:
                        return {
                            "ok": False,
                            "mensaje": "No se encontro el colegiado de la sesion."
                        }
                    if colegiado.get("estado") != "Vigente":
                        return {
                            "ok": False,
                            "mensaje": "Solo los colegiados vigentes pueden adelantar cuotas."
                        }

                    for mes in range(mes_inicio, mes_inicio + cantidad_meses):
                        periodo = f"{_nombre_mes(mes)} {anio}"
                        cursor.execute(
                            "SELECT id, estado FROM cuotas "
                            "WHERE colegiado_id = %s AND tipo = 'mensual' "
                            "AND periodo_anio = %s AND periodo_mes = %s",
                            (colegiado["id"], anio, mes))
                        cuota = cursor.fetchone()

                        if cuota:
                            if cuota.get("estado") == "Pagado":
                                ya_pagadas += 1
                                periodos.append(periodo + " (pagada)")
                            else:
                                existentes += 1
                                periodos.append(periodo + " (pendiente)")
                            continue

                        fecha_periodo = date(anio, mes, 1)
                        vencimiento = _ultimo_dia_mes(anio, mes)
                        concepto = "Cuota Ordinaria - " + periodo
                        sql =  "INSERT INTO cuotas "
                        sql += "(colegiado_id, fecha, fecha_emision, fecha_vencimiento, "
                        sql += " concepto, monto, estado, tipo, periodo_mes, periodo_anio) "
                        sql += "VALUES (%s, %s, %s, %s, %s, %s, 'Pendiente', 'mensual', %s, %s)"
                        cursor.execute(sql, (colegiado["id"], fecha_periodo,
                                            fecha_periodo, vencimiento,
                                            concepto, MONTO_CUOTA_ORDINARIA,
                                            mes, anio))
                        generadas += 1
                        periodos.append(periodo)
                conn.commit()

            return {
                "ok": True,
                "generadas": generadas,
                "existentes": existentes,
                "ya_pagadas": ya_pagadas,
                "periodos": periodos,
                "monto_mensual": MONTO_CUOTA_ORDINARIA,
            }
        return {"ok": False, "mensaje": "No se pudo conectar con la base de datos."}
    except Exception as e:
        print(repr(e))
        return {"ok": False, "mensaje": "No se pudieron generar las cuotas adelantadas."}


def generar_cuotas_anuales_colegiado(p_matricula, p_anio):
    try:
        hoy = date.today()
        if hoy.month not in [1, 2, 3]:
            return {
                "ok": False,
                "mensaje": "El pago anual con descuento solo se habilita de enero a marzo."
            }

        try:
            anio = int(p_anio)
        except ValueError:
            return {"ok": False, "mensaje": "Ingrese un anio valido."}

        if anio != hoy.year:
            return {
                "ok": False,
                "mensaje": "Solo se puede generar el pago anual del anio actual."
            }

        conn = obtenerconexion()
        generadas = 0
        actualizadas = 0
        monto_mensual = round(
            MONTO_CUOTA_ORDINARIA * (1 - (DESCUENTO_CUOTA_ANUAL / 100)),
            2
        )
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT id, matricula, nombre, estado "
                        "FROM colegiados WHERE matricula = %s",
                        (p_matricula,))
                    colegiado = cursor.fetchone()
                    if not colegiado:
                        return {
                            "ok": False,
                            "mensaje": "No se encontro el colegiado de la sesion."
                        }
                    if colegiado.get("estado") != "Vigente":
                        return {
                            "ok": False,
                            "mensaje": "Solo los colegiados vigentes pueden generar pago anual."
                        }

                    cursor.execute(
                        "SELECT COUNT(*) AS total FROM cuotas "
                        "WHERE colegiado_id = %s AND tipo = 'mensual' "
                        "AND periodo_anio = %s AND estado = 'Pagado'",
                        (colegiado["id"], anio))
                    pagadas = (cursor.fetchone() or {}).get("total", 0) or 0
                    if pagadas > 0:
                        return {
                            "ok": False,
                            "mensaje": (
                                "No se puede aplicar el descuento anual porque "
                                "ya existen cuotas pagadas de este anio."
                            )
                        }

                    for mes in range(1, 13):
                        fecha_periodo = date(anio, mes, 1)
                        vencimiento = _ultimo_dia_mes(anio, mes)
                        concepto = (
                            f"Cuota Ordinaria - {_nombre_mes(mes)} {anio} "
                            "(Pago anual con descuento)"
                        )
                        cursor.execute(
                            "SELECT id FROM cuotas "
                            "WHERE colegiado_id = %s AND tipo = 'mensual' "
                            "AND periodo_anio = %s AND periodo_mes = %s",
                            (colegiado["id"], anio, mes))
                        cuota = cursor.fetchone()
                        if cuota:
                            cursor.execute(
                                "UPDATE cuotas "
                                "SET fecha = %s, fecha_emision = %s, "
                                "    fecha_vencimiento = %s, concepto = %s, "
                                "    monto = %s, estado = 'Pendiente', fecha_pago = NULL "
                                "WHERE id = %s",
                                (fecha_periodo, fecha_periodo, vencimiento,
                                 concepto, monto_mensual, cuota["id"]))
                            actualizadas += 1
                        else:
                            sql =  "INSERT INTO cuotas "
                            sql += "(colegiado_id, fecha, fecha_emision, fecha_vencimiento, "
                            sql += " concepto, monto, estado, tipo, periodo_mes, periodo_anio) "
                            sql += "VALUES (%s, %s, %s, %s, %s, %s, 'Pendiente', 'mensual', %s, %s)"
                            cursor.execute(sql, (colegiado["id"], fecha_periodo,
                                                fecha_periodo, vencimiento,
                                                concepto, monto_mensual, mes,
                                                anio))
                            generadas += 1
                conn.commit()

            return {
                "ok": True,
                "anio": anio,
                "generadas": generadas,
                "actualizadas": actualizadas,
                "descuento": DESCUENTO_CUOTA_ANUAL,
                "monto_mensual": monto_mensual,
                "monto_total": monto_mensual * 12,
            }
        return {"ok": False, "mensaje": "No se pudo conectar con la base de datos."}
    except Exception as e:
        print(repr(e))
        return {"ok": False, "mensaje": "No se pudieron generar las cuotas anuales."}


def _tabla_pago_demo_no_existe(error):
    texto = str(error).lower()
    return (
        "transacciones_pago" in texto
        or "comprobantes_pago" in texto
        or "doesn't exist" in texto
        or "no existe" in texto
    )


def leer_cuota_pago_demo(p_cuota_id, p_matricula):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT q.id, q.colegiado_id, q.fecha, "
                    sql += "        q.fecha_vencimiento, q.fecha_pago, "
                    sql += "        q.concepto, q.monto, q.estado, q.tipo, "
                    sql += "        q.curso_id, q.inscripcion_id, "
                    sql += "        c.nombre, c.matricula, c.documento, c.correo "
                    sql += "   FROM cuotas q "
                    sql += "   JOIN colegiados c ON c.id = q.colegiado_id "
                    sql += "  WHERE q.id = %s AND c.matricula = %s "
                    cursor.execute(sql, (p_cuota_id, p_matricula))
                    return cursor.fetchone()
        return None
    except Exception:
        raise


def leer_comprobantes_pago_colegiado(p_matricula):
    try:
        conn = obtenerconexion()
        result = []
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT cp.id, cp.cuota_id, cp.tipo_comprobante, "
                    sql += "        cp.serie, cp.numero, cp.fecha_emision, "
                    sql += "        cp.concepto, cp.total, cp.estado, "
                    sql += "        tp.metodo, tp.codigo_transaccion "
                    sql += "   FROM comprobantes_pago cp "
                    sql += "   JOIN colegiados c ON c.id = cp.colegiado_id "
                    sql += "   JOIN transacciones_pago tp ON tp.id = cp.transaccion_id "
                    sql += "  WHERE c.matricula = %s "
                    sql += "  ORDER BY cp.fecha_emision DESC, cp.id DESC "
                    cursor.execute(sql, (p_matricula,))
                    result = cursor.fetchall()
        return result
    except Exception as e:
        if _tabla_pago_demo_no_existe(e):
            return []
        raise


def leer_comprobante_pago_colegiado(p_comprobante_id, p_matricula):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT cp.id, cp.cuota_id, cp.tipo_comprobante, "
                    sql += "        cp.serie, cp.numero, cp.fecha_emision, "
                    sql += "        cp.concepto, cp.subtotal, cp.igv, cp.total, "
                    sql += "        cp.moneda, cp.estado, cp.codigo_hash, "
                    sql += "        tp.proveedor, tp.metodo, tp.codigo_transaccion, "
                    sql += "        tp.codigo_autorizacion, tp.pagado_en, "
                    sql += "        c.nombre, c.matricula, c.documento, c.correo "
                    sql += "   FROM comprobantes_pago cp "
                    sql += "   JOIN transacciones_pago tp ON tp.id = cp.transaccion_id "
                    sql += "   JOIN colegiados c ON c.id = cp.colegiado_id "
                    sql += "  WHERE cp.id = %s AND c.matricula = %s "
                    cursor.execute(sql, (p_comprobante_id, p_matricula))
                    return cursor.fetchone()
        return None
    except Exception as e:
        if _tabla_pago_demo_no_existe(e):
            return None
        raise


def registrar_pago_demo_colegiado(p_cuota_id, p_matricula, p_metodo):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT q.id, q.colegiado_id, q.concepto, q.monto, "
                    sql += "        q.estado, q.inscripcion_id, c.matricula "
                    sql += "   FROM cuotas q "
                    sql += "   JOIN colegiados c ON c.id = q.colegiado_id "
                    sql += "  WHERE q.id = %s AND c.matricula = %s "
                    sql += "  FOR UPDATE "
                    cursor.execute(sql, (p_cuota_id, p_matricula))
                    cuota = cursor.fetchone()
                    if not cuota:
                        return {"ok": False, "mensaje": "La cuota seleccionada no existe."}
                    if cuota["estado"] != "Pendiente":
                        return {"ok": False, "mensaje": "Esta cuota ya fue pagada o no esta pendiente."}

                    cursor.execute(
                        "SELECT id, serie, numero FROM comprobantes_pago "
                        "WHERE cuota_id = %s AND estado = 'Emitido' LIMIT 1",
                        (cuota["id"],))
                    comprobante_existente = cursor.fetchone()
                    if comprobante_existente:
                        numero = (
                            str(comprobante_existente.get("serie") or "") +
                            "-" +
                            str(comprobante_existente.get("numero") or 0).zfill(8)
                        )
                        return {
                            "ok": False,
                            "mensaje": "La cuota ya tiene comprobante emitido: " + numero + ".",
                        }

                    codigo = "INT-" + uuid4().hex[:12].upper()
                    autorizacion = "AUT-" + uuid4().hex[:10].upper()
                    respuesta = (
                        "Pago aprobado por canal interno CCPL. "
                        "Registro administrativo para trazabilidad."
                    )
                    sql =  " INSERT INTO transacciones_pago "
                    sql += " (cuota_id, colegiado_id, proveedor, metodo, "
                    sql += "  codigo_transaccion, codigo_autorizacion, monto, "
                    sql += "  moneda, estado, respuesta_pasarela, pagado_en) "
                    sql += " VALUES (%s, %s, 'Pago Interno CCPL', %s, "
                    sql += "         %s, %s, %s, 'PEN', 'Aprobado', %s, NOW()) "
                    cursor.execute(sql, (cuota["id"], cuota["colegiado_id"],
                                        p_metodo, codigo, autorizacion,
                                        cuota["monto"], respuesta))
                    transaccion_id = cursor.lastrowid

                    sql =  " UPDATE cuotas "
                    sql += "    SET estado = 'Pagado', fecha_pago = CURDATE() "
                    sql += "  WHERE id = %s "
                    cursor.execute(sql, (cuota["id"],))

                    if cuota.get("inscripcion_id"):
                        sql =  " UPDATE inscripciones_curso "
                        sql += "    SET estado_pago = 'Pagado' "
                        sql += "  WHERE id = %s "
                        cursor.execute(sql, (cuota["inscripcion_id"],))

                    tipo = "Boleta Interna"
                    serie = "B001"
                    cursor.execute(
                        "SELECT COALESCE(MAX(numero), 0) + 1 AS siguiente "
                        "FROM comprobantes_pago "
                        "WHERE tipo_comprobante = %s AND serie = %s ",
                        (tipo, serie)
                    )
                    fila = cursor.fetchone() or {}
                    numero = fila.get("siguiente") or 1
                    hash_demo = uuid4().hex.upper()

                    sql =  " INSERT INTO comprobantes_pago "
                    sql += " (transaccion_id, cuota_id, colegiado_id, "
                    sql += "  tipo_comprobante, serie, numero, fecha_emision, "
                    sql += "  concepto, subtotal, igv, total, moneda, estado, "
                    sql += "  codigo_hash) "
                    sql += " VALUES (%s, %s, %s, %s, %s, %s, CURDATE(), "
                    sql += "         %s, %s, 0.00, %s, 'PEN', 'Emitido', %s) "
                    cursor.execute(sql, (transaccion_id, cuota["id"],
                                        cuota["colegiado_id"], tipo, serie,
                                        numero, cuota["concepto"],
                                        cuota["monto"], cuota["monto"],
                                        hash_demo))
                    comprobante_id = cursor.lastrowid
                conn.commit()
            return {
                "ok": True,
                "mensaje": "Pago aprobado y comprobante generado.",
                "transaccion_id": transaccion_id,
                "comprobante_id": comprobante_id,
                "codigo_transaccion": codigo,
            }
        return {"ok": False, "mensaje": "No se pudo conectar con la base de datos."}
    except Exception as e:
        print(repr(e))
        if _tabla_pago_demo_no_existe(e):
            return {
                "ok": False,
                "mensaje": (
                    "Actualice la base con database/schema.sql "
                    "para crear las tablas de pagos internos."
                ),
            }
        return {"ok": False, "mensaje": "No se pudo procesar el pago."}


def _tabla_mercado_pago_no_existe(error):
    texto = str(error).lower()
    return (
        "configuracion_mercado_pago" in texto
        or "ordenes_mercado_pago" in texto
        or "doesn't exist" in texto
        or "no existe" in texto
    )


def _mercado_pago_config(cursor=None):
    token_env = os.environ.get("MERCADOPAGO_ACCESS_TOKEN", "").strip()
    public_env = os.environ.get("MERCADOPAGO_PUBLIC_KEY", "").strip()
    config = {
        "access_token": token_env,
        "public_key": public_env,
        "modo": "TEST",
        "activo": 1 if token_env else 0,
    }
    if token_env:
        return config

    if cursor:
        cursor.execute(
            "SELECT access_token, public_key, modo "
            "FROM configuracion_mercado_pago "
            "WHERE activo = 1 "
            "ORDER BY id ASC LIMIT 1"
        )
        fila = cursor.fetchone() or {}
        config["access_token"] = (fila.get("access_token") or "").strip()
        config["public_key"] = (fila.get("public_key") or "").strip()
        config["modo"] = (fila.get("modo") or "TEST").strip()
        config["activo"] = 1 if config["access_token"] else 0
    return config


def _obtener_configuracion_mercado_pago(cursor, bloquear=False):
    sql =  " SELECT id, access_token, public_key, modo, activo "
    sql += "   FROM configuracion_mercado_pago "
    sql += "  ORDER BY id ASC "
    sql += "  LIMIT 1 "
    if bloquear:
        sql += " FOR UPDATE "
    cursor.execute(sql)
    config = cursor.fetchone()
    if config:
        return config

    cursor.execute(
        "INSERT INTO configuracion_mercado_pago "
        "(access_token, public_key, modo, activo) "
        "VALUES (NULL, NULL, 'TEST', 1)"
    )
    cursor.execute(
        "SELECT id, access_token, public_key, modo, activo "
        "FROM configuracion_mercado_pago WHERE id = %s",
        (cursor.lastrowid,))
    return cursor.fetchone()


def obtener_configuracion_mercado_pago():
    try:
        token_env = os.environ.get("MERCADOPAGO_ACCESS_TOKEN", "").strip()
        public_env = os.environ.get("MERCADOPAGO_PUBLIC_KEY", "").strip()

        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    config = _obtener_configuracion_mercado_pago(cursor)
                    token_bd = (config.get("access_token") or "").strip()
                    public_bd = (config.get("public_key") or "").strip()
                    modo = (config.get("modo") or "TEST").strip().upper()
                    activo = int(config.get("activo") or 0)
                    token_configurado = bool(token_env or token_bd)
                    public_key_configurada = bool(public_env or public_bd)
                    config["modo"] = modo
                    config["activo"] = activo
                    config["access_token_configurado"] = token_configurado
                    config["public_key_configurada"] = public_key_configurada
                    config["habilitado"] = bool(activo and token_configurado)
                    config["origen_token"] = (
                        "Variable de entorno" if token_env
                        else "Base de datos" if token_bd
                        else "Sin configurar"
                    )
                    return config
        return None
    except Exception as e:
        if _tabla_mercado_pago_no_existe(e):
            return None
        raise


def actualizar_configuracion_mercado_pago(datos):
    try:
        modo = (datos.get("modo") or "TEST").strip().upper()
        if modo == "PROD":
            modo = "PRODUCCION"
        if modo not in ["TEST", "PRODUCCION"]:
            return {"ok": False, "mensaje": "Seleccione un modo valido para Mercado Pago."}

        activo = 1 if str(datos.get("activo") or "0") == "1" else 0
        access_token = (datos.get("access_token") or "").strip()
        public_key = (datos.get("public_key") or "").strip()
        token_env = os.environ.get("MERCADOPAGO_ACCESS_TOKEN", "").strip()

        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    config = _obtener_configuracion_mercado_pago(cursor, bloquear=True)
                    if not access_token:
                        access_token = (config.get("access_token") or "").strip()
                    if not public_key:
                        public_key = (config.get("public_key") or "").strip()

                    if activo and not (access_token or token_env):
                        return {
                            "ok": False,
                            "mensaje": "Ingrese el Access Token de Mercado Pago o configure la variable de entorno.",
                        }

                    sql =  " UPDATE configuracion_mercado_pago "
                    sql += "    SET access_token = %s, public_key = %s, "
                    sql += "        modo = %s, activo = %s "
                    sql += "  WHERE id = %s "
                    cursor.execute(sql, (
                        access_token or None,
                        public_key or None,
                        modo,
                        activo,
                        config["id"],
                    ))
                conn.commit()
            return {
                "ok": True,
                "mensaje": "Configuracion de Mercado Pago actualizada.",
            }
        return {"ok": False, "mensaje": "No se pudo conectar con la base de datos."}
    except Exception as e:
        print(repr(e))
        if _tabla_mercado_pago_no_existe(e):
            return {
                "ok": False,
                "mensaje": "Actualice la base con database/alter_mercado_pago.sql.",
            }
        return {"ok": False, "mensaje": "No se pudo guardar la configuracion de Mercado Pago."}


def _mercado_pago_base_local(base_url):
    base = str(base_url or "").lower()
    return (
        "localhost" in base
        or "127.0.0.1" in base
        or base.startswith("http://192.168.")
        or base.startswith("http://10.")
    )


def _mercado_pago_request(method, path, token, payload=None):
    url = "https://api.mercadopago.com" + path
    headers = {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json",
    }
    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")

    req = request.Request(url, data=body, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=20) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            detalle = json.loads(raw)
        except ValueError:
            detalle = {"message": raw}
        return {
            "error": True,
            "status": e.code,
            "message": detalle.get("message") or detalle,
            "detalle": detalle,
        }


def _registrar_pago_aprobado_mercado_pago(cursor, orden, pago):
    cursor.execute(
        "SELECT id, colegiado_id, concepto, monto, estado, inscripcion_id "
        "FROM cuotas WHERE id = %s FOR UPDATE",
        (orden["cuota_id"],))
    cuota = cursor.fetchone()
    if not cuota:
        return {"ok": False, "mensaje": "No se encontro la cuota relacionada."}

    cursor.execute(
        "SELECT id, serie, numero FROM comprobantes_pago "
        "WHERE cuota_id = %s AND estado = 'Emitido' LIMIT 1",
        (cuota["id"],))
    existente = cursor.fetchone()
    if existente:
        return {
            "ok": True,
            "mensaje": "La cuota ya tenia comprobante emitido.",
            "comprobante_id": existente["id"],
        }

    payment_id = str(pago.get("id") or orden.get("mp_payment_id") or "")
    codigo = "MP-" + payment_id if payment_id else "MP-" + uuid4().hex[:12].upper()
    metodo = "Mercado Pago"
    if pago.get("payment_method_id"):
        metodo += " - " + str(pago.get("payment_method_id"))

    cursor.execute(
        "SELECT id FROM transacciones_pago "
        "WHERE codigo_transaccion = %s LIMIT 1",
        (codigo,))
    transaccion = cursor.fetchone()
    if transaccion:
        transaccion_id = transaccion["id"]
    else:
        sql =  " INSERT INTO transacciones_pago "
        sql += " (cuota_id, colegiado_id, proveedor, metodo, "
        sql += "  codigo_transaccion, codigo_autorizacion, monto, moneda, "
        sql += "  estado, respuesta_pasarela, pagado_en) "
        sql += " VALUES (%s, %s, 'Mercado Pago', %s, %s, %s, %s, 'PEN', "
        sql += "         'Aprobado', %s, NOW()) "
        cursor.execute(sql, (
            cuota["id"],
            cuota["colegiado_id"],
            metodo,
            codigo,
            str(pago.get("status_detail") or ""),
            cuota["monto"],
            json.dumps(pago, ensure_ascii=False),
        ))
        transaccion_id = cursor.lastrowid

    cursor.execute(
        "UPDATE cuotas SET estado = 'Pagado', fecha_pago = CURDATE() WHERE id = %s",
        (cuota["id"],))

    if cuota.get("inscripcion_id"):
        cursor.execute(
            "UPDATE inscripciones_curso SET estado_pago = 'Pagado' WHERE id = %s",
            (cuota["inscripcion_id"],))

    tipo = "Boleta Interna"
    serie = "B001"
    cursor.execute(
        "SELECT COALESCE(MAX(numero), 0) + 1 AS siguiente "
        "FROM comprobantes_pago "
        "WHERE tipo_comprobante = %s AND serie = %s",
        (tipo, serie))
    numero = (cursor.fetchone() or {}).get("siguiente") or 1

    sql =  " INSERT INTO comprobantes_pago "
    sql += " (transaccion_id, cuota_id, colegiado_id, tipo_comprobante, "
    sql += "  serie, numero, fecha_emision, concepto, subtotal, igv, "
    sql += "  total, moneda, estado, codigo_hash) "
    sql += " VALUES (%s, %s, %s, %s, %s, %s, CURDATE(), "
    sql += "         %s, %s, 0.00, %s, 'PEN', 'Emitido', %s) "
    cursor.execute(sql, (
        transaccion_id,
        cuota["id"],
        cuota["colegiado_id"],
        tipo,
        serie,
        numero,
        cuota["concepto"],
        cuota["monto"],
        cuota["monto"],
        uuid4().hex.upper(),
    ))
    return {
        "ok": True,
        "mensaje": "Pago Mercado Pago aprobado.",
        "comprobante_id": cursor.lastrowid,
    }


def crear_preferencia_mercado_pago(p_cuota_id, p_matricula, p_base_url):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    config = _mercado_pago_config(cursor)
                    token = config.get("access_token")
                    if not token:
                        return {
                            "ok": False,
                            "mensaje": (
                                "Falta configurar MERCADOPAGO_ACCESS_TOKEN "
                                "o la tabla configuracion_mercado_pago."
                            ),
                        }

                    cuota = leer_cuota_pago_demo(p_cuota_id, p_matricula)
                    if not cuota:
                        return {"ok": False, "mensaje": "La cuota seleccionada no pertenece al colegiado."}
                    if cuota.get("estado") != "Pendiente":
                        return {"ok": False, "mensaje": "Esta cuota no esta pendiente de pago."}

                    external_reference = "CUOTA-" + str(p_cuota_id) + "-" + uuid4().hex[:10].upper()
                    base = (p_base_url or "").rstrip("/")
                    retorno_url = base + "/pagos/mercado-pago/retorno"
                    webhook_url = base + "/pagos/mercado-pago/webhook"
                    payload = {
                        "items": [{
                            "title": cuota.get("concepto"),
                            "quantity": 1,
                            "currency_id": "PEN",
                            "unit_price": float(cuota.get("monto") or 0),
                        }],
                        "payer": {
                            "name": cuota.get("nombre"),
                            "email": cuota.get("correo") or "pagos@ccpl.test",
                        },
                        "back_urls": {
                            "success": retorno_url,
                            "failure": retorno_url,
                            "pending": retorno_url,
                        },
                        "external_reference": external_reference,
                        "metadata": {
                            "cuota_id": cuota.get("id"),
                            "matricula": p_matricula,
                        },
                    }
                    if _mercado_pago_base_local(base):
                        payload["metadata"]["ambiente_local"] = True
                    else:
                        payload["auto_return"] = "approved"
                        payload["notification_url"] = webhook_url

                    respuesta = _mercado_pago_request(
                        "POST",
                        "/checkout/preferences",
                        token,
                        payload
                    )
                    if respuesta.get("error"):
                        return {
                            "ok": False,
                            "mensaje": "Mercado Pago rechazo la preferencia: " + str(respuesta.get("message")),
                        }

                    sql =  " INSERT INTO ordenes_mercado_pago "
                    sql += " (cuota_id, colegiado_id, external_reference, "
                    sql += "  preference_id, init_point, sandbox_init_point, "
                    sql += "  estado, respuesta_preferencia) "
                    sql += " VALUES (%s, %s, %s, %s, %s, %s, 'Pendiente', %s) "
                    cursor.execute(sql, (
                        cuota["id"],
                        cuota["colegiado_id"],
                        external_reference,
                        respuesta.get("id"),
                        respuesta.get("init_point"),
                        respuesta.get("sandbox_init_point"),
                        json.dumps(respuesta, ensure_ascii=False),
                    ))
                conn.commit()

            url_pago = respuesta.get("sandbox_init_point") or respuesta.get("init_point")
            if str(config.get("modo")).upper() in ["PROD", "PRODUCCION", "PRODUCTION"]:
                url_pago = respuesta.get("init_point") or url_pago
            return {
                "ok": True,
                "mensaje": "Preferencia Mercado Pago creada.",
                "url_pago": url_pago,
                "preference_id": respuesta.get("id"),
            }
        return {"ok": False, "mensaje": "No se pudo conectar con la base de datos."}
    except Exception as e:
        print(repr(e))
        if _tabla_mercado_pago_no_existe(e):
            return {
                "ok": False,
                "mensaje": "Actualice la base con database/schema.sql para usar Mercado Pago.",
            }
        return {"ok": False, "mensaje": "No se pudo crear la preferencia de Mercado Pago."}


def confirmar_pago_mercado_pago(p_payment_id=None, p_external_reference=None):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    config = _mercado_pago_config(cursor)
                    token = config.get("access_token")
                    if not token:
                        return {"ok": False, "mensaje": "Mercado Pago no tiene token configurado."}

                    pago = {}
                    if p_payment_id:
                        pago = _mercado_pago_request(
                            "GET",
                            "/v1/payments/" + str(p_payment_id),
                            token
                        )
                        if pago.get("error"):
                            return {
                                "ok": False,
                                "mensaje": "No se pudo consultar el pago en Mercado Pago.",
                            }
                        p_external_reference = (
                            p_external_reference
                            or pago.get("external_reference")
                            or (pago.get("metadata") or {}).get("external_reference")
                        )

                    if not p_external_reference:
                        return {"ok": False, "mensaje": "No se recibio referencia externa del pago."}

                    cursor.execute(
                        "SELECT id, cuota_id, colegiado_id, estado "
                        "FROM ordenes_mercado_pago "
                        "WHERE external_reference = %s "
                        "LIMIT 1 FOR UPDATE",
                        (p_external_reference,))
                    orden = cursor.fetchone()
                    if not orden:
                        return {"ok": False, "mensaje": "No se encontro la orden Mercado Pago."}

                    estado_mp = pago.get("status") or ""
                    estado_orden = "Pendiente"
                    if estado_mp == "approved":
                        estado_orden = "Aprobado"
                    elif estado_mp in ["rejected", "cancelled", "refunded", "charged_back"]:
                        estado_orden = "Rechazado"

                    sql =  " UPDATE ordenes_mercado_pago "
                    sql += "    SET estado = %s, mp_payment_id = %s, "
                    sql += "        mp_status = %s, mp_status_detail = %s, "
                    sql += "        merchant_order_id = %s, respuesta_pago = %s "
                    sql += "  WHERE id = %s "
                    cursor.execute(sql, (
                        estado_orden,
                        str(pago.get("id") or p_payment_id or ""),
                        estado_mp,
                        str(pago.get("status_detail") or ""),
                        str(pago.get("merchant_order_id") or ""),
                        json.dumps(pago, ensure_ascii=False),
                        orden["id"],
                    ))

                    resultado = {
                        "ok": estado_orden == "Aprobado",
                        "mensaje": "El pago esta " + estado_orden + ".",
                    }
                    if estado_orden == "Aprobado":
                        resultado = _registrar_pago_aprobado_mercado_pago(
                            cursor,
                            orden,
                            pago
                        )
                conn.commit()
            return resultado
        return {"ok": False, "mensaje": "No se pudo conectar con la base de datos."}
    except Exception as e:
        print(repr(e))
        if _tabla_mercado_pago_no_existe(e):
            return {
                "ok": False,
                "mensaje": "Actualice la base con database/schema.sql para usar Mercado Pago.",
            }
        return {"ok": False, "mensaje": "No se pudo confirmar el pago Mercado Pago."}


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
# CURSOS DEL COLEGIADO
# ============================================================

def _cursos_tiene_monto_inhabil(cursor):
    cursor.execute("SHOW COLUMNS FROM cursos LIKE 'monto_inhabil'")
    return cursor.fetchone() is not None


def _curso_monto_inhabil_sql(cursor):
    if _cursos_tiene_monto_inhabil(cursor):
        return "cu.monto_inhabil"
    return "cu.monto AS monto_inhabil"


def _condicion_habilidad_colegiado(cursor, p_matricula):
    cursor.execute(
        "SELECT c.id, COUNT(q.id) AS cuotas_vencidas "
        "FROM colegiados c "
        "LEFT JOIN cuotas q ON q.colegiado_id = c.id "
        " AND q.tipo = 'mensual' "
        " AND q.estado = 'Pendiente' "
        " AND COALESCE(q.fecha_vencimiento, q.fecha) < CURDATE() "
        "WHERE c.matricula = %s "
        "GROUP BY c.id",
        (p_matricula,))
    fila = cursor.fetchone() or {}
    vencidas = int(fila.get("cuotas_vencidas") or 0)
    return {
        "condicion": "Inhabil" if vencidas >= 3 else "Habil",
        "cuotas_vencidas": vencidas,
    }


def _aplicar_precio_curso_por_condicion(p_curso, p_condicion):
    monto_habil = float(p_curso.get("monto") or 0)
    monto_inhabil = float(p_curso.get("monto_inhabil") or 0)
    precio = monto_habil
    if p_condicion == "Inhabil" and monto_inhabil > 0:
        precio = monto_inhabil
    p_curso["precio_aplicado"] = precio
    p_curso["condicion_precio"] = p_condicion
    return p_curso


def leer_cursos_colegiado(p_matricula):
    try:
        conn = obtenerconexion()
        result = None
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT i.id AS inscripcion_id, cu.id, cu.categoria, cu.titulo, cu.descripcion, "
                    sql += "        COALESCE(q.monto, cu.monto) AS monto, "
                    sql += "        cu.ponente, cu.modalidad, "
                    sql += "        cu.duracion_horas, cu.fecha_inicio, cu.fecha_fin, "
                    sql += "        cu.cupos, cu.fecha_evento, "
                    sql += "        i.progreso, i.estado_pago, "
                    sql += "        i.certificado "
                    sql += "   FROM inscripciones_curso i "
                    sql += "   JOIN cursos cu ON cu.id = i.curso_id "
                    sql += "   JOIN colegiados c ON c.id = i.colegiado_id "
                    sql += "   LEFT JOIN cuotas q ON q.inscripcion_id = i.id "
                    sql += "  WHERE c.matricula = %s "
                    sql += "  ORDER BY i.id DESC "
                    cursor.execute(sql, (p_matricula,))
                    result = cursor.fetchall()
        return result
    except Exception:
        raise


def leer_curso_inscrito_colegiado(p_inscripcion_id, p_matricula):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT i.id AS inscripcion_id, cu.id, cu.categoria, "
                    sql += "        cu.titulo, cu.descripcion, "
                    sql += "        COALESCE(q.monto, cu.monto) AS monto, "
                    sql += "        cu.ponente, "
                    sql += "        cu.modalidad, cu.duracion_horas, cu.fecha_inicio, "
                    sql += "        cu.fecha_fin, cu.cupos, "
                    sql += "        cu.fecha_evento, i.progreso, i.estado_pago, "
                    sql += "        i.certificado "
                    sql += "   FROM inscripciones_curso i "
                    sql += "   JOIN cursos cu ON cu.id = i.curso_id "
                    sql += "   JOIN colegiados c ON c.id = i.colegiado_id "
                    sql += "   LEFT JOIN cuotas q ON q.inscripcion_id = i.id "
                    sql += "  WHERE i.id = %s AND c.matricula = %s "
                    cursor.execute(sql, (p_inscripcion_id, p_matricula))
                    return cursor.fetchone()
        return None
    except Exception:
        raise


def leer_cursos_disponibles_colegiado(p_matricula):
    try:
        conn = obtenerconexion()
        result = None
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    habilidad = _condicion_habilidad_colegiado(
                        cursor, p_matricula
                    )
                    monto_inhabil_sql = _curso_monto_inhabil_sql(cursor)
                    sql =  " SELECT cu.id, cu.categoria, cu.titulo, cu.descripcion, "
                    sql += "        cu.monto, " + monto_inhabil_sql + ", "
                    sql += "        cu.ponente, cu.modalidad, cu.duracion_horas, "
                    sql += "        cu.fecha_inicio, cu.fecha_fin, cu.cupos, "
                    sql += "        cu.fecha_evento, "
                    sql += "        cu.estado, COUNT(i.id) AS inscritos "
                    sql += "   FROM cursos cu "
                    sql += "   LEFT JOIN inscripciones_curso i ON i.curso_id = cu.id "
                    sql += "  WHERE cu.estado = 'Activo' "
                    sql += "    AND NOT EXISTS ( "
                    sql += "        SELECT 1 "
                    sql += "          FROM inscripciones_curso ix "
                    sql += "          JOIN colegiados cx ON cx.id = ix.colegiado_id "
                    sql += "         WHERE ix.curso_id = cu.id AND cx.matricula = %s "
                    sql += "    ) "
                    sql += "  GROUP BY cu.id, cu.categoria, cu.titulo, cu.descripcion, "
                    sql += "           cu.monto, "
                    if _cursos_tiene_monto_inhabil(cursor):
                        sql += "           cu.monto_inhabil, "
                    sql += "           cu.ponente, cu.modalidad, cu.duracion_horas, "
                    sql += "           cu.fecha_inicio, cu.fecha_fin, cu.cupos, "
                    sql += "           cu.fecha_evento, cu.estado "
                    sql += "  ORDER BY cu.fecha_inicio ASC, cu.id DESC "
                    cursor.execute(sql, (p_matricula,))
                    result = cursor.fetchall()
                    result = [
                        _aplicar_precio_curso_por_condicion(
                            dict(curso), habilidad["condicion"]
                        )
                        for curso in result
                    ]
        return result
    except Exception:
        raise


def leer_certificado_curso_colegiado(p_inscripcion_id, p_matricula):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  " SELECT i.id AS inscripcion_id, i.progreso, "
                    sql += "        i.estado_pago, i.certificado, "
                    sql += "        c.nombre, c.matricula, c.documento, c.especialidad, "
                    sql += "        cu.titulo, cu.categoria, cu.ponente, cu.modalidad, "
                    sql += "        cu.duracion_horas, cu.fecha_evento "
                    sql += "   FROM inscripciones_curso i "
                    sql += "   JOIN colegiados c ON c.id = i.colegiado_id "
                    sql += "   JOIN cursos cu ON cu.id = i.curso_id "
                    sql += "  WHERE i.id = %s AND c.matricula = %s "
                    cursor.execute(sql, (p_inscripcion_id, p_matricula))
                    return cursor.fetchone()
        return None
    except Exception:
        raise


def finalizar_inscripcion_curso(p_id, p_matricula=None):
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql =  "SELECT i.id, i.progreso, i.estado_pago "
                    sql += "  FROM inscripciones_curso i "
                    sql += "  JOIN colegiados c ON c.id = i.colegiado_id "
                    sql += " WHERE i.id = %s "
                    params = [p_id]
                    if p_matricula:
                        sql += " AND c.matricula = %s "
                        params.append(p_matricula)
                    cursor.execute(sql, tuple(params))
                    inscripcion = cursor.fetchone()

                    if not inscripcion:
                        return "No se encontro la inscripcion del curso."
                    if inscripcion["estado_pago"] != "Pagado":
                        return "No se puede finalizar el curso porque el pago esta pendiente."
                    if inscripcion["progreso"] >= 100:
                        return "El curso ya se encuentra finalizado."

                    cursor.execute(
                        "UPDATE inscripciones_curso SET progreso = 100 WHERE id = %s",
                        (p_id,))
                conn.commit()
            return "ok"
        return "No se pudo conectar con la base de datos."
    except Exception as e:
        print(repr(e))
        return "No se pudo finalizar el curso."


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
    return TIPOS_TRAMITE.get(p_tipo, p_tipo or "Tramite")


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
                        return {"ok": False, "mensaje": "No se encontro el tramite."}

                    usuario_matricula = p_usuario_matricula or "admin"
                    usuario_nombre = p_usuario_nombre or "Administrador CCPL"
                    detalle = (p_detalle or "").strip()
                    if not detalle:
                        detalle = "Tramite actualizado a estado " + p_estado + "."

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
            return {"ok": True, "mensaje": "El estado del tramite fue actualizado."}
        return {"ok": False, "mensaje": "No se pudo conectar con la base de datos."}
    except Exception as e:
        print(repr(e))
        return {"ok": False, "mensaje": "No se pudo actualizar el tramite."}


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
