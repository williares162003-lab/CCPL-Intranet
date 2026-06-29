# Portal CCPL - Firma Digital con eDNI

Proyecto web para el Colegio de Contadores Publicos de Lambayeque.  
Esta documentacion explica la parte de investigacion implementada: generacion, firma digital y validacion del Certificado de Habilidad usando DNI electronico.

## 1. Objetivo del modulo

El objetivo es que el administrador pueda emitir un Certificado de Habilidad sin subirlo manualmente. El sistema genera el PDF, lo firma con el certificado digital del DNIe y lo guarda automaticamente en el trámite.

En resumen:

1. El colegiado solicita el certificado.
2. El administrador revisa la solicitud.
3. El sistema valida que no exista deuda.
4. Se genera un PDF base.
5. Se detecta lector, DNIe y certificado digital.
6. El administrador ingresa el PIN de firma.
7. El PDF se firma digitalmente.
8. El PDF firmado se registra en el trámite.
9. El colegiado puede descargar el documento firmado.

## 2. Archivos principales

```txt
main.py
firmador_edni_local.py
iniciar_firmador_edni.bat
opensc-dnie-peru.conf
requirements.txt
templates/admin/admin_firma_edni.html
templates/admin/admin_validar_firma.html
templates/admin/certificado_habilidad_borrador.html
static/js/admin/admin_firma_edni.js
static/css/admin/admin_firma_edni.css
static/css/admin/admin_validar_firma.css
static/css/admin/certificado_habilidad.css
database/schema.sql
colegiado_tramitesAD.py
colegiado_perfilAD.py
```

## 3. Librerias usadas

El archivo `requirements.txt` contiene:

```txt
Flask==3.1.1
PyMySQL==1.2.0
Werkzeug==3.1.3
fpdf==1.7.2
requests==2.32.4
pyHanko[pkcs11]==0.35.1
```

Uso de cada libreria:

- `Flask`: crea las rutas del sistema web.
- `PyMySQL`: permite conectarse a MySQL/XAMPP.
- `Werkzeug`: se usa `secure_filename` para guardar nombres de archivos de forma segura.
- `fpdf`: genera el PDF base del certificado.
- `requests`: apoyo para integraciones HTTP del proyecto.
- `pyHanko[pkcs11]`: firma digitalmente PDFs usando certificados disponibles por PKCS#11.

## 4. Que es PKCS#11

PKCS#11 es un estandar que permite que un programa se comunique con dispositivos criptograficos, por ejemplo:

- DNI electronico.
- Token USB.
- Tarjetas inteligentes.
- Lectores de smart card.

En este proyecto, PKCS#11 permite que Python pueda acceder al certificado digital del DNIe y usarlo para firmar el PDF.

La idea es:

```txt
Python -> PKCS#11 -> Driver del DNIe -> Lector -> DNI electronico -> Certificado de firma
```

Sin PKCS#11, Python no podria leer directamente el certificado ni usar la llave privada del DNIe.

## 5. Driver usado

Driver principal:

```txt
C:\Program Files\IDEMIA\IDPlugClassic\DLLs\idplug-pkcs11.dll
```

Ese archivo DLL pertenece al driver RENIEC/IDPlug. Es el puente principal entre Python y el DNIe.

Tambien queda OpenSC como respaldo:

```txt
opensc-dnie-peru.conf
```

OpenSC sirve como configuracion auxiliar o diagnostico para tarjetas inteligentes. En la demostracion principal se usa IDPlug/RENIEC.

## 6. Donde se configura el driver

En `iniciar_firmador_edni.bat`:

```bat
set "OPENSC_CONF=%~dp0opensc-dnie-peru.conf"
set "EDNI_PKCS11_DLL=C:\Program Files\IDEMIA\IDPlugClassic\DLLs\idplug-pkcs11.dll"
python firmador_edni_local.py
```

Explicacion:

- `OPENSC_CONF`: deja lista la configuracion auxiliar de OpenSC.
- `EDNI_PKCS11_DLL`: indica que DLL usara el sistema para acceder al DNIe.
- `python firmador_edni_local.py`: inicia el modulo que verifica y firma.

## 7. Imports importantes del firmador

