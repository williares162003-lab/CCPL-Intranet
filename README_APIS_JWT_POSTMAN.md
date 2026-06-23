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

## 5. Formato de rutas CRUD

Cada tabla tiene cinco APIs con el estilo trabajado en clase:

```http
/api_guardar<entidad>
/api_actualizar<entidad>/<id>
/api_eliminar<entidad>/<id>
/api_leer<entidad>xid/<id>
/api_leer<entidades>
```

Todas estas rutas usan `@jwt_required()`, por eso en Postman siempre se debe enviar el token.

## 6. Entidades disponibles

- `especialidadcolegiado`
- `colegiado`
- `usuario`
- `recuperacionpassword`
- `cuota`
- `mediopago`
- `evidenciapago`
- `transaccionpago`
- `comprobantepago`
- `configuracionmercadopago`
- `ordenmercadopago`
- `configuracionfacturacion`
- `comprobantefiscal`
- `comprobantefiscaldetalle`
- `facturacionsunatlog`
- `curso`
- `contenidocurso`
- `inscripcioncurso`
- `tramite`
- `ticket`
- `notificacion`

## 7. Ejemplos

Listar colegiados:

```http
GET /api_leercolegiados
Authorization: JWT TOKEN_GENERADO
```

Leer colegiado por id:

```http
GET /api_leercolegiadoxid/1
Authorization: JWT TOKEN_GENERADO
```

Guardar especialidad:

```http
POST /api_guardarespecialidadcolegiado
Authorization: JWT TOKEN_GENERADO
Content-Type: application/json

{
  "nombre": "Perito Tributario",
  "activo": 1
}
```

Actualizar especialidad:

```http
PUT /api_actualizarespecialidadcolegiado/1
Authorization: JWT TOKEN_GENERADO
Content-Type: application/json

{
  "nombre": "Perito Contable Actualizado",
  "activo": 1
}
```

Eliminar especialidad:

```http
DELETE /api_eliminarespecialidadcolegiado/1
Authorization: JWT TOKEN_GENERADO
```
