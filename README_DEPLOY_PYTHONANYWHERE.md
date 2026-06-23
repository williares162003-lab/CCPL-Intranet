# Despliegue en PythonAnywhere

Guia corta para subir la intranet CCPL a PythonAnywhere usando GitHub.

## 1. Clonar el proyecto

En una consola Bash de PythonAnywhere:

```bash
cd ~
git clone https://github.com/williares162003-lab/CCPL-Intranet.git
cd CCPL-Intranet
```

## 2. Crear entorno virtual

```bash
mkvirtualenv --python=/usr/bin/python3.10 ccpl-env
pip install -r requirements.txt
```

Si PythonAnywhere usa otra version disponible de Python, elegir esa misma version al crear la Web App.

## 3. Crear Web App

En PythonAnywhere:

```text
Web -> Add a new web app -> Manual configuration -> Python 3.10
```

En la seccion `Virtualenv`, colocar:

```text
/home/TrabajoDAWEB/.virtualenvs/ccpl-env
```

## 4. Configurar WSGI

En la pantalla `Web`, abrir el archivo WSGI y reemplazar su contenido usando como base:

```text
pythonanywhere_wsgi.py
```

Importante: cambiar los valores que dicen `CAMBIAR_...`.

Variables principales:

```python
os.environ["FLASK_SECRET_KEY"] = "clave-larga-segura"

os.environ["DB_HOST"] = "TrabajoDAWEB.mysql.pythonanywhere-services.com"
os.environ["DB_PORT"] = "3306"
os.environ["DB_USER"] = "TrabajoDAWEB"
os.environ["DB_PASSWORD"] = "password_mysql"
os.environ["DB_NAME"] = "TrabajoDAWEB$colegiocontadores"

os.environ["CCPL_SMTP_HOST"] = "smtp.gmail.com"
os.environ["CCPL_SMTP_PORT"] = "587"
os.environ["CCPL_SMTP_USER"] = "intranet162003@gmail.com"
os.environ["CCPL_SMTP_PASSWORD"] = "clave_de_aplicacion"
os.environ["CCPL_SMTP_FROM"] = "intranet162003@gmail.com"
```

No subir claves reales a GitHub.

## 5. Static files

En `Web -> Static files`, agregar:

```text
URL:       /static/
Directory: /home/TrabajoDAWEB/CCPL-Intranet/static/
```

## 6. Base de datos MySQL

Cuando la cuenta tenga MySQL activo:

1. Crear la base de datos:

```text
colegiocontadores
```

PythonAnywhere normalmente la nombrara asi:

```text
TrabajoDAWEB$colegiocontadores
```

2. Abrir una consola MySQL o subir `database/schema.sql`.
3. Ejecutar el contenido de:

```text
database/schema.sql
```

4. Si se necesita data de prueba, ejecutar:

```text
database/reset_datos_prueba.sql
```

## 7. Recargar la app

En la pestana `Web`, presionar:

```text
Reload
```

## 8. Actualizar cambios desde GitHub

Cada vez que se suban cambios desde la PC:

```bash
cd ~/CCPL-Intranet
git pull
```

Luego presionar `Reload` en la pestana `Web`.

## Notas importantes

- La firma eDNI con lector fisico funciona en la laptop local, no directamente dentro de PythonAnywhere.
- SUNAT beta requiere certificado, clave SOL y configuracion correcta.
- Mercado Pago requiere configurar credenciales en el modulo del sistema.
- Los archivos de `static/uploads` no se suben por Git, se generan en el servidor.