Archivo: `firmador_edni_local.py`

```python
import base64
import os
import re
import subprocess
import sys
import traceback
from io import BytesIO
from pathlib import Path
from flask import Flask, jsonify, request
```

Para que sirve cada uno:

- `base64`: convierte el PDF a texto para enviarlo y recibirlo por JSON.
- `os`: lee variables de entorno, por ejemplo `EDNI_PKCS11_DLL`.
- `re`: busca datos como DNI dentro del certificado.
- `subprocess`: permite consultar herramientas externas de diagnostico como OpenSC.
- `sys`: ayuda a ubicar paquetes instalados de Python.
- `traceback`: guarda errores tecnicos si falla el firmador.
- `BytesIO`: firma el PDF en memoria, sin crear archivos temporales.
- `Path`: maneja rutas de archivos.
- `Flask`: crea endpoints locales de firma.
- `jsonify`: devuelve respuestas JSON.
- `request`: recibe PDF base y PIN desde el sistema.

## 8. Imports importantes del sistema web

Archivo: `main.py`

```python
import base64
from datetime import date
from io import StringIO
from pathlib import Path
from uuid import uuid4
from flask import Flask, Response, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename
```

Uso dentro de firma:

- `base64`: recibe el PDF firmado desde el firmador.
- `date`: genera la fecha del archivo firmado.
- `StringIO`: ayuda a validar firmas sin mostrar mensajes internos.
- `Path`: ubica archivos dentro de `static/uploads`.
- `uuid4`: crea nombres unicos para PDFs firmados.
- `jsonify`: responde al JavaScript cuando firma o falla.
- `request`: recibe datos enviados desde la pantalla de firma.
- `session`: identifica al administrador que firma.
- `url_for`: arma URLs de PDF, firma y validacion.
- `secure_filename`: limpia nombres de archivo antes de guardarlos.

## 9. Donde se leen los datos del certificado

Funcion:

```txt
main.py -> _datos_certificado_habilidad(tid)
```

Esta funcion:

- Recibe el ID del trámite.
- Lee el trámite desde la base de datos.
- Verifica que el trámite sea `certificado_habilidad`.
- Valida que el colegiado no tenga deuda.
- Arma un diccionario `certificado` con los datos que iran al PDF.

Funciones de base de datos usadas:

```txt
colegiado_tramitesAD.py -> leer_tramite_por_id(p_id)
colegiado_perfilAD.py -> colegiado_tiene_deuda_pendiente_matricula(p_matricula)
```

Campos importantes que se usan:

- Nombre del colegiado.
- Matricula.
- Tipo de tramite.
- Fecha de solicitud.
- Deuda pendiente.
- Estado del trámite.

## 10. Donde se genera el PDF base

Funcion:

```txt
main.py -> _generar_pdf_certificado_habilidad(certificado)
```

Esta funcion usa `fpdf` para crear el certificado en formato PDF.

El PDF base contiene:

- Encabezado del Colegio de Contadores.
- Numero de certificado.
- Nombre del colegiado.
- Matricula.
- Texto legal de habilitacion.
- Fecha de emision.
- Cargo de la Decana.
- Vigencia del certificado.

Ruta que devuelve el PDF:

```txt
main.py -> admin_certificado_habilidad_pdf(tid)
```

Esta ruta genera el PDF y lo envia al navegador o al proceso de firma.

## 11. Donde esta la pantalla de firma

Template:

```txt
templates/admin/admin_firma_edni.html
```

Elementos importantes:

```html
data-estado-url
data-firma-url
data-pdf-url
data-guardar-url
```

Estos datos le dicen al JavaScript:

- Donde verificar el DNIe.
- Donde enviar el PDF para firmar.
- Donde obtener el PDF base.
- Donde guardar el PDF firmado.

Botones:

```html
btn-verificar-edni
btn-firmar-edni
```

- `Verificar`: revisa lector, DNIe y certificado.
- `Firmar con eDNI`: envia el PDF y el PIN al firmador.

## 12. Donde se maneja la logica del boton

Archivo:

```txt
static/js/admin/admin_firma_edni.js
```

Funciones importantes:

