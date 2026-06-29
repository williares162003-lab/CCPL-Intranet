"""
Ejemplo de WSGI para PythonAnywhere.

Copiar este contenido en el archivo WSGI de PythonAnywhere, normalmente:
/var/www/TrabajoDAWEB_pythonanywhere_com_wsgi.py

Las claves reales no deben subirse a GitHub. Configuralas en el WSGI de
PythonAnywhere o en variables de entorno del servidor.
"""

import os
import sys

PROJECT_HOME = "/home/TrabajoDAWEB/CCPL-Intranet"

if PROJECT_HOME not in sys.path:
    sys.path.insert(0, PROJECT_HOME)

os.chdir(PROJECT_HOME)

# Configuracion Flask
os.environ["FLASK_SECRET_KEY"] = "CAMBIAR_CLAVE_SECRETA_LARGA"

# Configuracion MySQL de PythonAnywhere. Completar despues de crear la BD.
os.environ["DB_HOST"] = "TrabajoDAWEB.mysql.pythonanywhere-services.com"
os.environ["DB_PORT"] = "3306"
os.environ["DB_USER"] = "TrabajoDAWEB"
os.environ["DB_PASSWORD"] = "CAMBIAR_PASSWORD_MYSQL"
os.environ["DB_NAME"] = "TrabajoDAWEB$colegiocontadores"

# Correo del sistema para recuperar contraseña.
os.environ["CCPL_SMTP_HOST"] = "smtp.gmail.com"
os.environ["CCPL_SMTP_PORT"] = "587"
os.environ["CCPL_SMTP_USER"] = "intranet162003@gmail.com"
os.environ["CCPL_SMTP_PASSWORD"] = "CAMBIAR_CLAVE_APLICACION"
os.environ["CCPL_SMTP_FROM"] = "intranet162003@gmail.com"

from main import app as application
