import os

import pymysql.cursors


def obtenerconexion():
    try:
        connection = pymysql.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "root"),
            port=int(os.getenv("DB_PORT", "3306")),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "colegiocontadores"),
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )
        return connection
    except:
        raise