```txt
verificarFirmador()
firmarConEdni()
blobToBase64()
mensajeFirmaAmigable()
```

Que hace cada una:

- `verificarFirmador()`: consulta si el lector, el DNIe y el certificado estan disponibles.
- `firmarConEdni()`: obtiene el PDF base, pide firma al modulo local y guarda el PDF firmado.
- `blobToBase64()`: convierte el PDF base a base64 para enviarlo al firmador.
- `mensajeFirmaAmigable()`: convierte errores tecnicos en mensajes entendibles.

Flujo del JavaScript:

```txt
Click en Verificar
-> GET /admin/firmador-edni/estado
-> muestra si el DNIe esta listo

Click en Firmar con eDNI
-> descarga PDF base
-> convierte PDF a base64
-> envia PDF + PIN al firmador
-> recibe PDF firmado
-> guarda PDF firmado en el trámite
-> redirige a Trámites
```

## 13. Donde se detecta lector y DNIe

Funcion:

```txt
firmador_edni_local.py -> estado()
```

Esta funcion se ejecuta cuando el sistema llama:

```txt
/admin/firmador-edni/estado
```

Internamente hace:

1. Busca la libreria PKCS#11 disponible.
2. Carga la libreria del driver.
3. Busca slots o lectores.
4. Verifica si hay token o DNIe insertado.
5. Lee certificados digitales.
6. Determina si hay certificado de firma.

Funciones auxiliares:

```txt
buscar_pkcs11()
preparar_dependencias_pkcs11()
importar_pkcs11()
elegir_token_firma()
leer_certificados_token()
es_certificado_firma()
```

## 14. Donde se busca la libreria PKCS#11

Funcion:

```txt
firmador_edni_local.py -> buscar_pkcs11()
```

Lista de candidatos:

```python
PKCS11_CANDIDATOS = [
    os.environ.get("EDNI_PKCS11_DLL", ""),
    r"C:\Program Files\IDEMIA\IDPlugClassic\DLLs\idplug-pkcs11.dll",
    r"C:\Program Files (x86)\IDEMIA\IDPlugClassic\DLLs\idplug-pkcs11.dll",
    r"C:\Program Files\OpenSC Project\OpenSC\pkcs11\onepin-opensc-pkcs11.dll",
    r"C:\Program Files\OpenSC Project\OpenSC\pkcs11\opensc-pkcs11.dll",
    r"C:\Program Files (x86)\OpenSC Project\OpenSC\pkcs11\opensc-pkcs11.dll",
    r"C:\Windows\System32\opensc-pkcs11.dll",
]
```

La primera opcion es la variable de entorno `EDNI_PKCS11_DLL`, configurada en el `.bat`.  
Por eso se usa primero IDPlug/RENIEC.

## 15. Donde se leen los certificados del DNIe

Funcion:

```txt
firmador_edni_local.py -> leer_certificados_token(token)
```

Esta funcion:

- Abre una sesión con el token del DNIe.
- Busca objetos tipo certificado.
- Usa `cryptography.x509` para leer el certificado.
- Extrae datos como titular, DNI, serie, vigencia y emisor.

Tambien identifica si el certificado sirve para firma.

## 16. Donde se selecciona el certificado de firma

Funciones:

```txt
firmador_edni_local.py -> es_certificado_firma(certificado)
firmador_edni_local.py -> buscar_certificado_firma(session)
```

El DNIe puede tener mas de un certificado. Normalmente puede haber:

- Certificado de autenticacion.
- Certificado de firma.

El sistema busca el certificado de firma usando palabras como:

```txt
FIR
SIGNATURE
FIRMA
```

Esto evita usar el certificado incorrecto.

## 17. Donde se firma el PDF

Funcion principal:

```txt
firmador_edni_local.py -> firmar()
```

Esta funcion recibe:

- PDF base en base64.
- Nombre del archivo.
- PIN del DNIe.

Luego usa:

```python
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.sign import fields, signers
from pyhanko.sign.pkcs11 import PKCS11Signer, open_pkcs11_session
from pyhanko.stamp import TextStampStyle
```

Que hace cada componente:

