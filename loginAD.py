import hashlib
from bd import obtenerconexion


# ============================================================
# USUARIOS LOCALES DE RESPALDO
# ============================================================

USERS = {
    "12455-A": {"password": "cpc123",     "role": "colegiado", "nombre": "CPC. Ricardo Mendoza"},
    "admin":   {"password": "admin2024",  "role": "admin",     "nombre": "Administrador CCPL"},
    "ponente": {"password": "ponente123", "role": "ponente",   "nombre": "CPC Luis Salazar"},
    "ponente1": {"password": "ponente123", "role": "ponente",   "nombre": "CPC Luis Salazar"},
    "ponente2": {"password": "ponente123", "role": "ponente",   "nombre": "CPC Ana Rojas"},
    "ponente3": {"password": "ponente123", "role": "ponente",   "nombre": "Mg. Marco Silva"},
    "ponente4": {"password": "ponente123", "role": "ponente",   "nombre": "CPC Patricia Leon"},
    "ponente5": {"password": "ponente123", "role": "ponente",   "nombre": "CPC Rosa Medina"},
}


# ============================================================
# AUTENTICACION
# ============================================================

def autenticar_usuario(user_id: str, password: str) -> dict | None:
    try:
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql = " SELECT u.matricula, u.rol, "
                    sql += "       CASE "
                    sql += "         WHEN c.nombre IS NOT NULL THEN c.nombre "
                    sql += "         WHEN u.rol = 'admin' THEN 'Administrador CCPL' "
                    sql += "         WHEN u.rol = 'ponente' AND u.matricula IN ('ponente', 'ponente1') THEN 'CPC Luis Salazar' "
                    sql += "         WHEN u.rol = 'ponente' AND u.matricula = 'ponente2' THEN 'CPC Ana Rojas' "
                    sql += "         WHEN u.rol = 'ponente' AND u.matricula = 'ponente3' THEN 'Mg. Marco Silva' "
                    sql += "         WHEN u.rol = 'ponente' AND u.matricula = 'ponente4' THEN 'CPC Patricia Leon' "
                    sql += "         WHEN u.rol = 'ponente' AND u.matricula = 'ponente5' THEN 'CPC Rosa Medina' "
                    sql += "         ELSE u.matricula "
                    sql += "       END AS nombre "
                    sql += "  FROM usuarios u "
                    sql += "  LEFT JOIN colegiados c ON c.matricula = u.matricula "
                    sql += " WHERE u.matricula = %s AND u.password = %s AND u.activo = 1 "
                    cursor.execute(sql, (user_id, password))
                    user = cursor.fetchone()
                    if user:
                        return dict(user)
    except Exception as e:
        print(f"DB auth error: {e}")

    local = USERS.get(user_id)
    if local and local["password"] == password:
        return {"matricula": user_id, "rol": local["role"], "nombre": local["nombre"]}
    return None


# ============================================================
# RECUPERACION DE CONTRASENA POR CORREO
# ============================================================

def _hash_codigo_recuperacion(matricula, codigo):
    texto = f"{str(matricula).strip().upper()}:{str(codigo).strip()}"
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def asegurar_tabla_recuperacion_password():
    conn = obtenerconexion()
    if conn:
        with conn:
            with conn.cursor() as cursor:
                sql = """
                CREATE TABLE IF NOT EXISTS recuperacion_password (
                  id INT AUTO_INCREMENT PRIMARY KEY,
                  matricula VARCHAR(30) NOT NULL,
                  correo VARCHAR(120) NOT NULL,
                  codigo_hash VARCHAR(128) NOT NULL,
                  usado TINYINT(1) NOT NULL DEFAULT 0,
                  fecha_expiracion DATETIME NOT NULL,
                  usado_en DATETIME NULL,
                  creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  INDEX idx_recuperacion_matricula (matricula, usado, fecha_expiracion)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
                cursor.execute(sql)
            conn.commit()


def buscar_usuario_recuperacion(identificador):
    identificador = (identificador or "").strip()
    if not identificador:
        return None

    try:
        asegurar_tabla_recuperacion_password()
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    sql = """
                    SELECT u.id, u.matricula, u.rol, u.activo,
                           COALESCE(c.nombre, u.matricula) AS nombre,
                           c.correo
                      FROM usuarios u
                      LEFT JOIN colegiados c ON c.matricula = u.matricula
                     WHERE u.activo = 1
                       AND (u.matricula = %s OR c.correo = %s)
                     LIMIT 1
                    """
                    cursor.execute(sql, (identificador, identificador))
                    return cursor.fetchone()
    except Exception as e:
        print("Error buscar_usuario_recuperacion:", repr(e))
    return None


def registrar_codigo_recuperacion(matricula, correo, codigo, minutos=10):
    try:
        asegurar_tabla_recuperacion_password()
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE recuperacion_password
                           SET usado = 1, usado_en = NOW()
                         WHERE matricula = %s AND usado = 0
                        """,
                        (matricula,)
                    )
                    cursor.execute(
                        """
                        INSERT INTO recuperacion_password
                          (matricula, correo, codigo_hash, fecha_expiracion)
                        VALUES (%s, %s, %s, DATE_ADD(NOW(), INTERVAL %s MINUTE))
                        """,
                        (
                            matricula,
                            correo,
                            _hash_codigo_recuperacion(matricula, codigo),
                            int(minutos),
                        )
                    )
                conn.commit()
            return True
    except Exception as e:
        print("Error registrar_codigo_recuperacion:", repr(e))
    return False


def actualizar_password_con_codigo(matricula, codigo, nueva_password):
    try:
        asegurar_tabla_recuperacion_password()
        conn = obtenerconexion()
        if conn:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id
                          FROM recuperacion_password
                         WHERE matricula = %s
                           AND codigo_hash = %s
                           AND usado = 0
                           AND fecha_expiracion >= NOW()
                         ORDER BY id DESC
                         LIMIT 1
                        """,
                        (
                            matricula,
                            _hash_codigo_recuperacion(matricula, codigo),
                        )
                    )
                    registro = cursor.fetchone()
                    if not registro:
                        return {
                            "ok": False,
                            "mensaje": "El codigo no es valido o ya vencio."
                        }

                    cursor.execute(
                        "UPDATE usuarios SET password = %s WHERE matricula = %s",
                        (nueva_password, matricula)
                    )
                    cursor.execute(
                        """
                        UPDATE recuperacion_password
                           SET usado = 1, usado_en = NOW()
                         WHERE id = %s
                        """,
                        (registro["id"],)
                    )
                conn.commit()
            return {
                "ok": True,
                "mensaje": "Contrasena actualizada correctamente."
            }
    except Exception as e:
        print("Error actualizar_password_con_codigo:", repr(e))
    return {
        "ok": False,
        "mensaje": "No se pudo actualizar la contrasena."
    }
