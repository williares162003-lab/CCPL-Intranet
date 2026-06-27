# APIs CRUD con JWT - CCPL

Las APIs estan protegidas con token JWT para probarlas desde Postman.

## 1. Instalar dependencias

```bash
pip install -r requirements.txt
```

El proyecto usa las versiones trabajadas en clase:

- `Flask==2.3.3`
- `Flask-JWT==0.3.2`
- `PyJWT==1.4.2`

## 2. Generar token

Ruta:

```http
POST /auth
```

Body:

```json
{
  "username": "admin",
  "password": "admin2024"
}
```

Respuesta esperada:

```json
{
  "access_token": "TOKEN_GENERADO"
}
```

Tambien queda disponible `POST /api/token`, pero para la presentacion usa `/auth`
porque es la ruta creada por `JWT(app, authenticate, identity)`.

## 3. Usar token en Postman

En cada API protegida agregar:

```http
Authorization: JWT TOKEN_GENERADO
```

## 4. Descargar/importar coleccion

Con el servidor abierto, importar esta ruta en Postman:

```http
GET /api/postman-collection
```

Ejemplo local:

```http
http://127.0.0.1:5000/api/postman-collection
```

Ejemplo PythonAnywhere:

```http
https://trabajodaweb.pythonanywhere.com/api/postman-collection
```

La coleccion generada es una sola y esta separada por tabla:

```text
CCPL Intranet - APIs JWT
|-- 01 - Generar token JWT
|-- especialidades_colegiado
|   |-- api_guardar_especialidad_colegiado [POST]
|   |-- api_actualizar_especialidad_colegiado [POST]
|   |-- api_eliminar_especialidad_colegiado [POST]
|   |-- api_leer_especialidad_colegiado_xid [GET]
|   `-- api_leer_especialidades_colegiado [GET]
|-- colegiados
|-- usuarios
|-- cuotas
|-- cursos
`-- demas tablas del proyecto
```

## 5. Formato de rutas CRUD

Cada tabla tiene cinco APIs con el estilo trabajado en clase:

```http
POST /api_guardar_<entidad>
POST /api_actualizar_<entidad>
POST /api_eliminar_<entidad>
GET  /api_leer_<entidad>_xid?id=1
GET  /api_leer_<entidades>
```

Para actualizar y eliminar se envia el `id` dentro del JSON. `api_leer_<entidad>_xid` tambien acepta POST si se envia el `id` en el body, pero en la coleccion se deja con GET para probarlo mas rapido.

Todas estas rutas usan `@jwt_required()`, por eso en Postman siempre se debe enviar el token.

En `main.py` las APIs quedaron escritas tabla por tabla y separadas por comentarios. No dependen de una funcion CRUD generica, para que el codigo se vea parecido al formato trabajado en clase.

## 6. Entidades disponibles

- `especialidad_colegiado`
- `colegiado`
- `usuario`
- `recuperacion_password`
- `cuota`
- `medio_pago`
- `evidencia_pago`
- `transaccion_pago`
- `comprobante_pago`
- `configuracion_mercado_pago`
- `orden_mercado_pago`
- `configuracion_facturacion`
- `comprobante_fiscal`
- `comprobante_fiscal_detalle`
- `facturacion_sunat_log`
- `curso`
- `contenido_curso`
- `inscripcion_curso`
- `tramite`
- `ticket`
- `notificacion`

## 7. Ejemplos

Listar colegiados:

```http
GET /api_leer_colegiados
Authorization: JWT TOKEN_GENERADO
```

Leer colegiado por id:

```http
GET /api_leer_colegiado_xid?id=1
Authorization: JWT TOKEN_GENERADO
```

Guardar especialidad:

```http
POST /api_guardar_especialidad_colegiado
Authorization: JWT TOKEN_GENERADO
Content-Type: application/json

{
  "nombre": "Perito Tributario",
  "activo": 1
}
```

Actualizar especialidad:

```http
POST /api_actualizar_especialidad_colegiado
Authorization: JWT TOKEN_GENERADO
Content-Type: application/json

{
  "id": 1,
  "nombre": "Perito Contable Actualizado",
  "activo": 1
}
```

Eliminar especialidad:

```http
POST /api_eliminar_especialidad_colegiado
Authorization: JWT TOKEN_GENERADO
Content-Type: application/json

{
  "id": 1
}
```