- `IncrementalPdfFileWriter`: abre el PDF sin destruir su contenido.
- `open_pkcs11_session`: abre una sesión con el DNIe usando PIN.
- `PKCS11Signer`: prepara el certificado para firmar.
- `PdfSignatureMetadata`: define motivo y ubicacion de la firma.
- `TextStampStyle`: define el texto visible de la firma.
- `SigFieldSpec`: define donde se vera la firma en el PDF.
- `PdfSigner`: firma el documento.

La firma se hace en memoria con `BytesIO`.

## 18. Donde se coloca la firma visible

En:

```txt
firmador_edni_local.py -> firmar()
```

Se usa:

```python
TextStampStyle(...)
SigFieldSpec(...)
```

Esto crea una apariencia visible dentro del PDF.  
Importante: la firma digital real no es solo la imagen o texto visible. La parte mas importante queda embebida criptograficamente dentro del PDF.

Por eso, aunque el navegador no siempre muestre un panel de firmas, Adobe Acrobat Reader si puede mostrar la firma digital.

## 19. Donde se conecta main.py con el firmador

Funcion:

```txt
main.py -> _consultar_firmador_edni(ruta="/estado", payload=None, timeout=8)
```

Esta funcion importa:

```python
import firmador_edni_local
```

Y usa el `test_client()` de Flask para llamar internamente:

- `/estado`
- `/firmar`

Esto permite que el sistema use el firmador sin que el navegador llame directamente al puerto local.

## 20. Donde se guarda el PDF firmado

Funcion:

```txt
main.py -> admin_guardar_firma_edni(tid)
```

Esta funcion:

1. Lee el trámite.
2. Verifica que sea certificado de habilidad.
3. Recibe el PDF firmado en base64.
4. Decodifica el PDF.
5. Verifica que empiece con `%PDF`.
6. Genera un nombre seguro.
7. Guarda el archivo en:

```txt
static/uploads/tramites/
```

8. Actualiza el trámite como aprobado.
9. Guarda datos de firma.
10. Notifica al colegiado.

Funcion de base de datos:

```txt
colegiado_tramitesAD.py -> actualizar_estado_tramite(...)
```

## 21. Donde se registra quien firmo

En `main.py -> admin_guardar_firma_edni(tid)` se obtiene el usuario desde:

```python
usuario = session.get("profile", {}) or {}
```

Luego se manda a `actualizar_estado_tramite(...)`:

```txt
matricula del administrador
nombre del administrador
tipo_firma = eDNI
estado_firma = Firmado
detalle_firma = Certificado firmado con eDNI desde el sistema.
```

En la base de datos, tabla `tramites`, los campos son:

```txt
estado_firma
tipo_firma
firmado_por_matricula
firmado_por_nombre
firmado_en
detalle_firma
```

Estos campos estan definidos en:

```txt
database/schema.sql
```

## 22. Donde se valida la firma

Funcion:

```txt
main.py -> _validar_firma_pdf(ruta_pdf)
```

Usa pyHanko:

```python
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.sign.validation import validate_pdf_signature
```

Valida:

- Si el PDF tiene firma digital.
- Si la firma esta intacta.
- Si el documento fue modificado despues de firmar.
- Firmante.
- Emisor.
- Fecha de firma.

Pantalla:

```txt
templates/admin/admin_validar_firma.html
```

Rutas:

```txt
/admin/tramites/<id>/validar-firma
/tramites/<id>/validar-firma
```

## 23. Base de datos

Tabla principal:

```txt
tramites
```

Campos importantes para firma:

```sql
archivo_respuesta VARCHAR(255),
estado_firma VARCHAR(30) DEFAULT 'Pendiente',
tipo_firma VARCHAR(30),
firmado_por_matricula VARCHAR(30),
firmado_por_nombre VARCHAR(150),
firmado_en TIMESTAMP NULL,
detalle_firma TEXT
```

Uso:

- `archivo_respuesta`: guarda la ruta del PDF firmado.
- `estado_firma`: indica si está pendiente o firmado.
- `tipo_firma`: indica que fue firmado con eDNI.
- `firmado_por_matricula`: usuario que firmo.
- `firmado_por_nombre`: nombre del usuario que firmo.
- `firmado_en`: fecha y hora de firma.
- `detalle_firma`: comentario administrativo.

## 24. Seguridad aplicada

- El PIN del DNIe no se guarda en base de datos.
- El PIN solo viaja durante el proceso de firma.
- El PDF se firma en memoria.
- El archivo firmado se guarda con nombre unico.
- Se valida que el archivo recibido sea PDF.
- El certificado no se aprueba si el colegiado tiene deuda.
- El trámite de certificado solo se aprueba al firmar con eDNI.
- Se guarda quien firmo y cuando.
- Se puede validar la integridad del PDF firmado.

## 25. Flujo tecnico completo

```txt
Administrador abre Trámites
-> Selecciona Firmar con eDNI
-> main.py carga admin_firma_edni.html
-> admin_firma_edni.js llama a /admin/firmador-edni/estado
-> main.py llama a firmador_edni_local.py /estado
-> firmador detecta lector, DNIe y certificado
-> administrador ingresa PIN
-> JS descarga PDF base desde /certificado-habilidad/pdf?modo=firma
-> JS convierte PDF a base64
-> JS llama a /admin/firmador-edni/firmar
-> main.py llama a firmador_edni_local.py /firmar
-> pyHanko firma el PDF con PKCS#11
-> firmador devuelve PDF firmado en base64
-> JS llama a /firma-edni/guardar
-> main.py guarda PDF firmado en static/uploads/tramites
-> main.py actualiza tramite como Aprobado
-> main.py registra estado de firma
-> main.py notifica al colegiado
```

## 26. Botones del flujo y que llama cada uno

Esta seccion explica que hace cada boton relacionado con Trámites, Certificado de Habilidad, firma eDNI y validacion.

### Botones en la pantalla de Trámites del administrador

Archivo:

```txt
templates/admin/admin_tramites.html
```

### Boton: Poner en revisión

Texto:

```txt
Poner en revisión
```

Que hace:

- Cambia el estado del trámite a `En Revision`.
- Registra que el administrador tomo el trámite para evaluarlo.

Ruta que llama:

```txt
POST /admin/tramites/<id>/estado
```

Funcion que se ejecuta:

```txt
main.py -> admin_estado_tramite(tid)
```

Datos que envia:

```txt
estado = En Revision
detalle_revision = Trámite tomado para revisión administrativa.
```

### Boton: Borrador certificado

Texto:

```txt
Borrador certificado
```

Que hace:

- Abre una vista previa del Certificado de Habilidad.
- Todavia no firma el documento.
- Solo sirve para revisar como quedara el certificado.

Ruta que llama:

```txt
GET /admin/tramites/<id>/certificado-habilidad
```

Funcion que se ejecuta:

```txt
main.py -> admin_certificado_habilidad_borrador(tid)
```

Funciones internas:

```txt
_datos_certificado_habilidad(tid)
```

Si el colegiado tiene deuda, el boton queda deshabilitado porque no se debe generar certificado de habilidad con deuda.

### Boton: Firmar con eDNI

Texto:

```txt
Firmar con eDNI
```

Que hace:

- Abre la pantalla donde el administrador firma el certificado con DNI electronico.
- No firma directamente desde la lista; primero lleva a la pantalla de verificacion.

Ruta que llama:

```txt
GET /admin/tramites/<id>/firma-edni
```

Funcion que se ejecuta:

```txt
main.py -> admin_firma_edni(tid)
```

Template que carga:

```txt
templates/admin/admin_firma_edni.html
```

### Boton: Ver PDF firmado

Texto:

```txt
Ver PDF firmado
```

Que hace:

- Abre el PDF firmado que ya fue guardado en el trámite.
- No modifica base de datos.
- Solo abre el archivo.

Ruta que abre:

```txt
static/uploads/tramites/<archivo_firmado>.pdf
```

El archivo se obtiene desde el campo:

```txt
tramites.archivo_respuesta
```

### Boton: Validar firma

Texto:

```txt
Validar firma
```

Que hace:

- Revisa si el PDF tiene una firma digital embebida.
- Verifica si el documento esta intacto.
- Muestra firmante, emisor, fecha de firma y estado de integridad.
- No aprueba ni rechaza el trámite.
- No modifica la base de datos.

Ruta que llama en administrador:

```txt
GET /admin/tramites/<id>/validar-firma
```

Ruta que llama en colegiado:

```txt
GET /tramites/<id>/validar-firma
```

Funcion principal:

```txt
main.py -> admin_validar_firma_tramite(tid)
```

Luego llama a:

```txt
main.py -> _render_validacion_firma_tramite(tid, es_admin=True)
main.py -> _validar_firma_pdf(ruta_pdf)
```

La funcion `_render_validacion_firma_tramite`:

- Lee el trámite.
- Verifica que exista `archivo_respuesta`.
- Ubica el PDF dentro de `static/uploads/tramites`.
- Llama al validador de firma.

La funcion `_validar_firma_pdf` usa pyHanko:

```python
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.sign.validation import validate_pdf_signature
```

Que valida:

- Si existe firma digital dentro del PDF.
- Si la firma es criptograficamente valida.
- Si el PDF fue modificado despues de la firma.
- Quien firmo.
- Que entidad emitio el certificado.
- Fecha reportada de firma.

Template que muestra el resultado:

```txt
templates/admin/admin_validar_firma.html
```

En resumen, el boton `Validar firma` sirve para demostrar que el PDF no solo tiene texto visible, sino una firma digital real dentro del documento.

### Boton: Aprobar tramite

Texto:

```txt
Aprobar tramite
```

Que hace:

- Aprueba tramites normales.
- Puede guardar un archivo emitido si corresponde.

Ruta que llama:

```txt
POST /admin/tramites/<id>/estado
```

Funcion:

```txt
main.py -> admin_estado_tramite(tid)
```

Importante:

Para `certificado_habilidad`, este boton no se usa para aprobar. El sistema muestra que el certificado solo se aprueba firmando con eDNI.

### Boton: Rechazar

Texto:

```txt
Rechazar
```

Que hace:

- Cambia el trámite a `Rechazado`.
- Guarda el motivo o detalle de rechazo.

Ruta que llama:

```txt
POST /admin/tramites/<id>/estado
```

Funcion:

```txt
main.py -> admin_estado_tramite(tid)
```

### Botones dentro de la pantalla Firma eDNI

Archivo:

```txt
templates/admin/admin_firma_edni.html
```

Logica JavaScript:

```txt
static/js/admin/admin_firma_edni.js
```

### Boton: Ver borrador

Texto:

```txt
Ver borrador
```

Que hace:

- Abre la vista HTML del certificado.
- Sirve para revisar el diseño antes de firmar.

Ruta:

```txt
GET /admin/tramites/<id>/certificado-habilidad
```

Funcion:

```txt
main.py -> admin_certificado_habilidad_borrador(tid)
```

### Boton: Abrir PDF

Texto:

```txt
Abrir PDF
```

Que hace:

- Abre el PDF base que sera firmado.
- Todavia no tiene firma digital definitiva.

Ruta:

```txt
GET /admin/tramites/<id>/certificado-habilidad/pdf?modo=firma
```

Funcion:

```txt
main.py -> admin_certificado_habilidad_pdf(tid)
```

Funciones internas:

```txt
_datos_certificado_habilidad(tid)
_generar_pdf_certificado_habilidad(certificado)
```

### Boton: Verificar

Texto:

```txt
Verificar
```

Que hace:

- Verifica si el modulo eDNI puede detectar el lector.
- Verifica si el DNIe esta insertado.
- Verifica si existe certificado digital.
- Verifica si el certificado detectado sirve para firma.
- Habilita el boton `Firmar con eDNI` solo si todo esta correcto.

JS que lo maneja:

```txt
static/js/admin/admin_firma_edni.js -> verificarFirmador()
```

Ruta que llama:

```txt
GET /admin/firmador-edni/estado
```

Funcion en `main.py`:

```txt
main.py -> admin_firmador_edni_estado()
```

Luego llama internamente a:

```txt
main.py -> _consultar_firmador_edni("/estado")
firmador_edni_local.py -> estado()
```

La funcion `estado()` del firmador:

- Busca la DLL PKCS#11.
- Carga el driver.
- Busca lectores o slots.
- Detecta si hay DNIe insertado.
- Lee los certificados digitales.
- Devuelve si el DNIe esta listo para firmar.

### Boton: Firmar con eDNI

Texto:

```txt
Firmar con eDNI
```

Que hace:

- Toma el PDF base.
- Lo convierte a base64.
- Envía el PDF y el PIN al módulo de firma.
- Recibe el PDF firmado.
- Guarda el PDF firmado en el trámite.
- Aprueba automaticamente el trámite.
- Notifica al colegiado.

JS que lo maneja:

```txt
static/js/admin/admin_firma_edni.js -> firmarConEdni()
```

Primera llamada: obtener PDF base

```txt
GET /admin/tramites/<id>/certificado-habilidad/pdf?modo=firma
```

Funcion:

```txt
main.py -> admin_certificado_habilidad_pdf(tid)
```

Segunda llamada: firmar PDF

```txt
POST /admin/firmador-edni/firmar
```

Funcion en `main.py`:

```txt
main.py -> admin_firmador_edni_firmar()
```

Luego llama internamente a:

```txt
firmador_edni_local.py -> firmar()
```

La funcion `firmar()`:

- Abre una sesión PKCS#11 con el PIN.
- Selecciona el certificado de firma.
- Usa `PKCS11Signer`.
- Usa `PdfSigner`.
- Firma el PDF con pyHanko.
- Devuelve el PDF firmado en base64.

Tercera llamada: guardar PDF firmado

```txt
POST /admin/tramites/<id>/firma-edni/guardar
```

Funcion:

```txt
main.py -> admin_guardar_firma_edni(tid)
```

Esta funcion:

- Decodifica el PDF firmado.
- Verifica que sea PDF.
- Lo guarda en `static/uploads/tramites`.
- Actualiza el trámite a `Aprobado`.
- Registra `estado_firma`, `tipo_firma`, `firmado_por`, `firmado_en`.
- Crea una notificacion para el colegiado.

## 27. Como ejecutarlo

Instalar dependencias:

```bash
pip install -r requirements.txt
```

Ejecutar el sistema:

```bash
python main.py
```

Verificar:

- Driver RENIEC/IDPlug instalado.
- Lector conectado.
- DNIe insertado.
- Certificados digitales activos en el DNIe.
- PIN de firma disponible.

## 28. Errores comunes

`Lector no conectado`

- El sistema no detecta lector.
- Revisar conexion USB o driver.

`DNIe no insertado`

- El lector existe, pero no hay DNIe insertado.

`Certificado de firma no detectado`

- El DNIe puede no tener certificado activo.
- Puede estar detectando solo autenticacion, no firma.

`PIN incorrecto`

- El PIN ingresado no corresponde al certificado de firma.

`No se pudo usar la llave privada`

- Puede faltar permiso del driver.
- Puede estar bloqueado el PIN.
- Puede no estar usando el certificado de firma correcto.

## 29. Explicacion corta para exposicion

Se implemento un flujo de firma digital para certificados de habilidad. El sistema genera el certificado en PDF, detecta el DNI electronico mediante el driver PKCS#11, obtiene el certificado digital de firma, solicita el PIN al administrador y firma el PDF con pyHanko. Luego el documento firmado se guarda automaticamente en el trámite, se registra quien lo firmo y queda disponible para que el colegiado lo descargue.

## 30. Explicacion tecnica para el profesor

La firma no es una imagen pegada al PDF. El sistema usa PKCS#11 para acceder al certificado y a la llave privada almacenada en el DNIe. pyHanko toma el PDF base, abre una sesión PKCS#11 con el PIN del usuario y genera una firma digital embebida en el documento. Esta firma permite validar integridad, firmante, emisor y fecha. Además, se agregó una apariencia visible para que el documento muestre una zona de firma, pero la validez real está en la firma criptográfica del PDF.

## 31. Frase final recomendada

> Nuestro aporte de investigacion fue integrar firma digital con eDNI. No solo generamos un certificado, sino que lo firmamos criptograficamente usando PKCS#11 y pyHanko, lo registramos en la base de datos, guardamos auditoria del usuario que firmo y permitimos validar que el PDF no fue modificado despues de la firma.
