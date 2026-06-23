import csv
import json
import os
import random
import re
import base64
import hashlib
from datetime import date, datetime, timedelta
from io import BytesIO, StringIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4

import pymysql
from decimal import Decimal
from flask import Flask, Response, flash, g, jsonify, redirect, render_template, request, session, url_for
from flask_jwt import JWT, jwt_required, current_identity
from werkzeug.utils import secure_filename

from bd import obtenerconexion
from loginAD import (autenticar_usuario, buscar_usuario_recuperacion,
                     registrar_codigo_recuperacion,
                     actualizar_password_con_codigo)
from colegiadoAD import (clsColegiado, leer_colegiados,
                         leer_especialidades_colegiados, buscar_colegiados,
                         insertar_colegiado, actualizar_colegiado,
                         toggle_estado_colegiado,
                         colegiado_vigente_con_deuda_pendiente,
                         leer_colegiado_por_matricula,
                         actualizar_perfil_colegiado,
                         leer_cursos_colegiado,
                         leer_cursos_disponibles_colegiado,
                         leer_curso_inscrito_colegiado,
                         leer_certificado_curso_colegiado,
                         leer_cuota_pago_demo,
                         registrar_pago_demo_colegiado,
                         obtener_configuracion_cuotas_colegiado,
                         generar_cuotas_adelantadas_colegiado,
                         obtener_configuracion_pago_anual_colegiado,
                         generar_cuotas_anuales_colegiado,
                         obtener_configuracion_mercado_pago,
                         actualizar_configuracion_mercado_pago,
                         crear_preferencia_mercado_pago,
                         confirmar_pago_mercado_pago,
                         leer_comprobantes_pago_colegiado,
                         leer_comprobante_pago_colegiado,
                         clsTramite, leer_tipos_tramite, leer_tramites,
                         tramite_requiere_sustento,
                         leer_tramite_por_id, insertar_tramite,
                         actualizar_estado_tramite,
                         colegiado_tiene_deuda_pendiente_matricula,
                         leer_notificaciones_colegiado,
                         contar_notificaciones_no_leidas,
                         insertar_notificacion_matricula,
                         marcar_notificacion_leida,
                         eliminar_notificaciones_leidas,
                         insertar_ticket, leer_tickets, leer_tickets_colegiado,
                         leer_ticket_por_id, actualizar_estado_ticket)
from adminAD import (clsUsuario, leer_usuarios, insertar_usuario,
                     actualizar_usuario,
                     clsCuota, leer_cuotas, contar_cuotas, resumir_cuotas,
                     insertar_cuota, pagar_cuota,
                     eliminar_cuota, leer_historial_cuota_admin,
                      obtener_resumen_cuotas_mensuales,
                      procesar_cuotas_mensuales,
                      obtener_resumen_pago_anual,
                      registrar_pago_anual_anticipado,
                      obtener_resumen_pago_adelantado,
                      registrar_pago_adelantado_cuotas,
                      procesar_cuotas_cursos_faltantes,
                     clsMedioPago, leer_medios_pago, insertar_medio_pago,
                     actualizar_medio_pago, eliminar_medio_pago,
                     leer_evidencias_pago, registrar_evidencia_pago,
                     actualizar_estado_evidencia_pago,
                     leer_transacciones_pago_demo,
                     contar_transacciones_pago_demo,
                     leer_comprobantes_pago_demo_admin,
                     contar_comprobantes_pago_demo_admin,
                     leer_comprobante_pago_demo_admin,
                     resumir_pagos_demo,
                     leer_reporte_contable_demo,
                     anular_comprobante_pago_demo,
                     leer_comprobantes_fiscales,
                     contar_comprobantes_fiscales,
                     leer_comprobante_fiscal_admin,
                     resumir_facturacion,
                     obtener_configuracion_facturacion,
                     actualizar_configuracion_facturacion,
                     emitir_comprobante_fiscal_desde_interno,
                     enviar_comprobante_fiscal_sunat,
                     anular_comprobante_fiscal,
                     clsCurso, leer_cursos,
                     leer_inscripciones_curso, contar_inscripciones_curso,
                     resumir_inscripciones_curso, insertar_inscripcion_curso,
                     validar_inscripcion_curso,
                     contar_inscritos_curso, actualizar_pago_inscripcion_curso,
                     actualizar_certificado_curso,
                     leer_estado_certificado_curso,
                     insertar_curso, actualizar_curso, eliminar_curso,
                     curso_tiene_inscripciones, curso_ya_finalizo,
                     leer_dashboard_admin, leer_reporte_financiero,
                     leer_reporte_cursos, leer_reporte_colegiados)
from ponenteAD import (leer_cursos_ponente, leer_curso_ponente,
                       leer_curso_por_id, leer_inscripcion_detalle,
                       leer_matriculas_inscritos_curso,
                       leer_inscritos_curso_ponente,
                       actualizar_contenido_curso_ponente,
                       clsContenidoCurso, leer_contenidos_curso,
                       insertar_contenido_curso_ponente,
                       eliminar_contenido_curso_ponente,
                       leer_seguimiento_ponente, contar_seguimiento_ponente,
                       resumir_seguimiento_ponente,
                       actualizar_progreso_curso_ponente,
                       leer_notificaciones_ponente,
                       contar_notificaciones_ponente)


# ============================================================
# CONFIGURACION GENERAL
# ============================================================

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "ccpl-secret-key")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["JWT_AUTH_URL_RULE"] = "/auth"
app.config["JWT_AUTH_HEADER_PREFIX"] = "JWT"


class User(object):
    def __init__(self, id, username, password, rol="admin", nombre=""):
        self.id = id
        self.username = username
        self.password = password
        self.rol = rol
        self.nombre = nombre

    def __str__(self):
        return "User(id='%s')" % self.id


def authenticate(username, password):
    usuario = autenticar_usuario(username, password)
    if usuario and usuario.get("rol") == "admin":
        return User(
            usuario.get("matricula"),
            usuario.get("matricula"),
            password,
            usuario.get("rol"),
            usuario.get("nombre", "")
        )
    return None


def identity(payload):
    user_id = payload["identity"]
    return User(user_id, user_id, "", "admin", "Administrador CCPL")


jwt = JWT(app, authenticate, identity)

EXTENSIONES_IMAGEN = {"jpg", "jpeg", "png", "webp"}
EXTENSIONES_ARCHIVO = EXTENSIONES_IMAGEN | {"pdf"}
EXTENSIONES_CERTIFICADO_SUNAT = {"pfx", "p12"}


# ============================================================
# NAVEGACION DEL SISTEMA
# ============================================================

ADMIN_NAV_ITEMS = [
    {"endpoint": "admin_dashboard",  "label": "Panel Admin",    "icon": "admin_panel_settings"},
    {"endpoint": "admin_reportes",   "label": "Reportes",       "icon": "query_stats"},
    {"endpoint": "admin_colegiados", "label": "Colegiados",     "icon": "group"},
    {"endpoint": "admin_usuarios",   "label": "Usuarios",       "icon": "manage_accounts"},
    {"endpoint": "admin_cuotas",     "label": "Cuotas",         "icon": "payments"},
    {"endpoint": "admin_pagos_demo", "label": "Pagos",          "icon": "point_of_sale"},
    {"endpoint": "admin_mercado_pago_configuracion", "label": "Mercado Pago", "icon": "credit_card"},
    {"endpoint": "admin_facturacion", "label": "Facturacion",    "icon": "receipt"},
    {"endpoint": "admin_facturacion_configuracion", "label": "SUNAT", "icon": "cloud_sync"},
    {"endpoint": "admin_medios_pago", "label": "Medios Pago",    "icon": "account_balance_wallet"},
    {"endpoint": "admin_evidencias_pago", "label": "Evidencias", "icon": "receipt_long"},
    {"endpoint": "admin_cursos",     "label": "Cursos",         "icon": "school"},
    {"endpoint": "admin_cursos_asignados", "label": "Asignaciones", "icon": "assignment_ind"},
    {"endpoint": "admin_tramites",   "label": "Tramites",       "icon": "assignment"},
    {"endpoint": "admin_tickets",    "label": "Tickets",        "icon": "support_agent"},
]

COLEGIADO_NAV_ITEMS = [
    {"endpoint": "dashboard",          "label": "Mi Panel",         "icon": "dashboard"},
    {"endpoint": "notificaciones",     "label": "Notificaciones",   "icon": "notifications"},
    {"endpoint": "estado_cuenta",      "label": "Estado de Cuenta", "icon": "receipt_long"},
    {"endpoint": "colegiado_pagos",    "label": "Pagos",            "icon": "payments"},
    {"endpoint": "educacion_continua", "label": "Educación",        "icon": "school"},
    {"endpoint": "tramites",           "label": "Tramites",         "icon": "assignment"},
    {"endpoint": "perfil_soporte",     "label": "Perfil / Soporte", "icon": "manage_accounts"},
]

PONENTE_NAV_ITEMS = [
    {"endpoint": "ponente_dashboard", "label": "Mis Cursos", "icon": "dashboard"},
    {"endpoint": "ponente_seguimiento", "label": "Seguimiento", "icon": "monitoring"},
    {"endpoint": "ponente_notificaciones", "label": "Avisos", "icon": "notifications"},
]

PONENTES_CURSO = [
    "CPC Luis Salazar",
    "CPC Ana Rojas",
    "Mg. Marco Silva",
    "CPC Patricia Leon",
    "CPC Rosa Medina",
]

METODOS_PAGO_INTERNO = [
    "Tarjeta",
    "Yape",
    "PagoEfectivo",
]


# ============================================================
# FUNCIONES AUXILIARES GENERALES
# ============================================================

def contexto_base(titulo: str, activo: str, subtitulo: str = "",
                  es_admin: bool = False, es_ponente: bool = False) -> dict:
    nav_items = COLEGIADO_NAV_ITEMS
    if es_admin:
        nav_items = ADMIN_NAV_ITEMS
    elif es_ponente:
        nav_items = PONENTE_NAV_ITEMS

    profile = session.get("profile", {"nombre": "", "matricula": ""})
    unread_count = 0
    notifs_recientes = []
    matricula = profile.get("matricula", "")
    if es_ponente:
        try:
            nombre_ponente = profile.get("nombre", "")
            unread_count = contar_notificaciones_ponente(nombre_ponente)
            notifs_recientes = leer_notificaciones_ponente(
                nombre_ponente,
                p_limite=5
            ) or []
        except Exception as e:
            print("Error al cargar avisos de ponente:", repr(e))
    elif matricula and not es_admin:
        try:
            unread_count = contar_notificaciones_no_leidas(matricula)
            notifs_recientes = leer_notificaciones_colegiado(
                matricula,
                p_solo_no_leidas=True,
                p_limite=5
            ) or []
        except Exception as e:
            print("Error al cargar notificaciones base:", repr(e))

    return {
        "nav_items": nav_items,
        "active_page": activo,
        "page_title": titulo,
        "page_subtitle": subtitulo,
        "profile": profile,
        "today": date.today().strftime("%d/%m/%Y"),
        "today_iso": date.today().isoformat(),
        "is_admin": es_admin,
        "is_ponente": es_ponente,
        "unread_count": unread_count,
        "notifs_recientes": notifs_recientes,
    }


def mostrar_exito(mensaje: str, volver_endpoint: str = "admin_dashboard",
                  primary_label: str = "Volver al panel"):
    rol = session.get("rol", "")
    if rol == "colegiado":
        panel = "dashboard"
    elif rol == "ponente":
        panel = "ponente_dashboard"
    else:
        panel = "admin_dashboard"
    return render_template("exito.html",
                           mensaje=mensaje,
                           volver_endpoint=volver_endpoint,
                           primary_label=primary_label,
                           panel_endpoint=panel)


def mostrar_error(mensaje: str, status: int = 400):
    rol = session.get("rol", "")
    if rol == "colegiado":
        volver = "dashboard"
    elif rol == "ponente":
        volver = "ponente_dashboard"
    else:
        volver = "admin_dashboard"
    return render_template("error400.html", mensaje=mensaje, status=status,
                           volver_endpoint=volver), status


# ============================================================
# SEGURIDAD DE SESSION Y ACCESO POR ROL
# ============================================================

RUTAS_PUBLICAS = {
    "index",
    "login",
    "logout",
    "recuperar_contrasena",
    "restablecer_contrasena",
    "jwt",
    "api_token",
    "api_auth",
    "api_postman_collection",
    "static",
    "mercado_pago_webhook",
}


def _panel_por_rol():
    rol = session.get("rol", "")
    if rol == "admin":
        return "admin_dashboard"
    if rol == "ponente":
        return "ponente_dashboard"
    return "dashboard"


def _es_peticion_api(endpoint):
    return bool(endpoint and endpoint.startswith("api_"))


def _respuesta_api(code, message, data=None, status=200):
    return jsonify({
        "code": code,
        "data": data if data is not None else {},
        "message": message
    }), status


def _importar_pyjwt():
    try:
        import jwt
        return jwt
    except ImportError as exc:
        raise RuntimeError(
            "Falta instalar PyJWT. Ejecute: pip install PyJWT==2.8.0"
        ) from exc


def _generar_token_jwt(usuario):
    jwt = _importar_pyjwt()
    ahora = datetime.utcnow()
    payload = {
        "identity": usuario.get("matricula"),
        "sub": usuario.get("matricula"),
        "rol": usuario.get("rol"),
        "nombre": usuario.get("nombre"),
        "iat": ahora,
        "exp": ahora + timedelta(hours=8),
    }
    token = jwt.encode(payload, app.config["SECRET_KEY"], algorithm="HS256")
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


def _token_desde_header():
    cabecera = request.headers.get("Authorization", "").strip()
    if not cabecera:
        return ""
    partes = cabecera.split(None, 1)
    if len(partes) == 2 and partes[0].lower() in ["bearer", "jwt"]:
        return partes[1].strip()
    return cabecera


def _usuario_desde_jwt():
    token = _token_desde_header()
    if not token:
        return None, "Debe enviar el token JWT en Authorization."

    jwt = _importar_pyjwt()
    try:
        payload = jwt.decode(
            token,
            app.config["SECRET_KEY"],
            algorithms=["HS256"]
        )
    except jwt.ExpiredSignatureError:
        return None, "El token JWT vencio. Genere uno nuevo."
    except jwt.InvalidTokenError:
        return None, "El token JWT no es valido."

    usuario = {
        "matricula": payload.get("identity") or payload.get("sub"),
        "rol": payload.get("rol") or "admin",
        "nombre": payload.get("nombre") or payload.get("identity") or "Administrador CCPL",
    }
    if not usuario["matricula"] or not usuario["rol"]:
        return None, "El token JWT no contiene datos de usuario validos."
    return usuario, ""


def _usuario_api_actual():
    if hasattr(g, "api_identity"):
        return g.api_identity, ""

    usuario, error = _usuario_desde_jwt()
    if usuario:
        g.api_identity = usuario
        return usuario, ""

    if session.get("rol") == "admin":
        profile = session.get("profile", {}) or {}
        usuario = {
            "matricula": profile.get("matricula", "admin"),
            "rol": "admin",
            "nombre": profile.get("nombre", "Administrador CCPL"),
        }
        g.api_identity = usuario
        return usuario, ""

    return None, error

def _respuesta_no_autenticado(endpoint):
    if _es_peticion_api(endpoint):
        return jsonify({
            "code": 0,
            "data": {},
            "message": "Debe iniciar sesion para usar esta API."
        }), 401
    flash("Inicie sesion para acceder al sistema.", "error")
    return redirect(url_for("login"))


def _respuesta_sin_permiso(endpoint):
    if _es_peticion_api(endpoint):
        return jsonify({
            "code": 0,
            "data": {},
            "message": "No tiene permisos para usar esta API."
        }), 403
    return mostrar_error("No tiene permisos para acceder a esta seccion.", 403)


def _rol_requerido_por_ruta(endpoint, ruta):
    if (
        endpoint and endpoint.startswith("admin_")
        or ruta == "/admin"
        or ruta.startswith("/admin/")
        or _es_peticion_api(endpoint)
    ):
        return "admin"

    if (
        endpoint and endpoint.startswith("ponente_")
        or ruta == "/ponente"
        or ruta.startswith("/ponente/")
    ):
        return "ponente"

    if endpoint and endpoint not in RUTAS_PUBLICAS:
        return "colegiado"
    return ""


@app.before_request
def proteger_rutas_con_session():
    endpoint = request.endpoint
    ruta = request.path or ""

    if endpoint in RUTAS_PUBLICAS:
        return None

    if _es_peticion_api(endpoint):
        usuario, error = _usuario_api_actual()
        if not usuario:
            return _respuesta_api(0, error, status=401)
        if usuario.get("rol") != "admin":
            return _respuesta_api(0, "Solo el administrador puede usar las APIs.", status=403)
        return None

    rol_requerido = _rol_requerido_por_ruta(endpoint, ruta)
    if not rol_requerido:
        return None

    if "user" not in session or "rol" not in session:
        return _respuesta_no_autenticado(endpoint)

    if session.get("rol") != rol_requerido:
        return _respuesta_sin_permiso(endpoint)

    return None


# ============================================================
# VALIDACIONES Y FORMATOS
# ============================================================

def _validar_dni_peru(dni: str) -> bool:
    return bool(re.fullmatch(r"\d{8}", dni.strip()))


def _validar_nombre_peru(nombre: str) -> bool:
    patron = r"[A-Za-záéíóúÁÉÍÓÚüÜñÑ\s\.\-]{3,100}"
    return bool(re.fullmatch(patron, nombre.strip()))


def _validar_telefono_peru(tel: str) -> bool:
    if not tel.strip():
        return True
    return bool(re.fullmatch(r"9\d{8}", tel.strip()))


def _validar_correo(correo: str) -> bool:
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", correo.strip()))


def _correo_oculto(correo):
    correo = (correo or "").strip()
    if "@" not in correo:
        return ""
    usuario, dominio = correo.split("@", 1)
    visible = usuario[:2] if len(usuario) > 2 else usuario[:1]
    return visible + "***@" + dominio


def _enviar_codigo_recuperacion(correo, nombre, codigo):
    import smtplib
    from email.message import EmailMessage

    host = os.getenv("CCPL_SMTP_HOST", "smtp.gmail.com").strip()
    port = int(os.getenv("CCPL_SMTP_PORT", "587"))
    usuario = os.getenv("CCPL_SMTP_USER", "").strip()
    password = os.getenv("CCPL_SMTP_PASSWORD", "").strip()
    remitente = os.getenv("CCPL_SMTP_FROM", usuario).strip()
    usar_tls = os.getenv("CCPL_SMTP_TLS", "1").strip() != "0"

    if not usuario or not password or not remitente:
        return {
            "ok": False,
            "mensaje": "Falta configurar el correo SMTP del sistema."
        }

    mensaje = EmailMessage()
    mensaje["Subject"] = "Codigo de recuperacion - Intranet CCPL"
    mensaje["From"] = remitente
    mensaje["To"] = correo
    mensaje.set_content(
        "Hola, {0}.\n\n"
        "Tu codigo para restablecer la contrasena en la Intranet CCPL es:\n\n"
        "{1}\n\n"
        "El codigo vence en 10 minutos. Si no solicitaste este cambio, ignora este correo.\n\n"
        "Colegio de Contadores Publicos de Lambayeque".format(
            nombre or "colegiado",
            codigo
        )
    )

    try:
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            if usar_tls:
                smtp.starttls()
            smtp.login(usuario, password)
            smtp.send_message(mensaje)
        return {"ok": True, "mensaje": "Codigo enviado correctamente."}
    except smtplib.SMTPAuthenticationError as e:
        print("Error SMTP recuperacion:", repr(e))
        return {
            "ok": False,
            "mensaje": "Gmail rechazo el usuario o clave SMTP. Use una contrasena de aplicacion."
        }
    except (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected, TimeoutError, OSError) as e:
        print("Error SMTP recuperacion:", repr(e))
        return {
            "ok": False,
            "mensaje": "No se pudo conectar con el servidor SMTP. Revise internet, host y puerto."
        }
    except smtplib.SMTPException as e:
        print("Error SMTP recuperacion:", repr(e))
        return {
            "ok": False,
            "mensaje": "El servidor SMTP rechazo el envio. Revise la configuracion del correo."
        }
    except Exception as e:
        print("Error SMTP recuperacion:", repr(e))
        return {
            "ok": False,
            "mensaje": "No se pudo enviar el correo de recuperacion. Revise la consola de Flask."
        }


def _leer_fecha_iso(valor: str):
    try:
        return date.fromisoformat(valor.strip())
    except ValueError:
        return None


def _resumen_fecha_curso(fecha_inicio: str, fecha_fin: str) -> str:
    if fecha_inicio == fecha_fin:
        return "Fecha: " + fecha_inicio
    return "Del " + fecha_inicio + " al " + fecha_fin


def _monto(valor) -> float:
    try:
        return float(valor or 0)
    except (TypeError, ValueError):
        return 0


def _nombre_periodo(mes, anio) -> str:
    if not mes or not anio:
        return ""
    meses = [
        "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    try:
        return f"{meses[int(mes)]} {int(anio)}"
    except (TypeError, ValueError, IndexError):
        return ""


def _fecha_larga(fecha_valor) -> str:
    if not fecha_valor:
        fecha_valor = date.today()
    if isinstance(fecha_valor, str):
        fecha_valor = _leer_fecha_iso(fecha_valor) or date.today()
    meses = [
        "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    return f"{fecha_valor.day:02d} de {meses[fecha_valor.month]} del {fecha_valor.year}"


def _fecha_certificado_habilidad(fecha_valor) -> str:
    if not fecha_valor:
        fecha_valor = date.today()
    if isinstance(fecha_valor, str):
        fecha_valor = _leer_fecha_iso(fecha_valor) or date.today()
    meses = [
        "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "setiembre", "octubre", "noviembre", "diciembre"
    ]
    return f"{fecha_valor.day:02d} de {meses[fecha_valor.month]} {fecha_valor.year}"


def _texto_pdf(valor) -> str:
    texto = str(valor or "")
    return texto.encode("latin-1", "replace").decode("latin-1")


def _datos_certificado_habilidad(tid):
    tramite = leer_tramite_por_id(tid)
    if not tramite:
        return None, None, "El tramite seleccionado no existe.", 404
    if tramite.get("tipo_tramite") != "certificado_habilidad":
        return None, None, "Este proceso solo corresponde a certificados de habilidad.", 400

    matricula = tramite.get("matricula", "")
    if colegiado_tiene_deuda_pendiente_matricula(matricula):
        return None, None, "No se puede generar el certificado porque el colegiado tiene cuotas pendientes.", 400

    colegiado = leer_colegiado_por_matricula(matricula) or {}
    hoy = date.today()
    vigencia = (colegiado.get("vigencia") or "").strip()
    if not vigencia:
        vigencia = "Fecha de vigencia por definir"

    certificado = {
        "numero": f"001-{tid:06d}",
        "fecha_emision": _fecha_certificado_habilidad(hoy),
        "ciudad": "Chiclayo",
        "nombre": colegiado.get("nombre") or tramite.get("nombre", ""),
        "documento": colegiado.get("documento") or "",
        "matricula": matricula,
        "habil_hasta": vigencia.upper(),
        "firmante_nombre": "M.Sc. CPC. ADAN PABLO CIEZA PEREZ",
        "firmante_cargo": "DECANO DEL COLEGIO DE CONTADORES PUBLICOS DE LAMBAYEQUE",
        "estado_firma": "PENDIENTE DE FIRMA DIGITAL eDNI",
        "tramite_id": tid,
    }
    return certificado, tramite, "", 200


def _fuente_certificado(tamano, negrita=False):
    try:
        from PIL import ImageFont
    except ImportError:
        return None

    candidatos = []
    if negrita:
        candidatos.extend([
            Path("C:/Windows/Fonts/timesbd.ttf"),
            Path("C:/Windows/Fonts/arialbd.ttf"),
        ])
    else:
        candidatos.extend([
            Path("C:/Windows/Fonts/times.ttf"),
            Path("C:/Windows/Fonts/arial.ttf"),
        ])
    candidatos.append(Path("C:/Windows/Fonts/calibri.ttf"))

    for ruta in candidatos:
        if ruta.exists():
            return ImageFont.truetype(str(ruta), tamano)
    return ImageFont.load_default()


def _ajustar_fuente(draw, texto, ancho_maximo, tamano, negrita=False,
                   minimo=18):
    fuente = _fuente_certificado(tamano, negrita)
    while tamano > minimo:
        caja = draw.textbbox((0, 0), texto, font=fuente)
        if caja[2] - caja[0] <= ancho_maximo:
            return fuente
        tamano -= 1
        fuente = _fuente_certificado(tamano, negrita)
    return fuente


def _texto_centrado(draw, xy, ancho, texto, fuente, fill):
    caja = draw.textbbox((0, 0), texto, font=fuente)
    x = xy[0] + (ancho - (caja[2] - caja[0])) / 2
    draw.text((x, xy[1]), texto, font=fuente, fill=fill)


def _texto_derecha(draw, xy, texto, fuente, fill):
    caja = draw.textbbox((0, 0), texto, font=fuente)
    draw.text((xy[0] - (caja[2] - caja[0]), xy[1]), texto,
              font=fuente, fill=fill)


def _texto_codigo_barras(numero):
    texto = re.sub(r"[^0-9-]", "", str(numero or ""))
    return " ".join(texto)


def _dibujar_codigo_barras(draw, numero, x, y, ancho, alto):
    digest = hashlib.sha256(str(numero).encode("utf-8")).hexdigest()
    bits = "".join(bin(int(char, 16))[2:].zfill(4) for char in digest)
    cursor = x
    draw.rectangle((x, y, x + 2, y + alto), fill=(0, 0, 0))
    cursor += 5
    for i in range(0, len(bits), 3):
        if cursor >= x + ancho:
            break
        valor = bits[i:i + 3]
        grosor = 1 + (int(valor or "0", 2) % 3)
        if valor.count("1") >= 2:
            draw.rectangle((cursor, y, cursor + grosor, y + alto), fill=(0, 0, 0))
        cursor += grosor + 2
    draw.rectangle((x + ancho - 3, y, x + ancho - 1, y + alto), fill=(0, 0, 0))


def _generar_qr_certificado(certificado, tamano):
    payload = {
        "tipo": "CONSTANCIA_HABILIDAD_CCPL",
        "numero": certificado["numero"],
        "matricula": certificado["matricula"],
        "nombre": certificado["nombre"],
        "emision": certificado["fecha_emision"],
        "vigencia": certificado["habil_hasta"],
    }
    texto = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    try:
        import qrcode
        qr = qrcode.QRCode(border=1, box_size=8)
        qr.add_data(texto)
        qr.make(fit=True)
        imagen = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        return imagen.resize((tamano, tamano))
    except Exception:
        from PIL import Image, ImageDraw
        imagen = Image.new("RGB", (tamano, tamano), "white")
        draw = ImageDraw.Draw(imagen)
        digest = hashlib.sha256(texto.encode("utf-8")).digest()
        celda = max(3, tamano // 29)
        for fila in range(29):
            for col in range(29):
                valor = digest[(fila * 29 + col) % len(digest)]
                if (valor + fila + col) % 3 == 0:
                    draw.rectangle(
                        (col * celda, fila * celda, (col + 1) * celda, (fila + 1) * celda),
                        fill="black"
                    )
        return imagen


def _generar_qr_data_uri(texto, tamano=150):
    try:
        import qrcode
        qr = qrcode.QRCode(border=1, box_size=8)
        qr.add_data(texto)
        qr.make(fit=True)
        imagen = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        imagen = imagen.resize((tamano, tamano))
    except Exception:
        from PIL import Image, ImageDraw
        imagen = Image.new("RGB", (tamano, tamano), "white")
        draw = ImageDraw.Draw(imagen)
        digest = hashlib.sha256(str(texto).encode("utf-8")).digest()
        celda = max(3, tamano // 29)
        for fila in range(29):
            for col in range(29):
                valor = digest[(fila * 29 + col) % len(digest)]
                if (valor + fila + col) % 3 == 0:
                    draw.rectangle(
                        (col * celda, fila * celda,
                         (col + 1) * celda, (fila + 1) * celda),
                        fill="black"
                    )

    buffer = BytesIO()
    imagen.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return "data:image/png;base64," + encoded


def _tipo_comprobante_sunat_codigo(tipo):
    return "01" if str(tipo or "").strip().lower() == "factura" else "03"


def _qr_comprobante_fiscal(config, comprobante, numero_comprobante):
    total = _monto(comprobante.get("total"))
    igv = _monto(comprobante.get("igv"))
    datos = [
        str(config.get("ruc") or ""),
        _tipo_comprobante_sunat_codigo(comprobante.get("tipo_comprobante")),
        str(comprobante.get("serie") or ""),
        str(comprobante.get("numero") or ""),
        format(igv, ".2f"),
        format(total, ".2f"),
        str(comprobante.get("fecha_emision") or ""),
        str(comprobante.get("tipo_documento_cliente") or ""),
        str(comprobante.get("numero_documento_cliente") or ""),
        str(comprobante.get("codigo_hash") or ""),
    ]
    return _generar_qr_data_uri("|".join(datos), 148)


def _generar_pdf_certificado_habilidad(certificado):
    try:
        from fpdf import FPDF
        from PIL import Image, ImageDraw
    except ImportError:
        return None

    plantilla = Path(app.root_path) / "static" / "imagenes" / "certificado-habilidad-base.png"
    if not plantilla.exists():
        return None

    imagen = Image.open(plantilla).convert("RGB")
    draw = ImageDraw.Draw(imagen)
    azul = (21, 59, 116)
    blanco = (255, 255, 255)
    negro = (0, 0, 0)
    mostrar_firma = str(certificado.get("estado_firma") or "").strip().upper().startswith("FIRMA DIGITAL")

    numero = str(certificado["numero"])
    draw.rounded_rectangle((868, 284, 1068, 324), radius=8, fill=azul)
    fuente_numero = _ajustar_fuente(draw, numero, 176, 31, negrita=True, minimo=22)
    _texto_centrado(draw, (868, 289), 200, numero, fuente_numero, blanco)

    nombre = "CPC. " + str(certificado["nombre"]).upper()
    matricula = "MATRICULA " + str(certificado["matricula"]).upper()
    fuente_nombre = _ajustar_fuente(draw, nombre, 760, 28, negrita=True, minimo=20)
    fuente_matricula = _ajustar_fuente(draw, matricula, 600, 28, negrita=True, minimo=20)
    _texto_centrado(draw, (205, 738), 780, nombre, fuente_nombre, negro)
    _texto_centrado(draw, (205, 790), 780, matricula, fuente_matricula, negro)

    fuente_fecha = _ajustar_fuente(
        draw,
        certificado["ciudad"] + ", " + certificado["fecha_emision"],
        380,
        29,
        negrita=False,
        minimo=20,
    )
    _texto_derecha(
        draw,
        (1025, 1069),
        certificado["ciudad"] + ", " + certificado["fecha_emision"],
        fuente_fecha,
        negro,
    )

    vigencia = "HABIL HASTA EL " + str(certificado["habil_hasta"]).upper()
    draw.rounded_rectangle((176, 1400, 615, 1437), radius=7, fill=azul)
    fuente_vigencia = _ajustar_fuente(draw, vigencia, 410, 22, negrita=False, minimo=16)
    _texto_centrado(draw, (176, 1406), 439, vigencia, fuente_vigencia, blanco)

    if mostrar_firma:
        draw.line((350, 1240, 840, 1240), fill=negro, width=2)
        fuente_estado = _fuente_certificado(18, negrita=False)
        fuente_firmante = _fuente_certificado(20, negrita=True)
        fuente_cargo = _fuente_certificado(18, negrita=True)
        _texto_centrado(
            draw,
            (350, 1248),
            490,
            "Firmado digitalmente con eDNI",
            fuente_estado,
            negro,
        )
        _texto_centrado(
            draw,
            (280, 1285),
            640,
            str(certificado.get("firmante_nombre") or "").upper(),
            fuente_firmante,
            negro,
        )
        _texto_centrado(
            draw,
            (250, 1320),
            700,
            str(certificado.get("firmante_cargo") or "").upper(),
            fuente_cargo,
            negro,
        )

        qr = _generar_qr_certificado(certificado, 112)
        imagen.paste(qr, (724, 1362))
        _dibujar_codigo_barras(draw, numero, 888, 1362, 178, 78)
        fuente_barra = _fuente_certificado(19, negrita=False)
        _texto_centrado(draw, (878, 1450), 205, _texto_codigo_barras(numero), fuente_barra, negro)

    pdf = FPDF("P", "mm", "A4")
    pdf.set_auto_page_break(False)
    pdf.add_page()
    temporal = None
    try:
        with NamedTemporaryFile(delete=False, suffix=".png") as archivo:
            temporal = Path(archivo.name)
            imagen.save(archivo, format="PNG")
        pdf.image(str(temporal), x=0, y=0, w=210, h=297)
        salida = pdf.output(dest="S")
        if isinstance(salida, str):
            return salida.encode("latin-1")
        return bytes(salida)
    finally:
        if temporal and temporal.exists():
            try:
                temporal.unlink()
            except OSError:
                pass


def _respuesta_csv(nombre_archivo, encabezados, filas):
    salida = StringIO()
    salida.write("\ufeff")
    writer = csv.writer(salida, delimiter=";")
    writer.writerow(encabezados)
    for fila in filas:
        writer.writerow(fila)
    return Response(
        salida.getvalue(),
        content_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={nombre_archivo}"}
    )


# ============================================================
# NOTIFICACIONES AUXILIARES
# ============================================================

def _notificar_colegiado(matricula, tipo, titulo, mensaje,
                         endpoint="notificaciones", link_text="Ver aviso",
                         relacion_tipo=None, relacion_id=None):
    if not matricula:
        return False
    try:
        return insertar_notificacion_matricula(
            matricula,
            tipo,
            titulo,
            mensaje,
            endpoint,
            link_text,
            relacion_tipo,
            relacion_id
        )
    except Exception as e:
        print("Error al registrar notificacion:", repr(e))
        return False


def _notificar_inscritos_curso(curso_id, tipo, titulo, mensaje,
                               endpoint="educacion_continua",
                               link_text="Ver curso"):
    enviados = 0
    for inscrito in (leer_matriculas_inscritos_curso(curso_id) or []):
        if _notificar_colegiado(
            inscrito.get("matricula"),
            tipo,
            titulo,
            mensaje,
            endpoint,
            link_text,
            "curso",
            curso_id
        ):
            enviados += 1
    return enviados


# ============================================================
# AULA, ARCHIVOS Y CERTIFICADOS
# ============================================================

def _ruta_archivo_estatico_upload(ruta):
    if not ruta:
        return None
    ruta_limpia = str(ruta).replace("\\", "/").lstrip("/")
    if not ruta_limpia.startswith("uploads/"):
        return None

    base_static = (Path(app.root_path) / "static").resolve()
    base_uploads = (base_static / "uploads").resolve()
    destino = (base_static / ruta_limpia).resolve()
    try:
        destino.relative_to(base_uploads)
    except ValueError:
        return None
    return destino


def _archivo_estatico_existe(ruta):
    destino = _ruta_archivo_estatico_upload(ruta)
    return bool(destino and destino.is_file())


def _certificado_asn1_nombre(certificado, campo):
    try:
        datos = getattr(getattr(certificado, campo, None), "native", {}) or {}
        return (
            datos.get("common_name")
            or datos.get("organization_name")
            or getattr(getattr(certificado, campo, None), "human_friendly", "")
            or ""
        )
    except Exception:
        return ""


def _validar_firma_pdf(ruta_pdf):
    resultado = {
        "ok": False,
        "estado": "No validado",
        "mensaje": "",
        "firmas": [],
    }

    if not ruta_pdf or not Path(ruta_pdf).is_file():
        resultado["estado"] = "Archivo no encontrado"
        resultado["mensaje"] = "No se encontro el PDF firmado en el sistema."
        return resultado

    try:
        from contextlib import redirect_stderr
        from pyhanko.pdf_utils.reader import PdfFileReader
        from pyhanko.sign.validation import validate_pdf_signature
    except ImportError:
        resultado["estado"] = "Validador no disponible"
        resultado["mensaje"] = "Falta instalar pyHanko para validar firmas PDF."
        return resultado

    try:
        with open(ruta_pdf, "rb") as archivo:
            lector = PdfFileReader(archivo)
            firmas = list(lector.embedded_signatures or [])
            if not firmas:
                resultado["estado"] = "Sin firma digital"
                resultado["mensaje"] = "El PDF no contiene una firma digital embebida."
                return resultado

            for indice, firma in enumerate(firmas, start=1):
                try:
                    with redirect_stderr(StringIO()):
                        estado = validate_pdf_signature(firma)
                    certificado = getattr(estado, "signing_cert", None)
                    firmante = _certificado_asn1_nombre(certificado, "subject")
                    emisor = _certificado_asn1_nombre(certificado, "issuer")
                    datos_subject = getattr(
                        getattr(certificado, "subject", None),
                        "native",
                        {}
                    ) or {}
                    firmado_en = getattr(estado, "signer_reported_dt", None)
                    if firmado_en:
                        firmado_en = firmado_en.strftime("%Y-%m-%d %H:%M:%S")

                    nivel = getattr(estado, "modification_level", "")
                    nivel_nombre = getattr(nivel, "name", str(nivel))
                    resumen = estado.summary() if hasattr(estado, "summary") else ""

                    resultado["firmas"].append({
                        "numero": indice,
                        "campo": getattr(firma, "field_name", "") or f"Firma {indice}",
                        "intacta": bool(getattr(estado, "intact", False)),
                        "valida": bool(getattr(estado, "valid", False)),
                        "confiable": bool(getattr(estado, "trusted", False)),
                        "resumen": resumen,
                        "firmante": firmante or "Certificado digital",
                        "dni": datos_subject.get("serial_number", ""),
                        "emisor": emisor or "Autoridad certificadora",
                        "firmado_en": firmado_en or "Fecha no informada",
                        "modificacion": nivel_nombre,
                    })
                except Exception as exc:
                    resultado["firmas"].append({
                        "numero": indice,
                        "campo": getattr(firma, "field_name", "") or f"Firma {indice}",
                        "intacta": False,
                        "valida": False,
                        "confiable": False,
                        "resumen": "ERROR",
                        "firmante": "No legible",
                        "dni": "",
                        "emisor": "",
                        "firmado_en": "",
                        "modificacion": "",
                        "error": str(exc),
                    })

        alguna_valida = any(f["valida"] for f in resultado["firmas"])
        todas_intactas = all(f["intacta"] for f in resultado["firmas"])
        resultado["ok"] = bool(alguna_valida and todas_intactas)
        if resultado["ok"]:
            resultado["estado"] = "Firma integra"
            resultado["mensaje"] = (
                "El PDF contiene firma digital criptograficamente valida y "
                "no presenta cambios despues de la firma."
            )
        else:
            resultado["estado"] = "Firma observada"
            resultado["mensaje"] = "El PDF tiene una firma, pero requiere revision."
        return resultado
    except Exception as exc:
        resultado["estado"] = "Error al validar"
        resultado["mensaje"] = str(exc)
        return resultado


def _marcar_archivos_aula(materiales):
    for material in materiales:
        material["archivo_existe"] = _archivo_estatico_existe(material.get("archivo"))


def _armar_materiales_aula(curso_id):
    materiales = [dict(m) for m in (leer_contenidos_curso(curso_id) or [])]
    _marcar_archivos_aula(materiales)
    return materiales


def _puede_ver_certificado(curso):
    return (
        curso
        and curso.get("estado_pago") == "Pagado"
        and int(curso.get("progreso") or 0) >= 100
        and bool(curso.get("certificado"))
    )


def _certificado_habilitado(registro):
    return (
        registro
        and registro.get("estado_pago") == "Pagado"
        and int(registro.get("progreso") or 0) >= 100
    )


def _resumen_aula_colegiado(materiales, curso, puede_certificado):
    if puede_certificado:
        estado_certificado = "Certificado disponible."
    elif curso.get("estado_pago") != "Pagado":
        estado_certificado = "Pago pendiente para habilitar certificado."
    elif int(curso.get("progreso") or 0) < 100:
        estado_certificado = "Completa el curso para habilitar certificado."
    else:
        estado_certificado = "Certificado pendiente de registro."

    return {
        "total_materiales": len(materiales or []),
        "estado_materiales": (
            "Material disponible para revisar."
            if len(materiales or []) == 1
            else f"{len(materiales or [])} materiales disponibles."
            if materiales else "El ponente aun no publico materiales."
        ),
        "estado_certificado": estado_certificado,
    }


def _resumen_aula_ponente(materiales, inscritos):
    total_inscritos = len(inscritos or [])
    progreso_promedio = 0
    if total_inscritos:
        progreso_promedio = round(
            sum(int(i.get("progreso") or 0) for i in inscritos) / total_inscritos
        )
    return {
        "total_materiales": len(materiales or []),
        "total_inscritos": total_inscritos,
        "progreso_promedio": progreso_promedio,
    }


def _guardar_archivo_subido(archivo, carpeta: str, extensiones: set[str]):
    if not archivo or not archivo.filename:
        return ""

    nombre_original = secure_filename(archivo.filename)
    if not nombre_original or "." not in nombre_original:
        return None

    extension = nombre_original.rsplit(".", 1)[1].lower()
    if extension not in extensiones:
        return None

    destino = Path(app.root_path) / "static" / "uploads" / carpeta
    destino.mkdir(parents=True, exist_ok=True)
    nombre_final = f"{date.today().strftime('%Y%m%d')}_{uuid4().hex[:10]}_{nombre_original}"
    archivo.save(destino / nombre_final)
    return f"uploads/{carpeta}/{nombre_final}"


def _guardar_certificado_sunat(archivo):
    if not archivo or not archivo.filename:
        return ""

    nombre_original = secure_filename(archivo.filename)
    if not nombre_original or "." not in nombre_original:
        return None

    extension = nombre_original.rsplit(".", 1)[1].lower()
    if extension not in EXTENSIONES_CERTIFICADO_SUNAT:
        return None

    destino = Path(app.root_path) / "private" / "sunat_certificados"
    destino.mkdir(parents=True, exist_ok=True)
    nombre_final = f"{date.today().strftime('%Y%m%d')}_{uuid4().hex[:10]}_{nombre_original}"
    ruta_final = (destino / nombre_final).resolve()
    archivo.save(ruta_final)
    return str(ruta_final)

# ============================================================
# MANEJO DE ERRORES
# ============================================================

@app.errorhandler(404)
def pagina_no_encontrada(error):
    return mostrar_error("La pagina solicitada no existe.", 404)


@app.errorhandler(500)
def error_servidor(error):
    return render_template("error500.html"), 500


# ============================================================
# RUTAS WEB - AUTENTICACION Y ENTRADA
# ============================================================

@app.route("/", endpoint="index")
def inicio():
    if "user" not in session:
        return redirect(url_for("login"))
    if session.get("rol") == "admin":
        return redirect(url_for("admin_dashboard"))
    if session.get("rol") == "ponente":
        return redirect(url_for("ponente_dashboard"))
    return redirect(url_for("dashboard"))


@app.route("/login", methods=["GET", "POST"], endpoint="login")
def login():
    if request.method == "GET" and "user" in session and "rol" in session:
        return redirect(url_for(_panel_por_rol()))

    if request.method == "POST":
        user_id = request.form.get("membership-id", "")
        password = request.form.get("password", "")
        user = autenticar_usuario(user_id, password)
        if user:
            session["user"] = user_id
            session["rol"] = user["rol"]
            session["profile"] = {"nombre": user["nombre"], "matricula": user["matricula"]}
            if user["rol"] == "admin":
                return redirect(url_for("admin_dashboard"))
            if user["rol"] == "ponente":
                return redirect(url_for("ponente_dashboard"))
            return redirect(url_for("dashboard"))
        flash("Credenciales incorrectas.", "error")
    return render_template("login.html", page_title="Inicio de sesión")


@app.route("/recuperar-contrasena", methods=["GET", "POST"],
           endpoint="recuperar_contrasena")
def recuperar_contrasena():
    if request.method == "POST":
        identificador = request.form.get("identificador", "").strip()
        if not identificador:
            flash("Ingrese su matricula o correo registrado.", "error")
            return redirect(url_for("recuperar_contrasena"))

        usuario = buscar_usuario_recuperacion(identificador)
        if not usuario:
            flash("No se encontro un usuario activo con esos datos.", "error")
            return redirect(url_for("recuperar_contrasena"))

        correo = (usuario.get("correo") or "").strip()
        if not correo or not _validar_correo(correo):
            flash("El usuario no tiene un correo valido registrado.", "error")
            return redirect(url_for("recuperar_contrasena"))

        codigo = f"{random.randint(0, 999999):06d}"
        if not registrar_codigo_recuperacion(
            usuario.get("matricula"),
            correo,
            codigo,
            minutos=10
        ):
            flash("No se pudo generar el codigo de recuperacion.", "error")
            return redirect(url_for("recuperar_contrasena"))

        envio = _enviar_codigo_recuperacion(
            correo,
            usuario.get("nombre"),
            codigo
        )
        if not envio.get("ok"):
            flash(envio.get("mensaje"), "error")
            return redirect(url_for("recuperar_contrasena"))

        session["recuperacion_matricula"] = usuario.get("matricula")
        session["recuperacion_correo"] = _correo_oculto(correo)
        flash("Enviamos un codigo a " + _correo_oculto(correo), "success")
        return redirect(url_for("restablecer_contrasena"))

    return render_template(
        "recuperar_contrasena.html",
        page_title="Recuperar contrasena"
    )


@app.route("/restablecer-contrasena", methods=["GET", "POST"],
           endpoint="restablecer_contrasena")
def restablecer_contrasena():
    matricula = session.get("recuperacion_matricula", "")
    if not matricula:
        flash("Primero solicite un codigo de recuperacion.", "error")
        return redirect(url_for("recuperar_contrasena"))

    if request.method == "POST":
        codigo = request.form.get("codigo", "").strip()
        password = request.form.get("password", "").strip()
        confirmar = request.form.get("confirmar", "").strip()

        if not re.fullmatch(r"\d{6}", codigo):
            flash("Ingrese el codigo de 6 digitos enviado al correo.", "error")
            return redirect(url_for("restablecer_contrasena"))
        if len(password) < 6:
            flash("La nueva contrasena debe tener al menos 6 caracteres.", "error")
            return redirect(url_for("restablecer_contrasena"))
        if password != confirmar:
            flash("La confirmacion no coincide con la nueva contrasena.", "error")
            return redirect(url_for("restablecer_contrasena"))

        resultado = actualizar_password_con_codigo(matricula, codigo, password)
        if resultado.get("ok"):
            session.pop("recuperacion_matricula", None)
            session.pop("recuperacion_correo", None)
            flash("Contrasena actualizada. Ya puede iniciar sesion.", "success")
            return redirect(url_for("login"))

        flash(resultado.get("mensaje"), "error")
        return redirect(url_for("restablecer_contrasena"))

    return render_template(
        "restablecer_contrasena.html",
        page_title="Restablecer contrasena",
        correo=session.get("recuperacion_correo", "")
    )


@app.route("/logout", endpoint="logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ============================================================
# RUTAS WEB - COLEGIADO
# ============================================================

@app.route("/dashboard", endpoint="dashboard")
def dashboard():
    try:
        ctx = contexto_base("Mi Panel", "dashboard")
        matricula = session.get("profile", {}).get("matricula", "")
        cuotas = leer_cuotas(matricula) or []
        deuda = sum(_monto(q.get("monto")) for q in cuotas if q.get("estado") == "Pendiente")
        pagadas = [q for q in cuotas if q.get("estado") == "Pagado"]
        pendientes = [q for q in cuotas if q.get("estado") == "Pendiente"]
        cursos = leer_cursos_colegiado(matricula) or []
        dashboard_courses = []
        materiales_disponibles = 0
        certificados_disponibles = 0
        total_progreso = 0

        for curso in cursos:
            total_progreso += int(curso.get("progreso") or 0)
            if (
                int(curso.get("progreso") or 0) >= 100
                and curso.get("estado_pago") == "Pagado"
                and curso.get("certificado")
            ):
                certificados_disponibles += 1

            materiales = leer_contenidos_curso(curso.get("id")) or []
            materiales_disponibles += len(materiales)

            dashboard_courses.append({
                "titulo": curso.get("titulo"),
                "categoria": curso.get("categoria"),
                "progreso": int(curso.get("progreso") or 0),
                "estado_pago": curso.get("estado_pago"),
                "inscripcion_id": curso.get("inscripcion_id"),
                "materiales": len(materiales),
            })

        promedio_cursos = round(total_progreso / len(cursos)) if cursos else 0
        ctx["status"] = "Vigente"
        ctx["saldo_pendiente"] = "S/ " + format(deuda, ".2f")
        ctx["ultimo_pago"] = (
            "S/ " + format(_monto(pagadas[0].get("monto")), ".2f")
            if pagadas else "Sin registros"
        )
        ctx["ultimo_recibo"] = "-"
        ctx["cuotas_pendientes"] = len(pendientes)
        ctx["cursos_inscritos"] = len(cursos)
        ctx["promedio_cursos"] = promedio_cursos
        ctx["materiales_disponibles"] = materiales_disponibles
        ctx["dashboard_courses"] = dashboard_courses[:4]
        ctx["certificados_disponibles"] = certificados_disponibles
        ctx["dashboard_cards"] = [
            {
                "endpoint": "estado_cuenta",
                "icon": "receipt_long",
                "title": "Estado de cuenta",
                "description": str(len(pendientes)) + " cuota(s) pendiente(s)."
            },
            {
                "endpoint": "educacion_continua",
                "icon": "school",
                "title": "Educacion continua",
                "description": str(len(cursos)) + " curso(s) inscrito(s)."
            },
            {
                "endpoint": "notificaciones",
                "icon": "notifications",
                "title": "Notificaciones",
                "description": "Avisos de pagos, cursos y certificados."
            },
            {
                "endpoint": "perfil_soporte",
                "icon": "support_agent",
                "title": "Perfil y soporte",
                "description": "Actualiza tus datos o registra un ticket."
            },
        ]
        return render_template("colegiado/dashboard.html", **ctx)
    except Exception as e:
        print("Error en /dashboard:", repr(e))
        return render_template("error500.html"), 500


@app.route("/notificaciones", endpoint="notificaciones")
def notificaciones():
    try:
        ctx = contexto_base("Notificaciones", "notificaciones")
        matricula = session.get("profile", {}).get("matricula", "")
        ctx["notifications"] = leer_notificaciones_colegiado(matricula) if matricula else []
        return render_template("colegiado/notificaciones.html", **ctx)
    except Exception as e:
        print("Error en /notificaciones:", repr(e))
        return render_template("error500.html"), 500


@app.route("/notificaciones/mark-read", methods=["POST"], endpoint="notificacion_marcar_leida")
def notificacion_marcar_leida():
    matricula = session.get("profile", {}).get("matricula", "")
    data = request.get_json(silent=True) or {}
    notif_id = request.form.get("id") or data.get("id")
    if not matricula or not notif_id:
        return jsonify({"ok": False, "message": "Datos incompletos"}), 400
    ok = marcar_notificacion_leida(notif_id, matricula)
    return jsonify({"ok": ok})


@app.route("/notificaciones/clear-read", methods=["POST"], endpoint="notificaciones_limpiar_leidas")
def notificaciones_limpiar_leidas():
    matricula = session.get("profile", {}).get("matricula", "")
    if not matricula:
        return jsonify({"ok": False, "message": "Sesion no valida"}), 400
    ok = eliminar_notificaciones_leidas(matricula)
    return jsonify({"ok": ok})


@app.route("/estado-cuenta", endpoint="estado_cuenta")
def estado_cuenta():
    try:
        ctx = contexto_base("Estado de Cuenta", "estado_cuenta")
        matricula = session.get("profile", {}).get("matricula", "")
        cuotas = leer_cuotas(matricula) or []
        evidencias = leer_evidencias_pago(matricula) or []
        comprobantes = leer_comprobantes_pago_colegiado(matricula) or []
        evidencias_por_cuota = {
            e.get("cuota_id"): e
            for e in evidencias
            if e.get("estado") == "Pendiente"
        }
        comprobantes_por_cuota = {
            c.get("cuota_id"): c
            for c in comprobantes
        }
        deuda = sum(_monto(q.get("monto")) for q in cuotas if q.get("estado") == "Pendiente")
        pagadas = [q for q in cuotas if q.get("estado") == "Pagado"]
        pendientes = [q for q in cuotas if q.get("estado") == "Pendiente"]
        ctx["deuda_total"] = "S/ " + format(deuda, ".2f")
        ctx["ultimo_pago"] = (
            "S/ " + format(_monto(pagadas[0].get("monto")), ".2f")
            if pagadas else "Sin pagos"
        )
        ctx["proximo_vencimiento"] = pendientes[-1]["fecha"] if pendientes else "Sin pendientes"
        ctx["account_movements"] = [
            {
                "id": q.get("id"),
                "fecha": q.get("fecha"),
                "concepto": q.get("concepto"),
                "monto": format(_monto(q.get("monto")), ".2f"),
                "estado": q.get("estado"),
                "evidencia": evidencias_por_cuota.get(q.get("id")),
                "comprobante": comprobantes_por_cuota.get(q.get("id")),
            }
            for q in cuotas
        ]
        ctx["medios_pago"] = leer_medios_pago(True) or []
        ctx["mercado_pago"] = obtener_configuracion_mercado_pago() or {}
        ctx["evidencias_pago"] = evidencias
        ctx["comprobantes_pago"] = comprobantes
        return render_template("colegiado/estado_cuenta.html", **ctx)
    except Exception as e:
        print("Error en /estado-cuenta:", repr(e))
        return render_template("error500.html"), 500


@app.route("/pagos", endpoint="colegiado_pagos")
def colegiado_pagos():
    try:
        ctx = contexto_base("Pagos", "colegiado_pagos")
        matricula = session.get("profile", {}).get("matricula", "")
        cuotas = leer_cuotas(matricula) or []
        evidencias = leer_evidencias_pago(matricula) or []
        comprobantes = leer_comprobantes_pago_colegiado(matricula) or []
        evidencias_por_cuota = {
            e.get("cuota_id"): e
            for e in evidencias
            if e.get("estado") == "Pendiente"
        }
        pendientes = []
        vencidas = 0
        hoy_iso = date.today().isoformat()
        for cuota in cuotas:
            if cuota.get("estado") != "Pendiente":
                continue
            vencimiento = cuota.get("fecha_vencimiento") or cuota.get("fecha")
            vencida = bool(vencimiento and str(vencimiento) < hoy_iso)
            if vencida:
                vencidas += 1
            pendientes.append({
                "id": cuota.get("id"),
                "fecha": cuota.get("fecha"),
                "fecha_vencimiento": vencimiento,
                "concepto": cuota.get("concepto"),
                "tipo": cuota.get("tipo"),
                "monto": format(_monto(cuota.get("monto")), ".2f"),
                "vencida": vencida,
                "evidencia": evidencias_por_cuota.get(cuota.get("id")),
            })

        ctx["pendientes"] = pendientes
        ctx["deuda_total"] = sum(_monto(q.get("monto")) for q in cuotas if q.get("estado") == "Pendiente")
        ctx["vencidas"] = vencidas
        ctx["en_revision"] = len(evidencias_por_cuota)
        ctx["medios_pago"] = leer_medios_pago(True) or []
        ctx["mercado_pago"] = obtener_configuracion_mercado_pago() or {}
        ctx["metodos_internos"] = METODOS_PAGO_INTERNO
        ctx["comprobantes_pago"] = comprobantes
        ctx["pago_adelantado"] = obtener_configuracion_cuotas_colegiado()
        ctx["pago_anual"] = obtener_configuracion_pago_anual_colegiado()
        return render_template("colegiado/pagos.html", **ctx)
    except Exception as e:
        print("Error en /pagos:", repr(e))
        return render_template("error500.html"), 500


@app.route("/pagos/adelantar-cuotas",
           methods=["POST"], endpoint="colegiado_adelantar_cuotas")
def colegiado_adelantar_cuotas():
    try:
        matricula = session.get("profile", {}).get("matricula", "")
        anio = request.form.get("anio", str(date.today().year)).strip()
        mes_inicio = request.form.get("mes_inicio", str(date.today().month)).strip()
        cantidad_meses = request.form.get("cantidad_meses", "1").strip()

        if not matricula:
            return mostrar_error("No se encontro la matricula del colegiado.")

        resultado = generar_cuotas_adelantadas_colegiado(
            matricula, anio, mes_inicio, cantidad_meses
        )
        if resultado.get("ok"):
            _notificar_colegiado(
                matricula,
                "cuota",
                "Cuotas adelantadas generadas",
                "Se generaron " + str(resultado.get("generadas", 0)) +
                " cuota(s) nuevas para pago adelantado.",
                "colegiado_pagos",
                "Ver pagos",
                "cuota",
                None
            )
            mensaje = (
                "Cuotas adelantadas listas para pagar. "
                f"Nuevas: {resultado.get('generadas', 0)}. "
                f"Ya pendientes: {resultado.get('existentes', 0)}. "
                f"Ya pagadas: {resultado.get('ya_pagadas', 0)}."
            )
            return mostrar_exito(mensaje, "colegiado_pagos", "Ver pagos")
        return mostrar_error(resultado.get("mensaje", "No se pudieron generar las cuotas."))
    except Exception as e:
        print("Error en /pagos/adelantar-cuotas:", repr(e))
        return render_template("error500.html"), 500


@app.route("/pagos/pago-anual",
           methods=["POST"], endpoint="colegiado_generar_pago_anual")
def colegiado_generar_pago_anual():
    try:
        matricula = session.get("profile", {}).get("matricula", "")
        anio = request.form.get("anio", str(date.today().year)).strip()
        if not matricula:
            return mostrar_error("No se encontro la matricula del colegiado.")

        resultado = generar_cuotas_anuales_colegiado(matricula, anio)
        if resultado.get("ok"):
            _notificar_colegiado(
                matricula,
                "cuota",
                "Pago anual habilitado",
                "Se generaron las cuotas del anio " +
                str(resultado.get("anio")) + " con " +
                str(resultado.get("descuento", 0)) + "% de descuento.",
                "colegiado_pagos",
                "Ver pagos",
                "cuota",
                None
            )
            mensaje = (
                "Pago anual con descuento listo para pagar. "
                f"Nuevas: {resultado.get('generadas', 0)}. "
                f"Actualizadas: {resultado.get('actualizadas', 0)}. "
                f"Total anual: S/ {format(_monto(resultado.get('monto_total')), '.2f')}."
            )
            return mostrar_exito(mensaje, "colegiado_pagos", "Ver pagos")
        return mostrar_error(resultado.get("mensaje", "No se pudo generar el pago anual."))
    except Exception as e:
        print("Error en /pagos/pago-anual:", repr(e))
        return render_template("error500.html"), 500


@app.route("/estado-cuenta/evidencia", methods=["POST"], endpoint="colegiado_registrar_evidencia_pago")
def colegiado_registrar_evidencia_pago():
    try:
        matricula = session.get("profile", {}).get("matricula", "")
        cuota_id = request.form.get("cuota_id", "").strip()
        medio_pago_id = request.form.get("medio_pago_id", "").strip()
        fecha_pago = request.form.get("fecha_pago", "").strip()
        numero_operacion = request.form.get("numero_operacion", "").strip()
        monto = request.form.get("monto", "").strip()
        comentario = request.form.get("comentario", "").strip()
        archivo_evidencia = request.files.get("archivo_evidencia")

        if not matricula:
            return mostrar_error("No se encontro la matricula del colegiado.")
        if not all([cuota_id, medio_pago_id, fecha_pago, numero_operacion, monto]):
            return mostrar_error("Complete los datos obligatorios de la evidencia.")
        if not archivo_evidencia or not archivo_evidencia.filename:
            return mostrar_error("Adjunte el voucher o evidencia del pago.")

        try:
            cuota_id_num = int(cuota_id)
            medio_pago_id_num = int(medio_pago_id)
            monto_num = float(monto)
        except ValueError:
            return mostrar_error("Seleccione datos validos para registrar la evidencia.")

        if monto_num <= 0:
            return mostrar_error("El monto pagado debe ser mayor a 0.")
        if not _leer_fecha_iso(fecha_pago):
            return mostrar_error("Ingrese una fecha de pago valida.")

        archivo_guardado = _guardar_archivo_subido(archivo_evidencia,
                                                   "evidencias",
                                                   EXTENSIONES_ARCHIVO)
        if archivo_guardado is None:
            return mostrar_error("La evidencia debe ser una imagen o PDF.")

        resultado = registrar_evidencia_pago(matricula, cuota_id_num,
                                             medio_pago_id_num,
                                             numero_operacion, fecha_pago,
                                             monto_num, comentario,
                                             archivo_guardado)
        if resultado == "ok":
            volver = request.form.get("volver_endpoint", "estado_cuenta").strip()
            if volver not in ["estado_cuenta", "colegiado_pagos"]:
                volver = "estado_cuenta"
            return mostrar_exito("La evidencia de pago fue registrada para revision.",
                                 volver,
                                 "Ver pagos" if volver == "colegiado_pagos" else "Ver estado")
        return mostrar_error(resultado)
    except Exception as e:
        print("Error en /estado-cuenta/evidencia:", repr(e))
        return render_template("error500.html"), 500


@app.route("/estado-cuenta/pagar/<int:cuota_id>", endpoint="colegiado_pasarela_demo")
def colegiado_pasarela_demo(cuota_id):
    try:
        matricula = session.get("profile", {}).get("matricula", "")
        cuota = leer_cuota_pago_demo(cuota_id, matricula)
        if not cuota:
            return mostrar_error("La cuota seleccionada no pertenece al colegiado.")
        if cuota.get("estado") != "Pendiente":
            return mostrar_error("Esta cuota no esta pendiente de pago.")

        ctx = contexto_base("Pago interno CCPL", "estado_cuenta")
        ctx["cuota"] = cuota
        ctx["metodos_internos"] = METODOS_PAGO_INTERNO
        return render_template("colegiado/pasarela_demo.html", **ctx)
    except Exception as e:
        print("Error en /estado-cuenta/pagar:", repr(e))
        return render_template("error500.html"), 500


@app.route("/estado-cuenta/pagar/<int:cuota_id>/confirmar",
           methods=["POST"], endpoint="colegiado_confirmar_pago_demo")
def colegiado_confirmar_pago_demo(cuota_id):
    try:
        matricula = session.get("profile", {}).get("matricula", "")
        metodo = request.form.get("metodo_pago", "").strip()
        if not matricula:
            return mostrar_error("No se encontro la matricula del colegiado.")
        if metodo not in METODOS_PAGO_INTERNO:
            return mostrar_error("Seleccione un metodo de pago valido.")

        resultado = registrar_pago_demo_colegiado(cuota_id, matricula, metodo)
        if not resultado.get("ok"):
            return mostrar_error(resultado.get("mensaje", "No se pudo procesar el pago."))

        _notificar_colegiado(
            matricula,
            "cuota",
            "Pago registrado",
            "Tu pago fue aprobado por el pago interno del CCPL.",
            "estado_cuenta",
            "Ver estado de cuenta",
            "cuota",
            cuota_id
        )
        flash("Pago aprobado. Se genero el comprobante interno.", "success")
        return redirect(url_for(
            "colegiado_comprobante_pago",
            comprobante_id=resultado["comprobante_id"]
        ))
    except Exception as e:
        print("Error en /estado-cuenta/pagar/confirmar:", repr(e))
        return render_template("error500.html"), 500


@app.route("/pagos/mercado-pago/<int:cuota_id>",
           methods=["POST"], endpoint="colegiado_crear_pago_mercado_pago")
def colegiado_crear_pago_mercado_pago(cuota_id):
    try:
        matricula = session.get("profile", {}).get("matricula", "")
        if not matricula:
            return mostrar_error("No se encontro la matricula del colegiado.")

        resultado = crear_preferencia_mercado_pago(
            cuota_id,
            matricula,
            request.host_url.rstrip("/")
        )
        if not resultado.get("ok"):
            return mostrar_error(resultado.get("mensaje", "No se pudo iniciar Mercado Pago."))
        return redirect(resultado.get("url_pago"))
    except Exception as e:
        print("Error en /pagos/mercado-pago:", repr(e))
        return render_template("error500.html"), 500


@app.route("/pagos/mercado-pago/retorno",
           endpoint="colegiado_retorno_mercado_pago")
def colegiado_retorno_mercado_pago():
    try:
        payment_id = (
            request.args.get("payment_id")
            or request.args.get("collection_id")
            or ""
        )
        external_reference = request.args.get("external_reference", "")
        status = request.args.get("status") or request.args.get("collection_status")

        if payment_id:
            resultado = confirmar_pago_mercado_pago(payment_id, external_reference)
            if resultado.get("ok"):
                _notificar_colegiado(
                    session.get("profile", {}).get("matricula", ""),
                    "cuota",
                    "Pago Mercado Pago confirmado",
                    "Tu pago fue aprobado por Mercado Pago.",
                    "estado_cuenta",
                    "Ver estado de cuenta",
                    "cuota",
                    None
                )
                if resultado.get("comprobante_id"):
                    flash("Pago Mercado Pago aprobado. Se genero comprobante interno.", "success")
                    return redirect(url_for(
                        "colegiado_comprobante_pago",
                        comprobante_id=resultado["comprobante_id"]
                    ))
                flash("Pago Mercado Pago aprobado.", "success")
            else:
                flash(resultado.get("mensaje", "El pago no fue aprobado."), "warning")
        elif status:
            flash("Mercado Pago devolvio estado: " + str(status) + ".", "warning")
        else:
            flash("No se recibio informacion suficiente de Mercado Pago.", "warning")

        return redirect(url_for("colegiado_pagos"))
    except Exception as e:
        print("Error en /pagos/mercado-pago/retorno:", repr(e))
        return render_template("error500.html"), 500


@app.route("/pagos/mercado-pago/webhook",
           methods=["GET", "POST"], endpoint="mercado_pago_webhook")
def mercado_pago_webhook():
    try:
        data = request.get_json(silent=True) or {}
        payment_id = (
            request.args.get("id")
            or request.args.get("data.id")
            or str((data.get("data") or {}).get("id") or "")
        )
        topic = request.args.get("topic") or request.args.get("type") or data.get("type")
        if payment_id and topic in ["payment", "payments", None, ""]:
            confirmar_pago_mercado_pago(payment_id)
        return jsonify({"ok": True})
    except Exception as e:
        print("Error en webhook Mercado Pago:", repr(e))
        return jsonify({"ok": False}), 500


@app.route("/estado-cuenta/comprobante/<int:comprobante_id>",
           endpoint="colegiado_comprobante_pago")
def colegiado_comprobante_pago(comprobante_id):
    try:
        matricula = session.get("profile", {}).get("matricula", "")
        comprobante = leer_comprobante_pago_colegiado(comprobante_id, matricula)
        if not comprobante:
            return mostrar_error("No se encontro el comprobante solicitado.", 404)

        ctx = contexto_base("Comprobante de Pago", "estado_cuenta")
        ctx["comprobante"] = comprobante
        ctx["numero_comprobante"] = (
            str(comprobante.get("serie") or "") + "-" +
            str(comprobante.get("numero") or 0).zfill(8)
        )
        return render_template("colegiado/comprobante_pago.html", **ctx)
    except Exception as e:
        print("Error en /estado-cuenta/comprobante:", repr(e))
        return render_template("error500.html"), 500


@app.route("/educacion-continua", endpoint="educacion_continua")
def educacion_continua():
    try:
        ctx = contexto_base("Educación Continua", "educacion_continua")
        matricula = session.get("profile", {}).get("matricula", "")
        colegiado = leer_colegiado_por_matricula(matricula) or {}
        ctx["epc_points"] = colegiado.get("epc_points", 0) or 0
        ctx["epc_target"] = 100
        ctx["courses"] = []
        total_cursos = 0
        total_progreso = 0
        total_materiales = 0
        certificados_disponibles = 0
        for curso in (leer_cursos_colegiado(matricula) or []):
            materiales = [
                {
                    "title": material.get("titulo", ""),
                    "description": material.get("descripcion", ""),
                    "link": material.get("enlace", ""),
                    "file": material.get("archivo", ""),
                }
                for material in (leer_contenidos_curso(curso.get("id")) or [])
            ]
            ctx["courses"].append({
                "id": curso.get("id"),
                "inscription_id": curso.get("inscripcion_id"),
                "category": curso.get("categoria", ""),
                "title": curso.get("titulo", ""),
                "description": curso.get("descripcion", ""),
                "date": curso.get("fecha_evento", ""),
                "amount": curso.get("precio_aplicado", curso.get("monto", 0)) or 0,
                "amount_habil": curso.get("monto", 0) or 0,
                "amount_inhabil": curso.get("monto_inhabil", curso.get("monto", 0)) or 0,
                "price_condition": curso.get("condicion_precio", "Habil"),
                "speaker": curso.get("ponente", ""),
                "modality": curso.get("modalidad", ""),
                "hours": curso.get("duracion_horas", 0) or 0,
                "progress": curso.get("progreso", 0),
                "badge": curso.get("estado_pago", "Pendiente"),
                "certificate": curso.get("certificado", ""),
                "materials": materiales,
                "material_count": len(materiales),
            })
            total_cursos += 1
            total_progreso += int(curso.get("progreso") or 0)
            total_materiales += len(materiales)
            if (
                int(curso.get("progreso") or 0) >= 100
                and curso.get("estado_pago") == "Pagado"
                and curso.get("certificado")
            ):
                certificados_disponibles += 1
        promedio_general = round(total_progreso / total_cursos) if total_cursos else 0
        ctx["education_summary"] = {
            "total_cursos": total_cursos,
            "promedio_general": promedio_general,
            "total_materiales": total_materiales,
            "certificados_disponibles": certificados_disponibles,
        }
        ctx["available_courses"] = [
            {
                "id": curso.get("id"),
                "category": curso.get("categoria", ""),
                "title": curso.get("titulo", ""),
                "description": curso.get("descripcion", ""),
                "date": curso.get("fecha_evento", ""),
                "amount": curso.get("monto", 0) or 0,
                "speaker": curso.get("ponente", ""),
                "modality": curso.get("modalidad", ""),
                "hours": curso.get("duracion_horas", 0) or 0,
                "cupos": curso.get("cupos", 0) or 0,
                "inscritos": curso.get("inscritos", 0) or 0,
            }
            for curso in (leer_cursos_disponibles_colegiado(matricula) or [])
        ]
        return render_template("colegiado/educacion_continua.html", **ctx)
    except Exception as e:
        print("Error en /educacion-continua:", repr(e))
        return render_template("error500.html"), 500


@app.route("/educacion-continua/cursos/<int:inscripcion_id>",
           endpoint="colegiado_aula_curso")
def colegiado_aula_curso(inscripcion_id):
    try:
        matricula = session.get("profile", {}).get("matricula", "")
        if not matricula:
            return redirect(url_for("login"))

        curso = leer_curso_inscrito_colegiado(inscripcion_id, matricula)
        if not curso:
            return mostrar_error("No se encontro el curso inscrito.", 404)

        ctx = contexto_base("Aula del Curso", "educacion_continua")
        ctx["curso"] = curso
        materiales = _armar_materiales_aula(curso.get("id"))
        puede_certificado = _puede_ver_certificado(curso)
        ctx["materiales"] = materiales
        ctx["puede_certificado"] = puede_certificado
        ctx["resumen_aula"] = _resumen_aula_colegiado(
            materiales, curso, puede_certificado
        )
        return render_template("colegiado/aula_curso.html", **ctx)
    except Exception as e:
        print("Error en /educacion-continua/cursos:", repr(e))
        return render_template("error500.html"), 500


@app.route("/educacion-continua/inscribirme", methods=["POST"], endpoint="colegiado_inscribirse_curso")
def colegiado_inscribirse_curso():
    try:
        matricula = session.get("profile", {}).get("matricula", "")
        curso_id = request.form.get("curso_id", "").strip()
        if not matricula:
            return mostrar_error("No se encontro la matricula del colegiado.")
        try:
            curso_id_num = int(curso_id)
        except ValueError:
            return mostrar_error("Seleccione un curso valido.")

        mensaje = validar_inscripcion_curso(matricula, curso_id_num)
        if mensaje:
            return mostrar_error(mensaje)

        if insertar_inscripcion_curso(matricula, curso_id_num, "Pendiente"):
            curso = leer_curso_por_id(curso_id_num) or {}
            titulo = curso.get("titulo", "curso seleccionado")
            _notificar_colegiado(
                matricula,
                "curso",
                "Inscripcion registrada",
                "Tu inscripcion al curso " + titulo + " fue registrada.",
                "educacion_continua",
                "Ver curso",
                "curso",
                curso_id_num
            )
            _notificar_colegiado(
                matricula,
                "cuota",
                "Cuota de curso generada",
                "Se genero una cuota pendiente por el curso " + titulo + ".",
                "estado_cuenta",
                "Ver pago",
                "curso",
                curso_id_num
            )
            return mostrar_exito("Inscripcion registrada. Se genero una cuota pendiente por el curso.",
                                 "educacion_continua",
                                 "Ver mis cursos")
        return mostrar_error("No se pudo completar la inscripcion al curso.")
    except Exception as e:
        print("Error en /educacion-continua/inscribirme:", repr(e))
        return render_template("error500.html"), 500


@app.route("/educacion-continua/<int:inscripcion_id>/finalizar",
           methods=["POST"], endpoint="colegiado_finalizar_curso")
def colegiado_finalizar_curso(inscripcion_id):
    try:
        return mostrar_error("El progreso del curso lo actualiza el ponente.")
    except Exception as e:
        print("Error en /educacion-continua/finalizar:", repr(e))
        return render_template("error500.html"), 500


@app.route("/educacion-continua/<int:inscripcion_id>/certificado",
           endpoint="colegiado_certificado_curso")
def colegiado_certificado_curso(inscripcion_id):
    try:
        matricula = session.get("profile", {}).get("matricula", "")
        if not matricula:
            return mostrar_error("Debe iniciar sesion como colegiado.")

        certificado = leer_certificado_curso_colegiado(inscripcion_id, matricula)
        if not certificado:
            return mostrar_error("No se encontro el certificado del curso.", 404)
        if certificado.get("estado_pago") != "Pagado":
            return mostrar_error("No se puede emitir certificado porque el pago esta pendiente.")
        if int(certificado.get("progreso") or 0) < 100:
            return mostrar_error("Debe finalizar el curso para emitir el certificado.")
        if not certificado.get("certificado"):
            return mostrar_error("El certificado aun no fue registrado por el administrador.")

        ctx = contexto_base("Certificado de Curso", "educacion_continua")
        ctx["certificado"] = certificado
        archivo_certificado = certificado.get("certificado", "") or ""
        ctx["certificado_archivo"] = (
            archivo_certificado
            if _archivo_estatico_existe(archivo_certificado)
            else ""
        )
        ctx["certificado_nombre"] = (
            archivo_certificado.rsplit("/", 1)[-1] if archivo_certificado else ""
        )
        return render_template("colegiado/certificado_curso.html", **ctx)
    except Exception as e:
        print("Error en /educacion-continua/certificado:", repr(e))
        return render_template("error500.html"), 500


@app.route("/constancia", endpoint="constancia")
def constancia():
    flash("El certificado de habilidad ahora se solicita desde Tramites.", "warning")
    return redirect(url_for("tramites"))


@app.route("/perfil-soporte", endpoint="perfil_soporte")
def perfil_soporte():
    try:
        ctx = contexto_base("Perfil y Soporte", "perfil_soporte")
        matricula = session.get("profile", {}).get("matricula", "")
        colegiado = leer_colegiado_por_matricula(matricula) or {}
        ctx["profile"] = {
            "nombre":      colegiado.get("nombre",      session.get("profile", {}).get("nombre", "")),
            "matricula":   colegiado.get("matricula",   matricula),
            "documento":   colegiado.get("documento",   ""),
            "especialidad":colegiado.get("especialidad",""),
            "correo":      colegiado.get("correo",      ""),
            "telefono":    colegiado.get("telefono",    ""),
        }
        ctx["support_documents"] = []
        ctx["tickets"] = leer_tickets_colegiado(matricula) if matricula else []
        return render_template("colegiado/perfil_soporte.html", **ctx)
    except Exception as e:
        print("Error en /perfil-soporte:", repr(e))
        return render_template("error500.html"), 500


@app.route("/documentos/<path:nombre>", endpoint="descargar_doc")
def descargar_doc(nombre):
    return mostrar_error("El documento solicitado no esta disponible.", 404)


@app.route("/perfil/actualizar", methods=["POST"], endpoint="perfil_actualizar")
def perfil_actualizar():
    try:
        matricula = session.get("profile", {}).get("matricula", "")
        if not matricula:
            return mostrar_error("Debe iniciar sesion como colegiado.")

        correo      = request.form.get("correo", "").strip()
        telefono    = request.form.get("telefono", "").strip()
        especialidad = request.form.get("especialidad", "").strip()

        if correo and not _validar_correo(correo):
            return mostrar_error("Ingrese un correo electrónico válido.")
        if not _validar_telefono_peru(telefono):
            return mostrar_error("El teléfono debe tener 9 dígitos y comenzar con 9 (ej: 987654321).")

        if actualizar_perfil_colegiado(matricula, correo, telefono, especialidad):
            return mostrar_exito("Sus datos fueron actualizados correctamente.",
                                 "perfil_soporte", "Ver perfil")
        return mostrar_error("No se pudo actualizar el perfil.")
    except Exception as e:
        print("Error en /perfil/actualizar:", repr(e))
        return render_template("error500.html"), 500


@app.route("/soporte/ticket", methods=["POST"], endpoint="soporte_ticket")
def soporte_ticket():
    try:
        matricula = session.get("profile", {}).get("matricula", "")
        if not matricula:
            return mostrar_error("Debe iniciar sesion para enviar un ticket.")

        categoria   = request.form.get("categoria", "otro").strip()
        asunto      = request.form.get("asunto", "").strip()
        descripcion = request.form.get("descripcion", "").strip()

        if not asunto or not descripcion:
            return mostrar_error("El asunto y la descripción son obligatorios.")

        if insertar_ticket(matricula, categoria, asunto, descripcion):
            insertar_notificacion_matricula(
                matricula,
                "ticket",
                "Ticket registrado",
                "Tu incidencia fue enviada al area de soporte.",
                "perfil_soporte",
                "Ver ticket",
                "ticket",
                None
            )
            return mostrar_exito("La incidencia fue enviada. El equipo de soporte la atenderá pronto.",
                                 "perfil_soporte", "Ver perfil")
        return mostrar_error("No se pudo enviar la incidencia.")
    except Exception as e:
        print("Error en /soporte/ticket:", repr(e))
        return render_template("error500.html"), 500


@app.route("/tramites", methods=["GET", "POST"], endpoint="tramites")
def tramites():
    try:
        ctx = contexto_base("Tramites", "tramites")
        profile = session.get("profile", {})
        matricula = profile.get("matricula", "")
        nombre = profile.get("nombre", "")

        if request.method == "POST":
            if not matricula or not nombre:
                return mostrar_error("Debe iniciar sesion como colegiado para enviar un tramite.")

            tipo_tramite = request.form.get("tipo_tramite", "").strip()
            asunto = request.form.get("asunto", "").strip()
            descripcion = request.form.get("descripcion", "").strip()
            archivo = request.files.get("documento")

            tipos_validos = [t["codigo"] for t in leer_tipos_tramite()]
            if tipo_tramite not in tipos_validos:
                return mostrar_error("Seleccione un tipo de tramite valido.")
            if not asunto or not descripcion:
                return mostrar_error("Complete los campos obligatorios del tramite.")
            if tramite_requiere_sustento(tipo_tramite) and (
                not archivo or not archivo.filename
            ):
                return mostrar_error("Para baja o traslado debe adjuntar el documento sustentatorio.")

            archivo_solicitud = _guardar_archivo_subido(
                archivo,
                "tramites",
                EXTENSIONES_ARCHIVO
            )
            if archivo_solicitud is None:
                return mostrar_error("El documento adjunto debe ser una imagen o PDF.")

            obj = clsTramite(0, matricula, nombre, tipo_tramite, asunto,
                             descripcion, archivo_solicitud, "Pendiente",
                             date.today())
            if insertar_tramite(obj):
                insertar_notificacion_matricula(
                    matricula,
                    "sistema",
                    "Tramite registrado",
                    "Tu tramite fue registrado y quedo pendiente de revision.",
                    "tramites",
                    "Ver tramite",
                    "tramite",
                    None
                )
                return mostrar_exito("El tramite fue registrado correctamente.",
                                     "tramites",
                                     "Ver tramites")
            return mostrar_error("No se pudo registrar el tramite. Verifique que la tabla tramites exista.")

        ctx["tipos_tramite"] = leer_tipos_tramite()
        ctx["tramites_previos"] = []
        if matricula:
            ctx["tramites_previos"] = leer_tramites(p_matricula=matricula) or []
            for tramite in ctx["tramites_previos"]:
                tramite["archivo_respuesta_existe"] = _archivo_estatico_existe(
                    tramite.get("archivo_respuesta")
                )
                tramite["archivo_solicitud_existe"] = _archivo_estatico_existe(
                    tramite.get("archivo_solicitud")
                )
        return render_template("colegiado/tramites.html", **ctx)
    except Exception as e:
        print("Error en /tramites:", repr(e))
        return render_template("error500.html")


@app.route("/tramites/<int:tid>/validar-firma", endpoint="validar_firma_tramite")
def validar_firma_tramite(tid):
    try:
        tramite = leer_tramite_por_id(tid)
        if not tramite:
            return mostrar_error("El tramite seleccionado no existe.", 404)

        matricula = session.get("profile", {}).get("matricula", "")
        if tramite.get("matricula") != matricula:
            return mostrar_error("No tiene permiso para validar este documento.", 403)

        return _render_validacion_firma_tramite(tid, es_admin=False)
    except Exception as e:
        print("Error en /tramites/validar-firma:", repr(e))
        return render_template("error500.html"), 500


# ============================================================
# RUTAS WEB - PONENTE
# ============================================================

def _nombre_ponente_actual():
    if session.get("rol") != "ponente":
        return ""
    return session.get("profile", {}).get("nombre", "")


@app.route("/ponente", endpoint="ponente_dashboard")
def ponente_dashboard():
    try:
        ponente = _nombre_ponente_actual()
        if not ponente:
            return redirect(url_for("login"))

        cursos = leer_cursos_ponente(ponente) or []
        total_inscritos = sum(int(c.get("inscritos") or 0) for c in cursos)
        total_materiales = sum(int(c.get("total_materiales") or 0) for c in cursos)
        activos = len([c for c in cursos if c.get("estado") == "Activo"])
        finalizados = len([c for c in cursos if c.get("estado") != "Activo"])
        promedio = 0
        if cursos:
            promedio = sum(float(c.get("progreso_promedio") or 0) for c in cursos) / len(cursos)

        resumen_seguimiento = resumir_seguimiento_ponente(ponente) or {}
        acciones_ponente = []
        for curso in cursos:
            if int(curso.get("total_materiales") or 0) == 0:
                acciones_ponente.append({
                    "icono": "upload_file",
                    "titulo": "Subir material",
                    "detalle": "Agrega material de apoyo para " +
                               str(curso.get("titulo")) + ".",
                    "curso_id": curso.get("id"),
                })
            if int(curso.get("inscritos") or 0) > 0 and float(curso.get("progreso_promedio") or 0) < 50:
                acciones_ponente.append({
                    "icono": "monitoring",
                    "titulo": "Revisar progreso",
                    "detalle": "Promedio bajo en " + str(curso.get("titulo")) +
                               ": " + str(round(float(curso.get("progreso_promedio") or 0))) + "%.",
                    "curso_id": curso.get("id"),
                })
        acciones_ponente = acciones_ponente[:6]

        ctx = contexto_base("Panel de Ponente", "ponente_dashboard", es_ponente=True)
        ctx["cursos"] = cursos
        ctx["total_inscritos"] = total_inscritos
        ctx["total_materiales"] = total_materiales
        ctx["total_activos"] = activos
        ctx["total_finalizados"] = finalizados
        ctx["promedio_general"] = round(promedio)
        ctx["resumen_seguimiento"] = resumen_seguimiento
        ctx["acciones_ponente"] = acciones_ponente
        ctx["avisos_ponente"] = leer_notificaciones_ponente(ponente, p_limite=5) or []
        ctx["seguimiento_prioridad"] = leer_seguimiento_ponente(
            ponente,
            p_progreso="bajo",
            p_limite=5,
            p_offset=0
        ) or []
        return render_template("ponente/ponente_dashboard.html", **ctx)
    except Exception as e:
        print("Error en /ponente:", repr(e))
        return render_template("error500.html"), 500


@app.route("/ponente/seguimiento", endpoint="ponente_seguimiento")
def ponente_seguimiento():
    try:
        ponente = _nombre_ponente_actual()
        if not ponente:
            return redirect(url_for("login"))

        curso_id = request.args.get("curso_id", "").strip()
        estado_pago = request.args.get("estado_pago", "").strip()
        progreso = request.args.get("progreso", "").strip()
        busqueda = request.args.get("q", "").strip()
        pagina_texto = request.args.get("pagina", "1").strip()
        por_pagina_texto = request.args.get("por_pagina", "20").strip()

        estados_pago_validos = {"", "Pendiente", "Pagado"}
        progresos_validos = {"", "bajo", "en_proceso", "finalizado"}
        if estado_pago not in estados_pago_validos:
            estado_pago = ""
        if progreso not in progresos_validos:
            progreso = ""

        curso_id_num = int(curso_id) if curso_id.isdigit() else None
        pagina = int(pagina_texto) if pagina_texto.isdigit() else 1
        pagina = max(pagina, 1)
        por_pagina = int(por_pagina_texto) if por_pagina_texto.isdigit() else 20
        if por_pagina not in {10, 20, 50}:
            por_pagina = 20

        total = contar_seguimiento_ponente(
            ponente, curso_id_num, estado_pago, progreso, busqueda
        )
        total_paginas = max((total + por_pagina - 1) // por_pagina, 1)
        if pagina > total_paginas:
            pagina = total_paginas
        offset = (pagina - 1) * por_pagina

        seguimiento = leer_seguimiento_ponente(
            ponente, curso_id_num, estado_pago, progreso, busqueda,
            por_pagina, offset
        ) or []

        ctx = contexto_base("Seguimiento Academico", "ponente_seguimiento",
                            es_ponente=True)
        ctx["seguimiento"] = seguimiento
        ctx["cursos"] = leer_cursos_ponente(ponente) or []
        ctx["resumen_seguimiento"] = resumir_seguimiento_ponente(ponente) or {}
        ctx["filtro_curso_id"] = curso_id
        ctx["filtro_estado_pago"] = estado_pago
        ctx["filtro_progreso"] = progreso
        ctx["busqueda"] = busqueda
        ctx["pagina"] = pagina
        ctx["por_pagina"] = por_pagina
        ctx["total_paginas"] = total_paginas
        ctx["total_registros"] = total
        return render_template("ponente/ponente_seguimiento.html", **ctx)
    except Exception as e:
        print("Error en /ponente/seguimiento:", repr(e))
        return render_template("error500.html"), 500


@app.route("/ponente/avisos", endpoint="ponente_notificaciones")
def ponente_notificaciones():
    try:
        ponente = _nombre_ponente_actual()
        if not ponente:
            return redirect(url_for("login"))

        ctx = contexto_base("Avisos del Ponente", "ponente_notificaciones",
                            es_ponente=True)
        ctx["avisos"] = leer_notificaciones_ponente(ponente, p_limite=20) or []
        ctx["resumen_seguimiento"] = resumir_seguimiento_ponente(ponente) or {}
        return render_template("ponente/ponente_notificaciones.html", **ctx)
    except Exception as e:
        print("Error en /ponente/avisos:", repr(e))
        return render_template("error500.html"), 500


@app.route("/ponente/cursos/<int:curso_id>", endpoint="ponente_curso")
def ponente_curso(curso_id):
    try:
        ponente = _nombre_ponente_actual()
        if not ponente:
            return redirect(url_for("login"))

        curso = leer_curso_ponente(curso_id, ponente)
        if not curso:
            return mostrar_error("No se encontro el curso asignado al ponente.", 404)

        ctx = contexto_base("Curso del Ponente", "ponente_dashboard", es_ponente=True)
        ctx["curso"] = curso
        inscritos = leer_inscritos_curso_ponente(curso_id, ponente) or []
        materiales = _armar_materiales_aula(curso_id)
        ctx["inscritos"] = inscritos
        ctx["materiales"] = materiales
        ctx["resumen_aula"] = _resumen_aula_ponente(materiales, inscritos)
        return render_template("ponente/ponente_curso.html", **ctx)
    except Exception as e:
        print("Error en /ponente/cursos:", repr(e))
        return render_template("error500.html"), 500


@app.route("/ponente/cursos/<int:curso_id>/contenido",
           methods=["POST"], endpoint="ponente_actualizar_contenido")
def ponente_actualizar_contenido(curso_id):
    try:
        ponente = _nombre_ponente_actual()
        if not ponente:
            return redirect(url_for("login"))

        descripcion = request.form.get("descripcion", "").strip()
        if not descripcion:
            return mostrar_error("Ingrese el contenido del curso.")

        if actualizar_contenido_curso_ponente(curso_id, ponente, descripcion):
            flash("El contenido del curso fue actualizado.", "success")
            return redirect(url_for("ponente_curso", curso_id=curso_id))
        return mostrar_error("No se pudo actualizar el contenido del curso.")
    except Exception as e:
        print("Error en /ponente/cursos/contenido:", repr(e))
        return render_template("error500.html"), 500


@app.route("/ponente/cursos/<int:curso_id>/materiales",
           methods=["POST"], endpoint="ponente_agregar_material")
def ponente_agregar_material(curso_id):
    try:
        ponente = _nombre_ponente_actual()
        if not ponente:
            return redirect(url_for("login"))

        titulo = request.form.get("titulo", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        enlace = request.form.get("enlace", "").strip()
        archivo_material = request.files.get("archivo_material")

        if not titulo or not descripcion:
            return mostrar_error("Ingrese el titulo y la descripcion del material.")

        archivo_guardado = _guardar_archivo_subido(archivo_material,
                                                   "materiales",
                                                   EXTENSIONES_ARCHIVO)
        if archivo_guardado is None:
            return mostrar_error("El material debe ser una imagen o PDF.")

        obj = clsContenidoCurso(0, curso_id, titulo, descripcion,
                                enlace, archivo_guardado)
        if insertar_contenido_curso_ponente(curso_id, ponente, obj):
            curso = leer_curso_por_id(curso_id) or {}
            _notificar_inscritos_curso(
                curso_id,
                "curso",
                "Nuevo material publicado",
                "El ponente publico nuevo material en el curso " +
                str(curso.get("titulo", "")) + ": " + titulo + ".",
                "educacion_continua",
                "Ir al aula"
            )
            flash("El material del curso fue registrado.", "success")
            return redirect(url_for("ponente_curso", curso_id=curso_id))
        return mostrar_error("No se pudo registrar el material del curso.")
    except Exception as e:
        print("Error en /ponente/cursos/materiales:", repr(e))
        return render_template("error500.html"), 500


@app.route("/ponente/materiales/<int:material_id>/eliminar",
           methods=["POST"], endpoint="ponente_eliminar_material")
def ponente_eliminar_material(material_id):
    try:
        ponente = _nombre_ponente_actual()
        if not ponente:
            return redirect(url_for("login"))

        curso_id = request.form.get("curso_id", "").strip()
        if eliminar_contenido_curso_ponente(material_id, ponente):
            flash("El material fue eliminado.", "warning")
            if curso_id.isdigit():
                return redirect(url_for("ponente_curso", curso_id=int(curso_id)))
            return redirect(url_for("ponente_dashboard"))
        return mostrar_error("No se pudo eliminar el material.")
    except Exception as e:
        print("Error en /ponente/materiales/eliminar:", repr(e))
        return render_template("error500.html"), 500


@app.route("/ponente/inscripciones/<int:inscripcion_id>/progreso",
           methods=["POST"], endpoint="ponente_actualizar_progreso")
def ponente_actualizar_progreso(inscripcion_id):
    try:
        ponente = _nombre_ponente_actual()
        if not ponente:
            return redirect(url_for("login"))

        progreso_texto = request.form.get("progreso", "").strip()
        curso_id = request.form.get("curso_id", "").strip()
        origen = request.form.get("origen", "").strip()

        try:
            progreso = int(progreso_texto)
        except ValueError:
            return mostrar_error("El progreso debe ser un numero entero.")

        if progreso < 0 or progreso > 100:
            return mostrar_error("El progreso debe estar entre 0 y 100.")

        if actualizar_progreso_curso_ponente(inscripcion_id, ponente, progreso):
            flash("El progreso del colegiado fue actualizado.", "success")
            if origen == "seguimiento":
                return redirect(url_for("ponente_seguimiento"))
            if curso_id.isdigit():
                return redirect(url_for("ponente_curso", curso_id=int(curso_id)))
            return redirect(url_for("ponente_dashboard"))
        return mostrar_error("No se pudo actualizar el progreso. Verifique que el curso sea suyo.")
    except Exception as e:
        print("Error en /ponente/inscripciones/progreso:", repr(e))
        return render_template("error500.html"), 500


# ============================================================
# RUTAS WEB - ADMINISTRADOR
# ============================================================

@app.route("/admin", endpoint="admin_dashboard")
def admin_dashboard():
    ctx = contexto_base("Panel de Administracion", "admin_dashboard", es_admin=True)
    dashboard = {
        "stats": {
            "colegiados_total": 0,
            "colegiados_activos": 0,
            "colegiados_inactivos": 0,
            "deuda_total": 0,
            "deuda_vencida": 0,
            "cuotas_pendientes": 0,
            "cuotas_vencidas": 0,
            "recaudado_mes": 0,
            "evidencias_pendientes": 0,
            "cursos_activos": 0,
            "cursos_sin_ponente": 0,
            "cursos_proximos": 0,
            "inscripciones_total": 0,
            "pagos_curso_pendientes": 0,
            "certificados_pendientes": 0,
            "tickets_abiertos": 0,
            "tramites_pendientes": 0,
            "reconocimientos_30": 0,
        },
        "serie_financiera": [],
        "tramites_recientes": [],
        "tickets_recientes": [],
        "evidencias_pendientes": [],
        "cuotas_vencidas": [],
        "cursos_top": [],
        "cursos_proximos": [],
    }
    try:
        dashboard = leer_dashboard_admin()
    except Exception as e:
        print("Error cargando resumen admin:", repr(e))

    stats = dashboard.get("stats", {})
    alertas = []
    if stats.get("cuotas_vencidas", 0):
        alertas.append({
            "icon": "warning",
            "titulo": "Cuotas vencidas",
            "detalle": f"{stats.get('cuotas_vencidas')} cuotas necesitan seguimiento.",
            "endpoint": "admin_cuotas",
        })
    if stats.get("evidencias_pendientes", 0):
        alertas.append({
            "icon": "receipt_long",
            "titulo": "Evidencias por revisar",
            "detalle": f"{stats.get('evidencias_pendientes')} comprobantes esperan validacion.",
            "endpoint": "admin_evidencias_pago",
        })
    if stats.get("certificados_pendientes", 0):
        alertas.append({
            "icon": "verified",
            "titulo": "Certificados pendientes",
            "detalle": f"{stats.get('certificados_pendientes')} colegiados ya cumplen pago y progreso.",
            "endpoint": "admin_cursos_asignados",
        })
    if stats.get("cursos_sin_ponente", 0):
        alertas.append({
            "icon": "person_alert",
            "titulo": "Cursos sin ponente",
            "detalle": f"{stats.get('cursos_sin_ponente')} cursos activos siguen por definir.",
            "endpoint": "admin_cursos",
        })
    if stats.get("tramites_pendientes", 0):
        alertas.append({
            "icon": "assignment",
            "titulo": "Tramites pendientes",
            "detalle": f"{stats.get('tramites_pendientes')} tramites esperan atencion.",
            "endpoint": "admin_tramites",
        })
    if stats.get("reconocimientos_30", 0):
        alertas.append({
            "icon": "military_tech",
            "titulo": "Reconocimientos 30 anios",
            "detalle": f"{stats.get('reconocimientos_30')} colegiados requieren preparar ceremonia, resolucion y placa.",
            "endpoint": "admin_colegiados",
            "url": url_for("admin_colegiados", reconocimiento="30"),
        })

    total_financiero = _monto(stats.get("total_pagado")) + _monto(stats.get("deuda_total"))
    stats["cumplimiento_pago_pct"] = round(
        (_monto(stats.get("total_pagado")) / total_financiero) * 100
    ) if total_financiero > 0 else 0

    total_inscripciones = _monto(stats.get("inscripciones_total"))
    stats["certificados_pendientes_pct"] = round(
        (_monto(stats.get("certificados_pendientes")) / total_inscripciones) * 100
    ) if total_inscripciones > 0 else 0

    for curso in dashboard.get("cursos_top", []):
        cupos = _monto(curso.get("cupos"))
        inscritos = _monto(curso.get("inscritos"))
        curso["ocupacion_pct"] = round((inscritos / cupos) * 100) if cupos > 0 else 0

    ctx.update(dashboard)
    ctx["alertas"] = alertas
    return render_template("admin/admin_dashboard.html", **ctx)


@app.route("/admin/reportes", endpoint="admin_reportes")
def admin_reportes():
    try:
        reporte_activo = request.args.get("reporte", "menu").strip()
        if reporte_activo not in ["menu", "financiero", "cursos", "colegiados"]:
            reporte_activo = "menu"

        busqueda = request.args.get("q", "").strip()
        tipo = request.args.get("tipo", "").strip()
        if tipo not in ["", "mensual", "curso", "otro"]:
            tipo = ""

        estado = request.args.get("estado", "").strip()
        if estado not in ["", "Pendiente", "Pagado", "Vencida"]:
            estado = ""

        estado_curso = request.args.get("estado_curso", "").strip()
        if estado_curso not in ["", "Activo", "Inactivo"]:
            estado_curso = ""

        estado_colegiado = request.args.get("estado_colegiado", "").strip()
        if estado_colegiado not in ["", "Vigente", "Inactivo"]:
            estado_colegiado = ""

        fecha_desde = request.args.get("fecha_desde", "").strip()
        fecha_hasta = request.args.get("fecha_hasta", "").strip()
        desde_obj = _leer_fecha_iso(fecha_desde) if fecha_desde else None
        hasta_obj = _leer_fecha_iso(fecha_hasta) if fecha_hasta else None
        if fecha_desde and not desde_obj:
            fecha_desde = ""
        if fecha_hasta and not hasta_obj:
            fecha_hasta = ""
        if desde_obj and hasta_obj and desde_obj > hasta_obj:
            fecha_desde, fecha_hasta = fecha_hasta, fecha_desde
            desde_obj, hasta_obj = hasta_obj, desde_obj

        try:
            pagina = int(request.args.get("pagina", "1"))
        except ValueError:
            pagina = 1
        pagina = max(1, pagina)

        try:
            por_pagina = int(request.args.get("por_pagina", "25"))
        except ValueError:
            por_pagina = 25
        if por_pagina not in [10, 25, 50, 100]:
            por_pagina = 25

        pre_reporte = leer_reporte_financiero(
            p_tipo=tipo or None,
            p_estado=estado or None,
            p_busqueda=busqueda or None,
            p_fecha_desde=fecha_desde or None,
            p_fecha_hasta=fecha_hasta or None,
            p_limite=1,
            p_offset=0
        )
        total_registros = int((pre_reporte.get("resumen") or {}).get("total_registros", 0) or 0)
        total_paginas = max(1, (total_registros + por_pagina - 1) // por_pagina)
        pagina = min(pagina, total_paginas)
        offset = (pagina - 1) * por_pagina

        reporte = leer_reporte_financiero(
            p_tipo=tipo or None,
            p_estado=estado or None,
            p_busqueda=busqueda or None,
            p_fecha_desde=fecha_desde or None,
            p_fecha_hasta=fecha_hasta or None,
            p_limite=por_pagina,
            p_offset=offset
        )
        reporte_contable = leer_reporte_contable_demo()

        reporte_cursos = leer_reporte_cursos(
            p_busqueda=busqueda or None,
            p_estado=estado_curso or None,
            p_limite=20
        )
        reporte_colegiados = leer_reporte_colegiados(
            p_busqueda=busqueda or None,
            p_estado=estado_colegiado or None,
            p_limite=20
        )

        resumen = reporte.get("resumen") or {}
        total_general = _monto(resumen.get("total_general"))
        total_pagado = _monto(resumen.get("total_pagado"))
        total_pendiente = _monto(resumen.get("total_pendiente"))
        resumen["cumplimiento_pct"] = round((total_pagado / total_general) * 100) if total_general > 0 else 0
        resumen["pendiente_pct"] = round((total_pendiente / total_general) * 100) if total_general > 0 else 0

        for item in reporte.get("por_tipo", []):
            item["pct"] = round((_monto(item.get("monto")) / total_general) * 100) if total_general > 0 else 0
            item["label"] = (
                "Mensual" if item.get("tipo") == "mensual"
                else "Curso" if item.get("tipo") == "curso"
                else "Otro"
            )

        for item in reporte.get("por_estado", []):
            item["pct"] = round((_monto(item.get("monto")) / total_general) * 100) if total_general > 0 else 0

        max_mes = 1
        for item in reporte.get("por_mes", []):
            max_mes = max(max_mes, _monto(item.get("pagado")), _monto(item.get("pendiente")))
        for item in reporte.get("por_mes", []):
            item["etiqueta"] = _nombre_periodo(item.get("mes"), item.get("anio"))
            item["pagado_pct"] = round((_monto(item.get("pagado")) / max_mes) * 100, 1)
            item["pendiente_pct"] = round((_monto(item.get("pendiente")) / max_mes) * 100, 1)

        max_contable_mes = 1
        for item in reporte_contable.get("por_mes", []):
            max_contable_mes = max(max_contable_mes, _monto(item.get("monto")))
        for item in reporte_contable.get("por_mes", []):
            item["etiqueta"] = _nombre_periodo(item.get("mes"), item.get("anio"))
            item["monto_pct"] = round((_monto(item.get("monto")) / max_contable_mes) * 100, 1)

        hoy_iso = date.today().isoformat()
        detalle = [dict(row) for row in (reporte.get("detalle") or [])]
        for cuota in detalle:
            cuota["periodo_label"] = _nombre_periodo(
                cuota.get("periodo_mes"),
                cuota.get("periodo_anio")
            )
            vencimiento = cuota.get("fecha_vencimiento")
            cuota["vencida"] = (
                cuota.get("estado") == "Pendiente"
                and vencimiento
                and str(vencimiento) < hoy_iso
            )
            cuota["estado_reporte"] = "Vencida" if cuota["vencida"] else cuota.get("estado")
        reporte["detalle"] = detalle

        cursos_resumen = reporte_cursos.get("resumen") or {}
        inscritos_total = _monto(cursos_resumen.get("inscritos_total"))
        cupos_total = _monto(cursos_resumen.get("cupos_total"))
        ingreso_programado = _monto(cursos_resumen.get("ingreso_programado"))
        ingreso_pagado = _monto(cursos_resumen.get("ingreso_pagado"))
        cursos_resumen["ocupacion_pct"] = round((inscritos_total / cupos_total) * 100) if cupos_total > 0 else 0
        cursos_resumen["recaudacion_pct"] = round((ingreso_pagado / ingreso_programado) * 100) if ingreso_programado > 0 else 0
        cursos_resumen["progreso_promedio"] = round(_monto(cursos_resumen.get("progreso_promedio")), 1)

        cursos_categoria = [dict(row) for row in (reporte_cursos.get("por_categoria") or [])]
        max_categoria = max([_monto(row.get("inscritos")) for row in cursos_categoria] + [1])
        for row in cursos_categoria:
            row["pct"] = round((_monto(row.get("inscritos")) / max_categoria) * 100) if max_categoria > 0 else 0
        reporte_cursos["por_categoria"] = cursos_categoria

        cursos_ponente = [dict(row) for row in (reporte_cursos.get("por_ponente") or [])]
        for row in cursos_ponente:
            row["progreso_promedio"] = round(_monto(row.get("progreso_promedio")), 1)
        reporte_cursos["por_ponente"] = cursos_ponente

        cursos_detalle = [dict(row) for row in (reporte_cursos.get("detalle") or [])]
        for curso in cursos_detalle:
            cupos = _monto(curso.get("cupos"))
            inscritos = _monto(curso.get("inscritos"))
            ingreso_programado_curso = _monto(curso.get("ingreso_programado"))
            ingreso_pagado_curso = _monto(curso.get("ingreso_pagado"))
            curso["ocupacion_pct"] = round((inscritos / cupos) * 100) if cupos > 0 else 0
            curso["recaudacion_pct"] = round((ingreso_pagado_curso / ingreso_programado_curso) * 100) if ingreso_programado_curso > 0 else 0
            curso["progreso_promedio"] = round(_monto(curso.get("progreso_promedio")), 1)
        reporte_cursos["detalle"] = cursos_detalle
        reporte_cursos["resumen"] = cursos_resumen

        colegiados_resumen = reporte_colegiados.get("resumen") or {}
        total_colegiados = _monto(colegiados_resumen.get("total_colegiados"))
        con_deuda = _monto(colegiados_resumen.get("con_deuda"))
        colegiados_resumen["sin_deuda"] = max(0, int(total_colegiados - con_deuda))
        colegiados_resumen["deuda_pct"] = round((con_deuda / total_colegiados) * 100) if total_colegiados > 0 else 0
        colegiados_resumen["vigentes_pct"] = round((_monto(colegiados_resumen.get("vigentes")) / total_colegiados) * 100) if total_colegiados > 0 else 0

        colegiados_estado = [dict(row) for row in (reporte_colegiados.get("por_estado") or [])]
        for row in colegiados_estado:
            row["pct"] = round((_monto(row.get("total")) / total_colegiados) * 100) if total_colegiados > 0 else 0
        reporte_colegiados["por_estado"] = colegiados_estado
        reporte_colegiados["top_deudores"] = [dict(row) for row in (reporte_colegiados.get("top_deudores") or [])]
        reporte_colegiados["detalle"] = [dict(row) for row in (reporte_colegiados.get("detalle") or [])]
        reporte_colegiados["resumen"] = colegiados_resumen

        desde = 0 if total_registros == 0 else offset + 1
        hasta = min(offset + len(detalle), total_registros)

        ctx = contexto_base(
            "Reportes",
            "admin_reportes",
            "Analisis financiero de cuotas mensuales, cursos y pagos.",
            es_admin=True
        )
        ctx.update(reporte)
        ctx["resumen"] = resumen
        ctx["busqueda"] = busqueda
        ctx["tipo"] = tipo
        ctx["estado"] = estado
        ctx["estado_curso"] = estado_curso
        ctx["estado_colegiado"] = estado_colegiado
        ctx["fecha_desde"] = fecha_desde
        ctx["fecha_hasta"] = fecha_hasta
        ctx["por_pagina"] = por_pagina
        ctx["reporte_cursos"] = reporte_cursos
        ctx["reporte_colegiados"] = reporte_colegiados
        ctx["reporte_contable"] = reporte_contable
        ctx["reporte_activo"] = reporte_activo
        ctx["paginacion"] = {
            "pagina": pagina,
            "por_pagina": por_pagina,
            "total": total_registros,
            "total_paginas": total_paginas,
            "desde": desde,
            "hasta": hasta,
            "inicio": max(1, pagina - 2),
            "fin": min(total_paginas, pagina + 2),
        }
        return render_template("admin/admin_reportes.html", **ctx)
    except Exception as e:
        print("Error en /admin/reportes:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/reportes/exportar", endpoint="admin_reportes_exportar")
def admin_reportes_exportar():
    try:
        reporte_activo = request.args.get("reporte", "financiero").strip()
        if reporte_activo not in ["financiero", "cursos", "colegiados"]:
            return mostrar_error("Seleccione un reporte para exportar.")

        busqueda = request.args.get("q", "").strip()
        tipo = request.args.get("tipo", "").strip()
        if tipo not in ["", "mensual", "curso", "otro"]:
            tipo = ""

        estado = request.args.get("estado", "").strip()
        if estado not in ["", "Pendiente", "Pagado", "Vencida"]:
            estado = ""

        estado_curso = request.args.get("estado_curso", "").strip()
        if estado_curso not in ["", "Activo", "Inactivo"]:
            estado_curso = ""

        estado_colegiado = request.args.get("estado_colegiado", "").strip()
        if estado_colegiado not in ["", "Vigente", "Inactivo"]:
            estado_colegiado = ""

        fecha_desde = request.args.get("fecha_desde", "").strip()
        fecha_hasta = request.args.get("fecha_hasta", "").strip()
        if fecha_desde and not _leer_fecha_iso(fecha_desde):
            fecha_desde = ""
        if fecha_hasta and not _leer_fecha_iso(fecha_hasta):
            fecha_hasta = ""

        if reporte_activo == "financiero":
            reporte = leer_reporte_financiero(
                p_tipo=tipo or None,
                p_estado=estado or None,
                p_busqueda=busqueda or None,
                p_fecha_desde=fecha_desde or None,
                p_fecha_hasta=fecha_hasta or None,
                p_limite=1000,
                p_offset=0
            )
            filas = []
            hoy_iso = date.today().isoformat()
            for q in reporte.get("detalle", []) or []:
                vencimiento = q.get("fecha_vencimiento")
                vencida = (
                    q.get("estado") == "Pendiente"
                    and vencimiento
                    and str(vencimiento) < hoy_iso
                )
                filas.append([
                    q.get("nombre", ""),
                    q.get("matricula", ""),
                    q.get("fecha", ""),
                    q.get("tipo", ""),
                    q.get("concepto", ""),
                    _nombre_periodo(q.get("periodo_mes"), q.get("periodo_anio")),
                    q.get("fecha_vencimiento", ""),
                    format(_monto(q.get("monto")), ".2f"),
                    "Vencida" if vencida else q.get("estado", ""),
                ])
            return _respuesta_csv(
                "reporte_financiero.csv",
                ["Colegiado", "Matricula", "Fecha", "Tipo", "Concepto",
                 "Periodo", "Vencimiento", "Monto", "Estado"],
                filas
            )

        if reporte_activo == "cursos":
            reporte = leer_reporte_cursos(
                p_busqueda=busqueda or None,
                p_estado=estado_curso or None,
                p_limite=1000
            )
            filas = []
            for c in reporte.get("detalle", []) or []:
                filas.append([
                    c.get("titulo", ""),
                    c.get("categoria", ""),
                    c.get("ponente", ""),
                    c.get("estado", ""),
                    c.get("inscritos", 0) or 0,
                    c.get("cupos", 0) or 0,
                    format(_monto(c.get("progreso_promedio")), ".1f"),
                    c.get("pagados", 0) or 0,
                    c.get("pendientes", 0) or 0,
                    c.get("certificados", 0) or 0,
                    format(_monto(c.get("ingreso_pagado")), ".2f"),
                ])
            return _respuesta_csv(
                "reporte_cursos.csv",
                ["Curso", "Categoria", "Ponente", "Estado", "Inscritos",
                 "Cupos", "Progreso", "Pagados", "Pendientes",
                 "Certificados", "Ingresos"],
                filas
            )

        reporte = leer_reporte_colegiados(
            p_busqueda=busqueda or None,
            p_estado=estado_colegiado or None,
            p_limite=1000
        )
        filas = []
        for c in reporte.get("detalle", []) or []:
            filas.append([
                c.get("nombre", ""),
                c.get("matricula", ""),
                c.get("documento", ""),
                c.get("especialidad", ""),
                c.get("estado", ""),
                c.get("cuotas_pendientes", 0) or 0,
                c.get("cuotas_vencidas", 0) or 0,
                format(_monto(c.get("deuda_pendiente")), ".2f"),
                c.get("cursos_inscritos", 0) or 0,
                c.get("certificados_emitidos", 0) or 0,
            ])
        return _respuesta_csv(
            "reporte_colegiados.csv",
            ["Colegiado", "Matricula", "DNI", "Especialidad", "Estado",
             "Cuotas pendientes", "Cuotas vencidas", "Deuda", "Cursos",
             "Certificados"],
            filas
        )
    except Exception as e:
        print("Error en /admin/reportes/exportar:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/colegiados", endpoint="admin_colegiados")
def admin_colegiados():
    try:
        ctx = contexto_base("Colegiados", "admin_colegiados", es_admin=True)
        busqueda = request.args.get("q", "").strip()
        especialidad = request.args.get("especialidad", "").strip()
        estado = request.args.get("estado", "").strip()
        reconocimiento = request.args.get("reconocimiento", "").strip()
        if estado not in ["", "Vigente", "Inactivo"]:
            estado = ""
        if reconocimiento not in ["", "30"]:
            reconocimiento = ""

        ctx["colegiados"] = leer_colegiados(
            p_busqueda=busqueda or None,
            p_especialidad=especialidad or None,
            p_estado=estado or None,
            p_reconocimiento_30=(reconocimiento == "30")
        ) or []
        especialidades = leer_especialidades_colegiados() or []
        especialidad_nombre = ""
        for item in especialidades:
            if str(item.get("id")) == str(especialidad):
                especialidad_nombre = item.get("nombre") or item.get("especialidad") or ""
                break

        ctx["especialidades"] = especialidades
        ctx["busqueda"] = busqueda
        ctx["especialidad_filtro"] = especialidad
        ctx["especialidad_filtro_nombre"] = especialidad_nombre
        ctx["estado_filtro"] = estado
        ctx["reconocimiento_filtro"] = reconocimiento
        return render_template("admin/admin_colegiados.html", **ctx)
    except Exception as e:
        print("Error en /admin/colegiados:", repr(e))
        return render_template("error500.html")


@app.route("/admin/colegiados/exportar", endpoint="admin_colegiados_exportar")
def admin_colegiados_exportar():
    try:
        busqueda = request.args.get("q", "").strip()
        especialidad = request.args.get("especialidad", "").strip()
        estado = request.args.get("estado", "").strip()
        reconocimiento = request.args.get("reconocimiento", "").strip()
        if estado not in ["", "Vigente", "Inactivo"]:
            estado = ""
        if reconocimiento not in ["", "30"]:
            reconocimiento = ""

        colegiados = leer_colegiados(
            p_busqueda=busqueda or None,
            p_especialidad=especialidad or None,
            p_estado=estado or None,
            p_reconocimiento_30=(reconocimiento == "30")
        ) or []
        filas = []
        for c in colegiados:
            filas.append([
                c.get("nombre", ""),
                c.get("matricula", ""),
                c.get("documento", ""),
                c.get("especialidad", ""),
                c.get("direccion", ""),
                c.get("correo", ""),
                c.get("telefono", ""),
                c.get("fecha_colegiatura", ""),
                c.get("fecha_reconocimiento_30", ""),
                c.get("dias_para_30", ""),
                c.get("vigencia", ""),
                c.get("estado", ""),
                c.get("epc_points", 0) or 0,
            ])
        return _respuesta_csv(
            "colegiados_filtrados.csv",
            ["Colegiado", "Matricula", "DNI", "Especialidad", "Direccion",
             "Correo", "Telefono", "Fecha colegiatura", "Cumple 30 anios",
             "Dias para 30", "Vigencia", "Estado", "Puntos EPC"],
            filas
        )
    except Exception as e:
        print("Error en /admin/colegiados/exportar:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/colegiados/nuevo", methods=["POST"], endpoint="admin_nuevo_colegiado")
def admin_nuevo_colegiado():
    try:
        nombre     = request.form.get("nombre", "").strip()
        matricula  = request.form.get("matricula", "").strip()
        documento  = request.form.get("documento", "").strip()
        especialidad_id = request.form.get("especialidad_id", "").strip()
        direccion  = request.form.get("direccion", "").strip()
        correo     = request.form.get("correo", "").strip()
        telefono   = request.form.get("telefono", "").strip()
        fecha_colegiatura_txt = request.form.get("fecha_colegiatura", "").strip()
        password   = request.form.get("password", "").strip()

        if not all([nombre, matricula, documento, especialidad_id, direccion, correo, password]):
            return mostrar_error("Complete todos los campos obligatorios.")
        if not _validar_nombre_peru(nombre):
            return mostrar_error("El nombre solo debe contener letras y espacios (mínimo 3 caracteres).")
        if not _validar_dni_peru(documento):
            return mostrar_error("El DNI debe tener exactamente 8 dígitos numéricos.")
        if not _validar_correo(correo):
            return mostrar_error("Ingrese un correo electrónico válido.")
        if not _validar_telefono_peru(telefono):
            return mostrar_error("El teléfono debe tener 9 dígitos y comenzar con 9 (ej: 987654321).")

        fecha_colegiatura = None
        if fecha_colegiatura_txt:
            fecha_colegiatura = _leer_fecha_iso(fecha_colegiatura_txt)
            if not fecha_colegiatura:
                return mostrar_error("Ingrese una fecha de colegiatura valida.")
            if fecha_colegiatura > date.today():
                return mostrar_error("La fecha de colegiatura no puede ser futura.")

        obj = clsColegiado(0, nombre, matricula, documento, especialidad_id,
                           correo, telefono, p_direccion=direccion,
                           p_especialidad_id=especialidad_id,
                           p_fecha_colegiatura=fecha_colegiatura)
        if insertar_colegiado(obj, password):
            return mostrar_exito("El colegiado fue registrado correctamente.",
                                 "admin_colegiados", "Ver colegiados")
        return mostrar_error("No se pudo registrar el colegiado. Verifique que la matrícula no exista.")
    except Exception as e:
        print("Error en /admin/colegiados/nuevo:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/colegiados/<int:cid>/editar", methods=["POST"], endpoint="admin_actualizar_colegiado")
def admin_actualizar_colegiado(cid):
    try:
        nombre       = request.form.get("nombre", "").strip()
        especialidad_id = request.form.get("especialidad_id", "").strip()
        direccion    = request.form.get("direccion", "").strip()
        correo       = request.form.get("correo", "").strip()
        telefono     = request.form.get("telefono", "").strip()
        epc_points   = request.form.get("epc_points", 0)
        vigencia     = request.form.get("vigencia", "").strip()
        fecha_colegiatura_txt = request.form.get("fecha_colegiatura", "").strip()

        if not nombre:
            return mostrar_error("El nombre es obligatorio.")
        if not especialidad_id:
            return mostrar_error("La especialidad es obligatoria.")
        if not direccion:
            return mostrar_error("La direccion es obligatoria.")
        if not _validar_nombre_peru(nombre):
            return mostrar_error("El nombre solo debe contener letras y espacios (mínimo 3 caracteres).")
        if correo and not _validar_correo(correo):
            return mostrar_error("Ingrese un correo electrónico válido.")
        if not _validar_telefono_peru(telefono):
            return mostrar_error("El teléfono debe tener 9 dígitos y comenzar con 9 (ej: 987654321).")

        fecha_colegiatura = None
        if fecha_colegiatura_txt:
            fecha_colegiatura = _leer_fecha_iso(fecha_colegiatura_txt)
            if not fecha_colegiatura:
                return mostrar_error("Ingrese una fecha de colegiatura valida.")
            if fecha_colegiatura > date.today():
                return mostrar_error("La fecha de colegiatura no puede ser futura.")

        obj = clsColegiado(p_id=cid, p_nombre=nombre, p_especialidad=especialidad_id,
                           p_correo=correo, p_telefono=telefono,
                           p_epc_points=epc_points, p_vigencia=vigencia,
                           p_direccion=direccion,
                           p_especialidad_id=especialidad_id,
                           p_fecha_colegiatura=fecha_colegiatura)
        if actualizar_colegiado(obj):
            return mostrar_exito("Los datos del colegiado fueron actualizados.",
                                 "admin_colegiados", "Ver colegiados")
        return mostrar_error("No se pudo actualizar el colegiado.")
    except Exception as e:
        print("Error en /admin/colegiados/editar:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/colegiados/<int:cid>/toggle", methods=["POST"], endpoint="admin_toggle_colegiado")
def admin_toggle_colegiado(cid):
    try:
        if colegiado_vigente_con_deuda_pendiente(cid):
            return mostrar_error("No se puede desactivar el colegiado porque tiene cuotas pendientes.")

        if toggle_estado_colegiado(cid):
            return mostrar_exito("El estado del colegiado fue actualizado.",
                                 "admin_colegiados", "Ver colegiados")
        return mostrar_error("No se pudo cambiar el estado del colegiado.")
    except Exception as e:
        print("Error en /admin/colegiados/toggle:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/usuarios", endpoint="admin_usuarios")
def admin_usuarios():
    try:
        ctx = contexto_base("Usuarios", "admin_usuarios", es_admin=True)
        ctx["usuarios"] = leer_usuarios() or []
        return render_template("admin/admin_usuarios.html", **ctx)
    except Exception as e:
        print("Error en /admin/usuarios:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/usuarios/nuevo", methods=["POST"], endpoint="admin_nuevo_usuario")
def admin_nuevo_usuario():
    try:
        matricula = request.form.get("matricula", "").strip()
        password = request.form.get("password", "").strip()
        rol = request.form.get("rol", "").strip()
        activo = request.form.get("activo", "1").strip()

        if not all([matricula, password, rol]):
            return mostrar_error("Complete los campos obligatorios del usuario.")
        if rol not in ["colegiado", "admin", "ponente"]:
            return mostrar_error("Seleccione un rol valido.")
        if activo not in ["0", "1"]:
            return mostrar_error("Seleccione un estado valido.")

        obj = clsUsuario(0, matricula, password, rol, int(activo))
        if insertar_usuario(obj):
            return mostrar_exito("El usuario fue creado correctamente.",
                                 "admin_usuarios",
                                 "Ver usuarios")
        return mostrar_error("No se pudo crear el usuario. Verifique la matricula o si ya existe.")
    except Exception as e:
        print("Error en /admin/usuarios/nuevo:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/usuarios/<int:uid>/editar", methods=["POST"], endpoint="admin_actualizar_usuario")
def admin_actualizar_usuario(uid):
    try:
        password = request.form.get("password", "").strip()
        rol = request.form.get("rol", "").strip()
        activo = request.form.get("activo", "1").strip()

        if rol not in ["colegiado", "admin", "ponente"]:
            return mostrar_error("Seleccione un rol valido.")
        if activo not in ["0", "1"]:
            return mostrar_error("Seleccione un estado valido.")

        obj = clsUsuario(uid, None, password, rol, int(activo))
        if actualizar_usuario(obj):
            return mostrar_exito("El usuario fue actualizado correctamente.",
                                 "admin_usuarios",
                                 "Ver usuarios")
        return mostrar_error("No se pudo actualizar el usuario.")
    except Exception as e:
        print("Error en /admin/usuarios/editar:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/cuotas", endpoint="admin_cuotas")
def admin_cuotas():
    try:
        busqueda = request.args.get("q", "").strip()
        filtro_legacy = request.args.get("matricula", "").strip()
        if filtro_legacy and not busqueda:
            busqueda = filtro_legacy
        tipo = request.args.get("tipo", "").strip()
        if tipo not in ["", "mensual", "curso", "otro"]:
            tipo = ""

        try:
            pagina = int(request.args.get("pagina", "1"))
        except ValueError:
            pagina = 1
        pagina = max(1, pagina)

        try:
            por_pagina = int(request.args.get("por_pagina", "25"))
        except ValueError:
            por_pagina = 25
        if por_pagina not in [10, 25, 50]:
            por_pagina = 25

        total_registros = contar_cuotas(
            p_tipo=tipo or None,
            p_busqueda=busqueda or None
        )
        total_paginas = max(1, (total_registros + por_pagina - 1) // por_pagina)
        pagina = min(pagina, total_paginas)
        offset = (pagina - 1) * por_pagina

        cuotas = [dict(q) for q in (leer_cuotas(
            p_tipo=tipo or None,
            p_busqueda=busqueda or None,
            p_limite=por_pagina,
            p_offset=offset
        ) or [])]
        hoy_iso = date.today().isoformat()
        for cuota in cuotas:
            cuota["periodo_label"] = _nombre_periodo(
                cuota.get("periodo_mes"),
                cuota.get("periodo_anio")
            )
            fecha_vencimiento = cuota.get("fecha_vencimiento")
            cuota["vencida"] = (
                cuota.get("estado") == "Pendiente"
                and fecha_vencimiento
                and str(fecha_vencimiento) < hoy_iso
            )

        desde = 0 if total_registros == 0 else offset + 1
        hasta = min(offset + len(cuotas), total_registros)

        ctx = contexto_base("Cuotas", "admin_cuotas", es_admin=True)
        ctx["cuotas"] = cuotas
        ctx["busqueda"] = busqueda
        ctx["filtro"] = busqueda
        ctx["tipo"] = tipo
        ctx["por_pagina"] = por_pagina
        ctx["resumen_cuotas"] = resumir_cuotas(
            p_tipo=tipo or None,
            p_busqueda=busqueda or None
        )
        ctx["paginacion"] = {
            "pagina": pagina,
            "por_pagina": por_pagina,
            "total": total_registros,
            "total_paginas": total_paginas,
            "desde": desde,
            "hasta": hasta,
            "inicio": max(1, pagina - 2),
            "fin": min(total_paginas, pagina + 2),
        }
        ctx["resumen_mensual"] = obtener_resumen_cuotas_mensuales() or {}
        ctx["pago_anual"] = obtener_resumen_pago_anual() or {}
        ctx["pago_adelantado"] = obtener_resumen_pago_adelantado() or {}
        return render_template("admin/admin_cuotas.html", **ctx)
    except Exception as e:
        print("Error en /admin/cuotas:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/cuotas/nueva", methods=["POST"], endpoint="admin_nueva_cuota")
def admin_nueva_cuota():
    try:
        requeridos = ["matricula", "fecha", "monto", "concepto", "estado"]
        for campo in requeridos:
            if not request.form.get(campo, "").strip():
                return mostrar_error("Complete todos los campos obligatorios.")

        fecha = _leer_fecha_iso(request.form["fecha"])
        if not fecha:
            return mostrar_error("Ingrese una fecha valida.")
        fecha_vencimiento_txt = request.form.get("fecha_vencimiento", "").strip()
        fecha_vencimiento = None
        if fecha_vencimiento_txt:
            fecha_vencimiento = _leer_fecha_iso(fecha_vencimiento_txt)
            if not fecha_vencimiento:
                return mostrar_error("Ingrese una fecha de vencimiento valida.")
            if fecha_vencimiento < fecha:
                return mostrar_error("La fecha de vencimiento no puede ser anterior a la fecha.")

        if _monto(request.form["monto"]) <= 0:
            return mostrar_error("Ingrese un monto mayor a cero.")

        estado = request.form["estado"].strip()
        if estado not in ["Pendiente", "Pagado"]:
            return mostrar_error("Seleccione un estado valido.")

        tipo = request.form.get("tipo", "otro").strip()
        if tipo not in ["mensual", "otro"]:
            tipo = "otro"
        periodo_mes = None
        periodo_anio = None
        if tipo == "mensual":
            periodo_mes = fecha.month
            periodo_anio = fecha.year

        obj = clsCuota(0,
                       request.form["matricula"],
                       request.form["fecha"],
                       request.form["concepto"],
                       request.form["monto"],
                       estado,
                       tipo,
                       periodo_mes,
                       periodo_anio,
                       fecha_vencimiento_txt or None)
        if insertar_cuota(obj):
            if estado == "Pendiente":
                _notificar_colegiado(
                    request.form["matricula"],
                    "cuota",
                    "Nueva cuota pendiente",
                    "Se registro una cuota pendiente: " +
                    request.form["concepto"] + " por S/ " +
                    format(_monto(request.form["monto"]), ".2f") + ".",
                    "estado_cuenta",
                    "Ver estado",
                    "cuota",
                    None
                )
            return mostrar_exito("La cuota fue registrada correctamente.",
                                 "admin_cuotas",
                                 "Ver cuotas")
        return mostrar_error("No se pudo registrar la cuota. Verifique el colegiado seleccionado.")
    except Exception:
        return render_template("error500.html")


@app.route("/admin/cuotas/procesar-mensuales",
           methods=["POST"], endpoint="admin_procesar_cuotas_mensuales")
def admin_procesar_cuotas_mensuales():
    try:
        monto = request.form.get("monto_mensual", "80").strip()
        resultado = procesar_cuotas_mensuales(monto)
        if resultado.get("ok"):
            for aviso in resultado.get("notificaciones", []) or []:
                _notificar_colegiado(
                    aviso.get("matricula"),
                    "cuota",
                    "Cuota mensual generada",
                    "Se genero la cuota " + str(aviso.get("periodo")) +
                    " por S/ " + format(_monto(aviso.get("monto")), ".2f") + ".",
                    "estado_cuenta",
                    "Ver estado",
                    "cuota",
                    None
                )
            mensaje = (
                f"Periodo {resultado.get('periodo')} procesado. "
                f"Generadas: {resultado.get('generadas', 0)}. "
                f"Ya existentes: {resultado.get('existentes', 0)}."
            )
            return mostrar_exito(mensaje, "admin_cuotas", "Ver cuotas")
        return mostrar_error(resultado.get("mensaje", "No se pudieron procesar las cuotas."))
    except Exception as e:
        print("Error en /admin/cuotas/procesar-mensuales:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/cuotas/pago-anual",
           methods=["POST"], endpoint="admin_registrar_pago_anual")
def admin_registrar_pago_anual():
    try:
        matricula = request.form.get("matricula", "").strip()
        anio = request.form.get("anio", str(date.today().year)).strip()
        monto = request.form.get("monto_mensual", "80").strip()
        descuento = request.form.get("descuento_anual", "10").strip()

        if not matricula:
            return mostrar_error("Seleccione el colegiado para el pago anual.")

        resultado = registrar_pago_anual_anticipado(
            matricula, anio, monto, descuento
        )
        if resultado.get("ok"):
            colegiado = resultado.get("colegiado", {}) or {}
            _notificar_colegiado(
                colegiado.get("matricula", matricula),
                "cuota",
                "Pago anual registrado",
                "Se registro el pago anual anticipado " +
                str(resultado.get("anio")) + " por S/ " +
                format(_monto(resultado.get("monto_total")), ".2f") + ".",
                "estado_cuenta",
                "Ver estado",
                "cuota",
                None
            )
            mensaje = (
                "Pago anual anticipado registrado. "
                f"Descuento: {resultado.get('descuento', 0)}%. "
                f"Generadas: {resultado.get('generadas', 0)}. "
                f"Actualizadas: {resultado.get('actualizadas', 0)}. "
                f"Ya pagadas: {resultado.get('ya_pagadas', 0)}. "
                f"Comprobantes: {resultado.get('comprobantes', 0)}."
            )
            return mostrar_exito(mensaje, "admin_cuotas", "Ver cuotas")
        return mostrar_error(resultado.get("mensaje", "No se pudo registrar el pago anual."))
    except Exception as e:
        print("Error en /admin/cuotas/pago-anual:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/cuotas/pago-adelantado",
           methods=["POST"], endpoint="admin_registrar_pago_adelantado")
def admin_registrar_pago_adelantado():
    try:
        matricula = request.form.get("matricula", "").strip()
        anio = request.form.get("anio", str(date.today().year)).strip()
        mes_inicio = request.form.get("mes_inicio", str(date.today().month)).strip()
        cantidad_meses = request.form.get("cantidad_meses", "1").strip()
        monto = request.form.get("monto_mensual", "80").strip()

        if not matricula:
            return mostrar_error("Seleccione el colegiado para el pago adelantado.")

        resultado = registrar_pago_adelantado_cuotas(
            matricula, anio, mes_inicio, cantidad_meses, monto
        )
        if resultado.get("ok"):
            colegiado = resultado.get("colegiado", {}) or {}
            _notificar_colegiado(
                colegiado.get("matricula", matricula),
                "cuota",
                "Pago adelantado registrado",
                "Se registro el pago adelantado de " +
                str(resultado.get("comprobantes", 0)) +
                " cuota(s) por S/ " +
                format(_monto(resultado.get("monto_total")), ".2f") + ".",
                "estado_cuenta",
                "Ver estado",
                "cuota",
                None
            )
            mensaje = (
                "Pago adelantado registrado. "
                f"Generadas: {resultado.get('generadas', 0)}. "
                f"Actualizadas: {resultado.get('actualizadas', 0)}. "
                f"Ya pagadas: {resultado.get('ya_pagadas', 0)}. "
                f"Comprobantes: {resultado.get('comprobantes', 0)}."
            )
            return mostrar_exito(mensaje, "admin_cuotas", "Ver cuotas")
        return mostrar_error(resultado.get("mensaje", "No se pudo registrar el pago adelantado."))
    except Exception as e:
        print("Error en /admin/cuotas/pago-adelantado:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/cuotas/procesar-cursos",
           methods=["POST"], endpoint="admin_procesar_cuotas_cursos")
def admin_procesar_cuotas_cursos():
    try:
        resultado = procesar_cuotas_cursos_faltantes()
        if resultado.get("ok"):
            for aviso in resultado.get("notificaciones", []) or []:
                _notificar_colegiado(
                    aviso.get("matricula"),
                    "cuota",
                    "Cuota de curso generada",
                    "Se genero la cuota pendiente del curso " +
                    str(aviso.get("titulo")) + " por S/ " +
                    format(_monto(aviso.get("monto")), ".2f") + ".",
                    "estado_cuenta",
                    "Ver pago",
                    "curso",
                    None
                )
            mensaje = (
                "Cuotas de cursos revisadas. "
                f"Generadas: {resultado.get('generadas', 0)}. "
                f"Ya existentes/actualizadas: {resultado.get('existentes', 0)}."
            )
            return mostrar_exito(mensaje, "admin_cuotas", "Ver cuotas")
        return mostrar_error(resultado.get("mensaje", "No se pudieron procesar las cuotas de cursos."))
    except Exception as e:
        print("Error en /admin/cuotas/procesar-cursos:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/cuotas/<int:qid>/historial", endpoint="admin_historial_cuota")
def admin_historial_cuota(qid):
    try:
        historial = leer_historial_cuota_admin(qid)
        if not historial.get("cuota"):
            return mostrar_error("No se encontro la cuota seleccionada.", 404)
        ctx = contexto_base("Historial de Cuota", "admin_cuotas", es_admin=True)
        ctx.update(historial)
        ctx["periodo_label"] = _nombre_periodo(
            historial["cuota"].get("periodo_mes"),
            historial["cuota"].get("periodo_anio")
        )
        return render_template("admin/admin_historial_cuota.html", **ctx)
    except Exception as e:
        print("Error en /admin/cuotas/historial:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/cuotas/<int:qid>/pagar", methods=["POST"], endpoint="admin_pagar_cuota")
def admin_pagar_cuota(qid):
    try:
        resultado = pagar_cuota(qid)
        if resultado.get("ok"):
            return mostrar_exito("La cuota fue marcada como pagada.",
                                 "admin_cuotas",
                                 "Ver cuotas")
        return mostrar_error(resultado.get("mensaje", "No se pudo actualizar el estado de la cuota."))
    except Exception:
        return render_template("error500.html")


@app.route("/admin/cuotas/<int:qid>/eliminar", methods=["POST"], endpoint="admin_eliminar_cuota")
def admin_eliminar_cuota(qid):
    try:
        resultado = eliminar_cuota(qid)
        if resultado.get("ok"):
            return mostrar_exito("La cuota fue eliminada correctamente.",
                                 "admin_cuotas",
                                 "Ver cuotas")
        return mostrar_error(resultado.get("mensaje", "No se pudo eliminar la cuota."))
    except Exception:
        return render_template("error500.html")


@app.route("/admin/pagos-demo", endpoint="admin_pagos_demo_legacy")
def admin_pagos_demo_legacy():
    return redirect(url_for("admin_pagos_demo"))


@app.route("/admin/pagos", endpoint="admin_pagos_demo")
def admin_pagos_demo():
    try:
        busqueda = request.args.get("q", "").strip()
        estado_pago = request.args.get("estado_pago", "").strip()
        if estado_pago not in ["", "Aprobado", "Pendiente", "Rechazado"]:
            estado_pago = ""
        estado_comprobante = request.args.get("estado_comprobante", "").strip()
        if estado_comprobante not in ["", "Emitido", "Anulado"]:
            estado_comprobante = ""

        try:
            pagina = int(request.args.get("pagina", "1"))
        except ValueError:
            pagina = 1
        pagina = max(1, pagina)

        try:
            por_pagina = int(request.args.get("por_pagina", "25"))
        except ValueError:
            por_pagina = 25
        if por_pagina not in [10, 25, 50]:
            por_pagina = 25

        total_registros = contar_transacciones_pago_demo(
            p_estado=estado_pago or None,
            p_busqueda=busqueda or None
        )
        total_paginas = max(1, (total_registros + por_pagina - 1) // por_pagina)
        pagina = min(pagina, total_paginas)
        offset = (pagina - 1) * por_pagina

        transacciones = leer_transacciones_pago_demo(
            p_estado=estado_pago or None,
            p_busqueda=busqueda or None,
            p_limite=por_pagina,
            p_offset=offset
        ) or []
        comprobantes = leer_comprobantes_pago_demo_admin(
            p_estado=estado_comprobante or None,
            p_busqueda=busqueda or None,
            p_limite=50
        ) or []

        desde = 0 if total_registros == 0 else offset + 1
        hasta = min(offset + len(transacciones), total_registros)

        ctx = contexto_base("Pagos y Comprobantes", "admin_pagos_demo", es_admin=True)
        ctx["busqueda"] = busqueda
        ctx["estado_pago"] = estado_pago
        ctx["estado_comprobante"] = estado_comprobante
        ctx["por_pagina"] = por_pagina
        ctx["transacciones"] = transacciones
        ctx["comprobantes"] = comprobantes
        ctx["resumen_pagos"] = resumir_pagos_demo()
        ctx["paginacion"] = {
            "pagina": pagina,
            "por_pagina": por_pagina,
            "total": total_registros,
            "total_paginas": total_paginas,
            "desde": desde,
            "hasta": hasta,
            "inicio": max(1, pagina - 2),
            "fin": min(total_paginas, pagina + 2),
        }
        return render_template("admin/admin_pagos_demo.html", **ctx)
    except Exception as e:
        print("Error en /admin/pagos:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/pagos/exportar", endpoint="admin_pagos_demo_exportar")
def admin_pagos_demo_exportar():
    try:
        busqueda = request.args.get("q", "").strip()
        estado_pago = request.args.get("estado_pago", "").strip()
        if estado_pago not in ["", "Aprobado", "Pendiente", "Rechazado"]:
            estado_pago = ""
        transacciones = leer_transacciones_pago_demo(
            p_estado=estado_pago or None,
            p_busqueda=busqueda or None,
            p_limite=100
        ) or []
        filas = []
        for t in transacciones:
            comprobante = ""
            if t.get("serie"):
                comprobante = str(t.get("serie")) + "-" + str(t.get("numero") or 0).zfill(8)
            filas.append([
                t.get("pagado_en") or t.get("creado_en"),
                t.get("matricula"),
                t.get("nombre"),
                t.get("concepto"),
                t.get("metodo"),
                t.get("codigo_transaccion"),
                t.get("codigo_autorizacion"),
                t.get("monto"),
                t.get("estado"),
                comprobante,
                t.get("comprobante_estado") or "",
            ])
        return _respuesta_csv(
            "pagos_comprobantes.csv",
            ["Fecha", "Matricula", "Colegiado", "Concepto", "Metodo",
             "Transaccion", "Autorizacion", "Monto", "Estado pago",
             "Comprobante", "Estado comprobante"],
            filas
        )
    except Exception as e:
        print("Error en /admin/pagos/exportar:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/pagos/comprobante/<int:comprobante_id>",
           endpoint="admin_comprobante_pago_demo")
def admin_comprobante_pago_demo(comprobante_id):
    try:
        comprobante = leer_comprobante_pago_demo_admin(comprobante_id)
        if not comprobante:
            return mostrar_error("No se encontro el comprobante solicitado.", 404)
        ctx = contexto_base("Comprobante de Pago", "admin_pagos_demo", es_admin=True)
        ctx["comprobante"] = comprobante
        ctx["volver_endpoint"] = "admin_pagos_demo"
        ctx["volver_label"] = "Pagos"
        ctx["numero_comprobante"] = (
            str(comprobante.get("serie") or "") + "-" +
            str(comprobante.get("numero") or 0).zfill(8)
        )
        return render_template("colegiado/comprobante_pago.html", **ctx)
    except Exception as e:
        print("Error en /admin/pagos/comprobante:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/pagos/comprobante/<int:comprobante_id>/anular",
           methods=["POST"], endpoint="admin_anular_comprobante_pago_demo")
def admin_anular_comprobante_pago_demo(comprobante_id):
    try:
        motivo = request.form.get("motivo", "").strip()
        if len(motivo) < 5:
            return mostrar_error("Ingrese un motivo de anulacion mas detallado.")
        usuario = session.get("profile", {}) or {}
        resultado = anular_comprobante_pago_demo(
            comprobante_id,
            usuario.get("matricula", "admin"),
            usuario.get("nombre", "Administrador CCPL"),
            motivo
        )
        if resultado.get("ok"):
            _notificar_colegiado(
                resultado.get("matricula"),
                "cuota",
                "Comprobante anulado",
                "El comprobante del concepto " +
                str(resultado.get("concepto")) +
                " fue anulado por administracion.",
                "estado_cuenta",
                "Ver estado",
                "comprobante",
                comprobante_id
            )
            return mostrar_exito("El comprobante fue anulado correctamente.",
                                 "admin_pagos_demo",
                                 "Ver pagos")
        return mostrar_error(resultado.get("mensaje", "No se pudo anular el comprobante."))
    except Exception as e:
        print("Error en /admin/pagos/anular:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/pagos/mercado-pago",
           methods=["GET", "POST"], endpoint="admin_mercado_pago_configuracion")
def admin_mercado_pago_configuracion():
    try:
        config_actual = obtener_configuracion_mercado_pago() or {}
        if request.method == "POST":
            datos = {
                "modo": request.form.get("modo", "TEST"),
                "activo": request.form.get("activo", "0"),
                "access_token": request.form.get("access_token", ""),
                "public_key": request.form.get("public_key", ""),
            }
            resultado = actualizar_configuracion_mercado_pago(datos)
            if resultado.get("ok"):
                flash(resultado.get("mensaje"), "success")
                return redirect(url_for("admin_mercado_pago_configuracion"))
            flash(resultado.get("mensaje", "No se pudo guardar Mercado Pago."), "error")
            config_actual = {**config_actual, **datos}

        ctx = contexto_base("Mercado Pago", "admin_mercado_pago_configuracion", es_admin=True)
        ctx["config"] = config_actual
        return render_template("admin/admin_mercado_pago_configuracion.html", **ctx)
    except Exception as e:
        print("Error en /admin/pagos/mercado-pago:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/facturacion", endpoint="admin_facturacion")
def admin_facturacion():
    try:
        busqueda = request.args.get("q", "").strip()
        estado = request.args.get("estado", "").strip()
        if estado not in ["", "Pendiente", "Aceptado", "Rechazado", "Anulado"]:
            estado = ""

        try:
            pagina = int(request.args.get("pagina", "1"))
        except ValueError:
            pagina = 1
        pagina = max(1, pagina)

        try:
            por_pagina = int(request.args.get("por_pagina", "25"))
        except ValueError:
            por_pagina = 25
        if por_pagina not in [10, 25, 50]:
            por_pagina = 25

        total_registros = contar_comprobantes_fiscales(
            p_estado=estado or None,
            p_busqueda=busqueda or None
        )
        total_paginas = max(1, (total_registros + por_pagina - 1) // por_pagina)
        pagina = min(pagina, total_paginas)
        offset = (pagina - 1) * por_pagina

        comprobantes = leer_comprobantes_fiscales(
            p_estado=estado or None,
            p_busqueda=busqueda or None,
            p_limite=por_pagina,
            p_offset=offset
        ) or []

        desde = 0 if total_registros == 0 else offset + 1
        hasta = min(offset + len(comprobantes), total_registros)

        ctx = contexto_base("Facturacion", "admin_facturacion", es_admin=True)
        ctx["busqueda"] = busqueda
        ctx["estado"] = estado
        ctx["por_pagina"] = por_pagina
        ctx["comprobantes"] = comprobantes
        ctx["resumen_facturacion"] = resumir_facturacion()
        ctx["config_facturacion"] = obtener_configuracion_facturacion() or {}
        ctx["paginacion"] = {
            "pagina": pagina,
            "por_pagina": por_pagina,
            "total": total_registros,
            "total_paginas": total_paginas,
            "desde": desde,
            "hasta": hasta,
            "inicio": max(1, pagina - 2),
            "fin": min(total_paginas, pagina + 2),
        }
        return render_template("admin/admin_facturacion.html", **ctx)
    except Exception as e:
        print("Error en /admin/facturacion:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/facturacion/configuracion",
           methods=["GET", "POST"], endpoint="admin_facturacion_configuracion")
def admin_facturacion_configuracion():
    try:
        config_actual = obtener_configuracion_facturacion() or {}
        if request.method == "POST":
            certificado_ruta = config_actual.get("certificado_ruta") or ""
            certificado_archivo = request.files.get("certificado_archivo")
            if certificado_archivo and certificado_archivo.filename:
                certificado_ruta = _guardar_certificado_sunat(certificado_archivo)
                if certificado_ruta is None:
                    flash("El certificado debe ser un archivo .pfx o .p12.", "error")
                    ctx = contexto_base("Configuracion SUNAT", "admin_facturacion_configuracion", es_admin=True)
                    ctx["config"] = config_actual
                    ruta_guardada = str(config_actual.get("certificado_ruta") or "")
                    ctx["certificado_guardado"] = bool(ruta_guardada and Path(ruta_guardada).is_file())
                    return render_template("admin/admin_facturacion_configuracion.html", **ctx)

            datos = {
                "modo_envio": "SUNAT_BETA",
                "ruc": request.form.get("ruc", ""),
                "razon_social": request.form.get("razon_social", ""),
                "nombre_comercial": request.form.get("nombre_comercial", ""),
                "direccion": request.form.get("direccion", ""),
                "serie_boleta": request.form.get("serie_boleta", ""),
                "serie_factura": request.form.get("serie_factura", ""),
                "usuario_sol": request.form.get("usuario_sol", ""),
                "clave_sol": request.form.get("clave_sol", ""),
                "certificado_ruta": certificado_ruta,
                "certificado_clave": request.form.get("certificado_clave", ""),
                "endpoint_beta": request.form.get("endpoint_beta", ""),
            }
            resultado = actualizar_configuracion_facturacion(datos)
            if resultado.get("ok"):
                flash(resultado.get("mensaje"), "success")
                return redirect(url_for("admin_facturacion_configuracion"))
            flash(resultado.get("mensaje", "No se pudo guardar la configuracion."), "error")
            config_actual = {**config_actual, **datos}

        ctx = contexto_base("Configuracion SUNAT", "admin_facturacion_configuracion", es_admin=True)
        ctx["config"] = config_actual
        ruta_guardada = str(config_actual.get("certificado_ruta") or "")
        ctx["certificado_guardado"] = bool(ruta_guardada and Path(ruta_guardada).is_file())
        return render_template("admin/admin_facturacion_configuracion.html", **ctx)
    except Exception as e:
        print("Error en /admin/facturacion/configuracion:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/facturacion/emitir/<int:comprobante_pago_id>",
           methods=["POST"], endpoint="admin_emitir_comprobante_fiscal")
def admin_emitir_comprobante_fiscal(comprobante_pago_id):
    try:
        tipo = request.form.get("tipo_comprobante", "").strip()
        usuario = session.get("profile", {}) or {}
        resultado = emitir_comprobante_fiscal_desde_interno(
            comprobante_pago_id,
            tipo,
            usuario.get("matricula", "admin"),
            usuario.get("nombre", "Administrador CCPL"),
        )
        if resultado.get("ok"):
            flash("Comprobante fiscal creado correctamente.", "success")
            return redirect(url_for(
                "admin_comprobante_fiscal",
                fiscal_id=resultado.get("comprobante_id")
            ))
        return mostrar_error(resultado.get("mensaje", "No se pudo emitir el comprobante fiscal."))
    except Exception as e:
        print("Error en /admin/facturacion/emitir:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/facturacion/<int:fiscal_id>",
           endpoint="admin_comprobante_fiscal")
def admin_comprobante_fiscal(fiscal_id):
    try:
        data = leer_comprobante_fiscal_admin(fiscal_id)
        if not data.get("comprobante"):
            return mostrar_error("No se encontro el comprobante fiscal.", 404)
        comprobante = data["comprobante"]
        ctx = contexto_base("Comprobante Fiscal", "admin_facturacion", es_admin=True)
        ctx.update(data)
        config_facturacion = obtener_configuracion_facturacion() or {}
        ctx["config_facturacion"] = config_facturacion
        ctx["numero_comprobante"] = (
            str(comprobante.get("serie") or "") + "-" +
            str(comprobante.get("numero") or 0).zfill(8)
        )
        ctx["numero_interno"] = (
            str(comprobante.get("interno_serie") or "") + "-" +
            str(comprobante.get("interno_numero") or 0).zfill(8)
        )
        ctx["tipo_codigo_sunat"] = _tipo_comprobante_sunat_codigo(
            comprobante.get("tipo_comprobante")
        )
        ctx["qr_fiscal"] = _qr_comprobante_fiscal(
            config_facturacion,
            comprobante,
            ctx["numero_comprobante"]
        )
        return render_template("admin/admin_comprobante_fiscal.html", **ctx)
    except Exception as e:
        print("Error en /admin/facturacion/detalle:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/facturacion/<int:fiscal_id>/enviar-sunat",
           methods=["POST"], endpoint="admin_enviar_comprobante_fiscal")
def admin_enviar_comprobante_fiscal(fiscal_id):
    try:
        usuario = session.get("profile", {}) or {}
        resultado = enviar_comprobante_fiscal_sunat(
            fiscal_id,
            usuario.get("matricula", "admin"),
            usuario.get("nombre", "Administrador CCPL"),
        )
        if resultado.get("ok"):
            flash(resultado.get("mensaje", "Envio SUNAT registrado."), "success")
            return redirect(url_for("admin_comprobante_fiscal", fiscal_id=fiscal_id))
        return mostrar_error(resultado.get("mensaje", "No se pudo enviar el comprobante fiscal."))
    except Exception as e:
        print("Error en /admin/facturacion/enviar-sunat:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/facturacion/<int:fiscal_id>/anular",
           methods=["POST"], endpoint="admin_anular_comprobante_fiscal")
def admin_anular_comprobante_fiscal(fiscal_id):
    try:
        motivo = request.form.get("motivo", "").strip()
        if len(motivo) < 5:
            return mostrar_error("Ingrese un motivo de anulacion mas detallado.")
        usuario = session.get("profile", {}) or {}
        resultado = anular_comprobante_fiscal(
            fiscal_id,
            usuario.get("matricula", "admin"),
            usuario.get("nombre", "Administrador CCPL"),
            motivo
        )
        if resultado.get("ok"):
            flash("Comprobante fiscal anulado correctamente.", "success")
            return redirect(url_for("admin_comprobante_fiscal", fiscal_id=fiscal_id))
        return mostrar_error(resultado.get("mensaje", "No se pudo anular el comprobante fiscal."))
    except Exception as e:
        print("Error en /admin/facturacion/anular:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/medios-pago", endpoint="admin_medios_pago")
def admin_medios_pago():
    try:
        ctx = contexto_base("Medios de pago", "admin_medios_pago", es_admin=True)
        ctx["medios"] = leer_medios_pago() or []
        return render_template("admin/admin_medios_pago.html", **ctx)
    except Exception as e:
        print("Error en /admin/medios-pago:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/medios-pago/nuevo", methods=["POST"], endpoint="admin_nuevo_medio_pago")
def admin_nuevo_medio_pago():
    try:
        nombre = request.form.get("nombre", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        numero_cuenta = request.form.get("numero_cuenta", "").strip()
        titular = request.form.get("titular", "").strip()
        activo = request.form.get("activo", "1").strip()

        if not nombre:
            return mostrar_error("Ingrese el nombre del medio de pago.")
        if not numero_cuenta:
            return mostrar_error("Ingrese el numero o identificador de cuenta.")
        if not titular:
            return mostrar_error("Ingrese el titular del medio de pago.")
        if activo not in ["0", "1"]:
            return mostrar_error("Seleccione un estado valido.")

        obj = clsMedioPago(0, nombre, descripcion, numero_cuenta, titular, int(activo))
        if insertar_medio_pago(obj):
            return mostrar_exito("El medio de pago fue registrado correctamente.",
                                 "admin_medios_pago",
                                 "Ver medios")
        return mostrar_error("No se pudo registrar el medio de pago.")
    except Exception as e:
        print("Error en /admin/medios-pago/nuevo:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/medios-pago/<int:medio_id>/editar",
           methods=["POST"], endpoint="admin_actualizar_medio_pago")
def admin_actualizar_medio_pago(medio_id):
    try:
        nombre = request.form.get("nombre", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        numero_cuenta = request.form.get("numero_cuenta", "").strip()
        titular = request.form.get("titular", "").strip()
        activo = request.form.get("activo", "1").strip()

        if not nombre:
            return mostrar_error("Ingrese el nombre del medio de pago.")
        if not numero_cuenta:
            return mostrar_error("Ingrese el numero o identificador de cuenta.")
        if not titular:
            return mostrar_error("Ingrese el titular del medio de pago.")
        if activo not in ["0", "1"]:
            return mostrar_error("Seleccione un estado valido.")

        obj = clsMedioPago(medio_id, nombre, descripcion, numero_cuenta, titular, int(activo))
        if actualizar_medio_pago(obj):
            return mostrar_exito("El medio de pago fue actualizado correctamente.",
                                 "admin_medios_pago",
                                 "Ver medios")
        return mostrar_error("No se pudo actualizar el medio de pago.")
    except Exception as e:
        print("Error en /admin/medios-pago/editar:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/medios-pago/<int:medio_id>/eliminar",
           methods=["POST"], endpoint="admin_eliminar_medio_pago")
def admin_eliminar_medio_pago(medio_id):
    try:
        if eliminar_medio_pago(medio_id):
            return mostrar_exito("El medio de pago fue eliminado correctamente.",
                                 "admin_medios_pago",
                                 "Ver medios")
        return mostrar_error("No se pudo eliminar el medio de pago.")
    except Exception as e:
        print("Error en /admin/medios-pago/eliminar:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/evidencias-pago", endpoint="admin_evidencias_pago")
def admin_evidencias_pago():
    try:
        filtro = request.args.get("estado", "").strip()
        if filtro not in ["", "Pendiente", "Aprobado", "Rechazado"]:
            filtro = ""

        ctx = contexto_base("Evidencias de pago", "admin_evidencias_pago", es_admin=True)
        ctx["evidencias"] = leer_evidencias_pago(p_estado=filtro) or []
        ctx["filtro"] = filtro
        return render_template("admin/admin_evidencias_pago.html", **ctx)
    except Exception as e:
        print("Error en /admin/evidencias-pago:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/evidencias-pago/<int:evidencia_id>/estado",
           methods=["POST"], endpoint="admin_estado_evidencia_pago")
def admin_estado_evidencia_pago(evidencia_id):
    try:
        estado = request.form.get("estado", "").strip()
        if estado not in ["Aprobado", "Rechazado"]:
            return mostrar_error("Seleccione un estado valido para la evidencia.")

        profile = session.get("profile", {})
        admin_matricula = profile.get("matricula", "admin")
        admin_nombre = profile.get("nombre", "Administrador CCPL")
        detalle_revision = request.form.get("detalle_revision", "").strip()

        resultado = actualizar_estado_evidencia_pago(
            evidencia_id,
            estado,
            admin_matricula,
            admin_nombre,
            detalle_revision
        )
        if resultado.get("ok"):
            mensaje = "La evidencia fue aprobada, la cuota se marco como pagada y se genero comprobante."
            if estado == "Rechazado":
                mensaje = "La evidencia fue anulada correctamente."
            return mostrar_exito(mensaje,
                                 "admin_evidencias_pago",
                                 "Ver evidencias")
        return mostrar_error(resultado.get(
            "mensaje",
            "No se pudo actualizar la evidencia. Verifique que siga pendiente."
        ))
    except Exception as e:
        print("Error en /admin/evidencias-pago/estado:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/cursos", endpoint="admin_cursos")
def admin_cursos():
    try:
        filtro = request.args.get("estado", "").strip()
        ctx = contexto_base("Cursos", "admin_cursos", es_admin=True)
        ctx["cursos"] = leer_cursos(filtro) or []
        ctx["ponentes"] = PONENTES_CURSO
        ctx["filtro"] = filtro
        return render_template("admin/admin_cursos.html", **ctx)
    except Exception as e:
        print("Error en /admin/cursos:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/cursos-asignados", endpoint="admin_cursos_asignados")
def admin_cursos_asignados():
    try:
        busqueda = request.args.get("q", "").strip()
        filtro_legacy = request.args.get("matricula", "").strip()
        if filtro_legacy and not busqueda:
            busqueda = filtro_legacy

        try:
            pagina = int(request.args.get("pagina", "1"))
        except ValueError:
            pagina = 1
        pagina = max(1, pagina)

        try:
            por_pagina = int(request.args.get("por_pagina", "25"))
        except ValueError:
            por_pagina = 25
        if por_pagina not in [10, 25, 50]:
            por_pagina = 25

        total_registros = contar_inscripciones_curso(
            p_busqueda=busqueda or None
        )
        total_paginas = max(1, (total_registros + por_pagina - 1) // por_pagina)
        pagina = min(pagina, total_paginas)
        offset = (pagina - 1) * por_pagina

        ctx = contexto_base("Cursos asignados", "admin_cursos_asignados", es_admin=True)
        ctx["cursos"] = leer_cursos("Activo") or []
        inscripciones = [
            dict(i) for i in (leer_inscripciones_curso(
                p_busqueda=busqueda or None,
                p_limite=por_pagina,
                p_offset=offset
            ) or [])
        ]
        for inscripcion in inscripciones:
            inscripcion["certificado_habilitado"] = _certificado_habilitado(inscripcion)
            inscripcion["certificado_existe"] = _archivo_estatico_existe(
                inscripcion.get("certificado")
            )
        desde = 0 if total_registros == 0 else offset + 1
        hasta = min(offset + len(inscripciones), total_registros)

        ctx["inscripciones"] = inscripciones
        ctx["busqueda"] = busqueda
        ctx["filtro"] = busqueda
        ctx["por_pagina"] = por_pagina
        ctx["resumen_inscripciones"] = resumir_inscripciones_curso(
            p_busqueda=busqueda or None
        )
        ctx["paginacion"] = {
            "pagina": pagina,
            "por_pagina": por_pagina,
            "total": total_registros,
            "total_paginas": total_paginas,
            "desde": desde,
            "hasta": hasta,
            "inicio": max(1, pagina - 2),
            "fin": min(total_paginas, pagina + 2),
        }
        return render_template("admin/admin_cursos_asignados.html", **ctx)
    except Exception as e:
        print("Error en /admin/cursos-asignados:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/cursos-asignados/nuevo", methods=["POST"], endpoint="admin_nueva_inscripcion_curso")
def admin_nueva_inscripcion_curso():
    try:
        matricula = request.form.get("matricula", "").strip()
        curso_id = request.form.get("curso_id", "").strip()
        estado_pago = request.form.get("estado_pago", "Pendiente").strip()

        if not matricula or not curso_id:
            return mostrar_error("Seleccione el colegiado y el curso.")
        if estado_pago not in ["Pendiente", "Pagado"]:
            return mostrar_error("Seleccione un estado de pago valido.")

        try:
            curso_id_num = int(curso_id)
        except ValueError:
            return mostrar_error("Seleccione un curso valido.")

        mensaje = validar_inscripcion_curso(matricula, curso_id_num)
        if mensaje:
            return mostrar_error(mensaje)

        if insertar_inscripcion_curso(matricula, curso_id_num, estado_pago):
            curso = leer_curso_por_id(curso_id_num) or {}
            titulo = curso.get("titulo", "curso seleccionado")
            _notificar_colegiado(
                matricula,
                "curso",
                "Curso asignado",
                "Administracion te asigno al curso " + titulo + ".",
                "educacion_continua",
                "Ver curso",
                "curso",
                curso_id_num
            )
            if estado_pago == "Pendiente":
                _notificar_colegiado(
                    matricula,
                    "cuota",
                    "Cuota de curso pendiente",
                    "Tienes una cuota pendiente por el curso " + titulo + ".",
                    "estado_cuenta",
                    "Ver pago",
                    "curso",
                    curso_id_num
                )
            return mostrar_exito("La inscripcion fue registrada y se genero la cuota del curso.",
                                 "admin_cursos_asignados",
                                 "Ver asignaciones")
        return mostrar_error("No se pudo registrar la inscripcion del curso.")
    except Exception as e:
        print("Error en /admin/cursos-asignados/nuevo:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/cursos-asignados/<int:inscripcion_id>/actualizar",
           methods=["POST"], endpoint="admin_actualizar_curso_asignado")
def admin_actualizar_curso_asignado(inscripcion_id):
    try:
        estado_pago = request.form.get("estado_pago", "").strip()

        if estado_pago not in ["Pendiente", "Pagado"]:
            return mostrar_error("Seleccione un estado de pago valido.")

        if actualizar_pago_inscripcion_curso(inscripcion_id, estado_pago):
            return mostrar_exito("El estado de pago del curso fue actualizado.",
                                 "admin_cursos_asignados",
                                 "Ver asignaciones")
        return mostrar_error("No se pudo actualizar el estado de pago del curso.")
    except Exception as e:
        print("Error en /admin/cursos-asignados/actualizar:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/cursos-asignados/<int:inscripcion_id>/finalizar",
           methods=["POST"], endpoint="admin_finalizar_curso_asignado")
def admin_finalizar_curso_asignado(inscripcion_id):
    try:
        return mostrar_error("El progreso del curso lo actualiza el ponente.")
    except Exception as e:
        print("Error en /admin/cursos-asignados/finalizar:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/cursos-asignados/<int:inscripcion_id>/certificado",
           methods=["POST"], endpoint="admin_registrar_certificado_curso")
def admin_registrar_certificado_curso(inscripcion_id):
    try:
        estado_certificado = leer_estado_certificado_curso(inscripcion_id)
        if not estado_certificado:
            return mostrar_error("No se encontro la inscripcion del curso.", 404)
        if not _certificado_habilitado(estado_certificado):
            return mostrar_error("Solo se puede registrar certificado con pago pagado y progreso 100%.")

        archivo = request.files.get("certificado_archivo")
        certificado = _guardar_archivo_subido(archivo,
                                              "certificados",
                                              EXTENSIONES_ARCHIVO)

        if certificado is None:
            return mostrar_error("El certificado debe ser una imagen o PDF.")
        if not certificado:
            return mostrar_error("Seleccione el archivo del certificado.")

        if actualizar_certificado_curso(inscripcion_id, certificado):
            detalle = leer_inscripcion_detalle(inscripcion_id) or {}
            _notificar_colegiado(
                detalle.get("matricula"),
                "curso",
                "Certificado disponible",
                "Ya puedes ver el certificado del curso " +
                str(detalle.get("titulo", "")) + ".",
                "educacion_continua",
                "Ver certificado",
                "certificado",
                inscripcion_id
            )
            return mostrar_exito("El certificado fue registrado correctamente.",
                                 "admin_cursos_asignados",
                                 "Ver asignaciones")
        return mostrar_error("Solo se puede registrar certificado con pago pagado y progreso 100%.")
    except Exception as e:
        print("Error en /admin/cursos-asignados/certificado:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/cursos/nuevo", methods=["POST"], endpoint="admin_nuevo_curso")
def admin_nuevo_curso():
    try:
        categoria = request.form.get("categoria", "").strip()
        titulo = request.form.get("titulo", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        monto = request.form.get("monto", "").strip()
        monto_inhabil = request.form.get("monto_inhabil", "").strip()
        ponente = request.form.get("ponente", "").strip()
        modalidad = request.form.get("modalidad", "").strip()
        duracion_horas = request.form.get("duracion_horas", "").strip()
        fecha_inicio = request.form.get("fecha_inicio", "").strip()
        fecha_fin = request.form.get("fecha_fin", "").strip()
        cupos = request.form.get("cupos", "").strip()
        estado = request.form.get("estado", "").strip()

        if not all([categoria, titulo, monto, monto_inhabil, ponente, modalidad,
                    duracion_horas, fecha_inicio, fecha_fin, cupos,
                    estado]):
            return mostrar_error("Complete los campos obligatorios del curso.")
        if estado not in ["Activo", "Inactivo"]:
            return mostrar_error("Seleccione un estado valido para el curso.")
        if modalidad not in ["Presencial", "Virtual", "Mixta"]:
            return mostrar_error("Seleccione una modalidad valida.")
        if ponente not in PONENTES_CURSO:
            return mostrar_error("Seleccione un ponente valido.")

        try:
            monto_num = float(monto)
            monto_inhabil_num = float(monto_inhabil)
            duracion_num = int(duracion_horas)
            cupos_num = int(cupos)
        except ValueError:
            return mostrar_error("Montos, duracion y cupos deben ser valores numericos.")

        if monto_num <= 0:
            return mostrar_error("El precio habil del curso debe ser mayor a 0.")
        if monto_inhabil_num < monto_num:
            return mostrar_error("El precio inhabil debe ser mayor o igual al precio habil.")
        if duracion_num <= 0:
            return mostrar_error("La duracion debe ser mayor a 0 horas.")
        if cupos_num <= 0:
            return mostrar_error("Los cupos deben ser mayores a 0.")

        fecha_inicio_obj = _leer_fecha_iso(fecha_inicio)
        fecha_fin_obj = _leer_fecha_iso(fecha_fin)
        if not fecha_inicio_obj or not fecha_fin_obj:
            return mostrar_error("Ingrese fechas validas para el curso.")
        if fecha_fin_obj < fecha_inicio_obj:
            return mostrar_error("La fecha fin no puede ser menor que la fecha inicio.")

        fecha_evento = _resumen_fecha_curso(fecha_inicio, fecha_fin)

        obj = clsCurso(0, categoria, titulo, descripcion, fecha_evento, estado,
                       monto_num, ponente, modalidad, duracion_num,
                       fecha_inicio, fecha_fin, cupos_num, monto_inhabil_num)
        if insertar_curso(obj):
            return mostrar_exito("El curso fue creado correctamente.",
                                 "admin_cursos",
                                 "Ver cursos")
        return mostrar_error("No se pudo crear el curso.")
    except Exception as e:
        print("Error en /admin/cursos/nuevo:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/cursos/<int:curso_id>/editar", methods=["POST"], endpoint="admin_actualizar_curso")
def admin_actualizar_curso(curso_id):
    try:
        if curso_ya_finalizo(curso_id):
            return mostrar_error("No se puede editar un curso que ya finalizo.")

        categoria = request.form.get("categoria", "").strip()
        titulo = request.form.get("titulo", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        monto = request.form.get("monto", "").strip()
        monto_inhabil = request.form.get("monto_inhabil", "").strip()
        ponente = request.form.get("ponente", "").strip()
        modalidad = request.form.get("modalidad", "").strip()
        duracion_horas = request.form.get("duracion_horas", "").strip()
        fecha_inicio = request.form.get("fecha_inicio", "").strip()
        fecha_fin = request.form.get("fecha_fin", "").strip()
        cupos = request.form.get("cupos", "").strip()
        estado = request.form.get("estado", "").strip()

        if not all([categoria, titulo, monto, monto_inhabil, ponente, modalidad,
                    duracion_horas, fecha_inicio, fecha_fin, cupos,
                    estado]):
            return mostrar_error("Complete los campos obligatorios del curso.")
        if estado not in ["Activo", "Inactivo"]:
            return mostrar_error("Seleccione un estado valido para el curso.")
        if modalidad not in ["Presencial", "Virtual", "Mixta"]:
            return mostrar_error("Seleccione una modalidad valida.")
        if ponente not in PONENTES_CURSO:
            return mostrar_error("Seleccione un ponente valido.")

        try:
            monto_num = float(monto)
            monto_inhabil_num = float(monto_inhabil)
            duracion_num = int(duracion_horas)
            cupos_num = int(cupos)
        except ValueError:
            return mostrar_error("Montos, duracion y cupos deben ser valores numericos.")

        if monto_num <= 0:
            return mostrar_error("El precio habil del curso debe ser mayor a 0.")
        if monto_inhabil_num < monto_num:
            return mostrar_error("El precio inhabil debe ser mayor o igual al precio habil.")
        if duracion_num <= 0:
            return mostrar_error("La duracion debe ser mayor a 0 horas.")
        if cupos_num <= 0:
            return mostrar_error("Los cupos deben ser mayores a 0.")

        inscritos_actuales = contar_inscritos_curso(curso_id)
        if cupos_num < inscritos_actuales:
            return mostrar_error("No puede reducir los cupos por debajo de los colegiados inscritos.")

        fecha_inicio_obj = _leer_fecha_iso(fecha_inicio)
        fecha_fin_obj = _leer_fecha_iso(fecha_fin)
        if not fecha_inicio_obj or not fecha_fin_obj:
            return mostrar_error("Ingrese fechas validas para el curso.")
        if fecha_fin_obj < fecha_inicio_obj:
            return mostrar_error("La fecha fin no puede ser menor que la fecha inicio.")

        fecha_evento = _resumen_fecha_curso(fecha_inicio, fecha_fin)

        obj = clsCurso(curso_id, categoria, titulo, descripcion, fecha_evento,
                       estado, monto_num, ponente, modalidad, duracion_num,
                       fecha_inicio, fecha_fin, cupos_num, monto_inhabil_num)
        if actualizar_curso(obj):
            return mostrar_exito("El curso fue actualizado correctamente.",
                                 "admin_cursos",
                                 "Ver cursos")
        return mostrar_error("No se pudo actualizar el curso.")
    except Exception as e:
        print("Error en /admin/cursos/editar:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/cursos/<int:curso_id>/eliminar", methods=["POST"], endpoint="admin_eliminar_curso")
def admin_eliminar_curso(curso_id):
    try:
        if curso_tiene_inscripciones(curso_id):
            return mostrar_error("No se puede eliminar el curso porque tiene colegiados matriculados.")

        if eliminar_curso(curso_id):
            return mostrar_exito("El curso fue eliminado correctamente.",
                                 "admin_cursos",
                                 "Ver cursos")
        return mostrar_error("No se pudo eliminar el curso.")
    except Exception as e:
        print("Error en /admin/cursos/eliminar:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/tramites", endpoint="admin_tramites")
def admin_tramites():
    try:
        filtro = request.args.get("estado", "").strip()
        tipo = request.args.get("tipo", "").strip()
        tipos_validos = [t["codigo"] for t in leer_tipos_tramite()]
        if tipo not in tipos_validos:
            tipo = ""
        ctx = contexto_base("Tramites", "admin_tramites", es_admin=True)
        ctx["tramites"] = leer_tramites(filtro, p_tipo=tipo) or []
        for tramite in ctx["tramites"]:
            tramite["archivo_respuesta_existe"] = _archivo_estatico_existe(
                tramite.get("archivo_respuesta")
            )
            tramite["archivo_solicitud_existe"] = _archivo_estatico_existe(
                tramite.get("archivo_solicitud")
            )
        ctx["filtro"] = filtro
        ctx["tipo_filtro"] = tipo
        ctx["tipos_tramite"] = leer_tipos_tramite()
        return render_template("admin/admin_tramites.html", **ctx)
    except Exception as e:
        print("Error en /admin/tramites:", repr(e))
        return render_template("error500.html")


@app.route("/admin/tramites/<int:tid>/certificado-habilidad",
           endpoint="admin_certificado_habilidad_borrador")
def admin_certificado_habilidad_borrador(tid):
    try:
        certificado, tramite, mensaje, status = _datos_certificado_habilidad(tid)
        if mensaje:
            return mostrar_error(mensaje, status)
        return render_template(
            "admin/certificado_habilidad_borrador.html",
            page_title="Borrador certificado de habilidad",
            certificado=certificado,
            pdf_url=url_for("admin_certificado_habilidad_pdf", tid=tid)
        )
    except Exception as e:
        print("Error en /admin/tramites/certificado-habilidad:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/tramites/<int:tid>/certificado-habilidad/pdf",
           endpoint="admin_certificado_habilidad_pdf")
def admin_certificado_habilidad_pdf(tid):
    try:
        certificado, tramite, mensaje, status = _datos_certificado_habilidad(tid)
        if mensaje:
            return mostrar_error(mensaje, status)
        if request.args.get("modo") == "firma":
            certificado["estado_firma"] = "FIRMA DIGITAL eDNI"

        pdf_bytes = _generar_pdf_certificado_habilidad(certificado)
        if not pdf_bytes:
            return mostrar_error("No se pudo generar el PDF. Verifique que la libreria fpdf este instalada.")

        nombre = f"certificado_habilidad_{certificado['matricula']}_{certificado['numero']}.pdf"
        return Response(
            pdf_bytes,
            mimetype="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{nombre}"',
                "Cache-Control": "no-store",
            }
        )
    except Exception as e:
        print("Error en /admin/tramites/certificado-habilidad/pdf:", repr(e))
        return render_template("error500.html"), 500


def _consultar_firmador_edni(ruta="/estado", payload=None, timeout=8):
    import firmador_edni_local

    cliente = firmador_edni_local.app.test_client()
    if payload is None:
        respuesta = cliente.get(ruta)
    else:
        respuesta = cliente.post(ruta, json=payload)

    data = respuesta.get_json(silent=True)
    if data is None:
        data = {
            "code": 0,
            "message": "El modulo de firma eDNI no devolvio una respuesta valida.",
        }
    return data, respuesta.status_code


@app.route("/admin/firmador-edni/estado", endpoint="admin_firmador_edni_estado")
def admin_firmador_edni_estado():
    try:
        data, status = _consultar_firmador_edni()
        return jsonify(data), status
    except Exception as exc:
        return jsonify({
            "code": 0,
            "message": "No se pudo verificar el modulo de firma eDNI.",
            "detalle": str(exc),
            "lectores": 0,
            "dni_insertado": False,
        }), 500


@app.route("/admin/firmador-edni/firmar", methods=["POST"], endpoint="admin_firmador_edni_firmar")
def admin_firmador_edni_firmar():
    try:
        data, status = _consultar_firmador_edni("/firmar", request.get_json(silent=True) or {})
        return jsonify(data), status
    except Exception as exc:
        return jsonify({
            "code": 0,
            "message": "No se pudo ejecutar la firma eDNI desde el sistema.",
            "detalle": str(exc),
        }), 500


@app.route("/admin/tramites/<int:tid>/firma-edni",
           endpoint="admin_firma_edni")
def admin_firma_edni(tid):
    try:
        certificado, tramite, mensaje, status = _datos_certificado_habilidad(tid)
        if mensaje:
            return mostrar_error(mensaje, status)

        ctx = contexto_base("Firma eDNI", "admin_tramites", es_admin=True)
        ctx["tramite"] = tramite
        ctx["certificado"] = certificado
        ctx["pdf_url"] = url_for("admin_certificado_habilidad_pdf", tid=tid, modo="firma")
        ctx["guardar_url"] = url_for("admin_guardar_firma_edni", tid=tid)
        firmador_local_url = os.getenv(
            "EDNI_FIRMADOR_LOCAL_URL",
            "http://127.0.0.1:8765"
        ).rstrip("/")
        ctx["firmador_base_url"] = firmador_local_url
        ctx["firmador_estado_url"] = f"{firmador_local_url}/estado"
        ctx["firmador_firma_url"] = f"{firmador_local_url}/firmar"
        ctx["firmador_descarga_url"] = url_for(
            "static",
            filename="descargas/firmador_edni_ccpl.zip"
        )
        ctx["driver_reniec_url"] = "https://identidad.reniec.gob.pe/dni-electronico"
        return render_template("admin/admin_firma_edni.html", **ctx)
    except Exception as e:
        print("Error en /admin/tramites/firma-edni:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/tramites/<int:tid>/firma-edni/guardar",
           methods=["POST"], endpoint="admin_guardar_firma_edni")
def admin_guardar_firma_edni(tid):
    try:
        tramite = leer_tramite_por_id(tid)
        if not tramite:
            return jsonify({"code": 0, "message": "El tramite no existe."}), 404
        if tramite.get("tipo_tramite") != "certificado_habilidad":
            return jsonify({"code": 0, "message": "Solo se registra firma eDNI para certificados de habilidad."}), 400

        data = request.get_json(silent=True) or {}
        pdf_base64 = (data.get("archivo_pdf_base64") or "").strip()
        if "," in pdf_base64:
            pdf_base64 = pdf_base64.split(",", 1)[1]
        try:
            pdf_bytes = base64.b64decode(pdf_base64, validate=True)
        except Exception:
            pdf_bytes = b""
        if not pdf_bytes.startswith(b"%PDF"):
            return jsonify({"code": 0, "message": "El firmador eDNI no devolvio un PDF valido."}), 400

        nombre_original = secure_filename(data.get("nombre_archivo") or f"certificado_{tid}_firmado.pdf")
        if not nombre_original.lower().endswith(".pdf"):
            nombre_original += ".pdf"
        destino = Path(app.root_path) / "static" / "uploads" / "tramites"
        destino.mkdir(parents=True, exist_ok=True)
        nombre_final = f"{date.today().strftime('%Y%m%d')}_{uuid4().hex[:10]}_{nombre_original}"
        (destino / nombre_final).write_bytes(pdf_bytes)
        archivo_respuesta = f"uploads/tramites/{nombre_final}"

        usuario = session.get("profile", {}) or {}
        detalle = "Certificado firmado con eDNI desde el sistema."

        resultado = actualizar_estado_tramite(
            tid,
            "Aprobado",
            usuario.get("matricula", "admin"),
            usuario.get("nombre", "Administrador CCPL"),
            "Certificado de habilidad firmado y emitido.",
            archivo_respuesta,
            "eDNI",
            "Firmado",
            detalle
        )
        if not resultado.get("ok"):
            return jsonify({"code": 0, "message": resultado.get("mensaje", "No se pudo registrar la firma.")}), 400

        insertar_notificacion_matricula(
            tramite.get("matricula", ""),
            "sistema",
            "Certificado de habilidad emitido",
            "Tu certificado de habilidad ya esta disponible para descargar.",
            "tramites",
            "Ver tramite",
            "tramite",
            tid
        )

        return jsonify({
            "code": 1,
            "message": "Certificado firmado registrado correctamente.",
            "redirect": url_for("admin_tramites")
        })
    except Exception as e:
        print("Error en /admin/tramites/firma-edni/guardar:", repr(e))
        return jsonify({"code": 0, "message": "No se pudo registrar la firma eDNI."}), 500


def _render_validacion_firma_tramite(tid, es_admin=False):
    tramite = leer_tramite_por_id(tid)
    if not tramite:
        return mostrar_error("El tramite seleccionado no existe.", 404)
    if not tramite.get("archivo_respuesta"):
        return mostrar_error("Este tramite aun no tiene un PDF firmado para validar.")

    ruta_pdf = _ruta_archivo_estatico_upload(tramite.get("archivo_respuesta"))
    if not ruta_pdf or not ruta_pdf.is_file():
        return mostrar_error("El PDF firmado no esta disponible en el sistema.", 404)

    activo = "admin_tramites" if es_admin else "tramites"
    ctx = contexto_base("Validar firma", activo, es_admin=es_admin)
    ctx["tramite"] = tramite
    ctx["resultado"] = _validar_firma_pdf(ruta_pdf)
    ctx["pdf_url"] = url_for("static", filename=tramite.get("archivo_respuesta"))
    ctx["volver_url"] = url_for("admin_tramites" if es_admin else "tramites")
    return render_template("admin/admin_validar_firma.html", **ctx)


@app.route("/admin/tramites/<int:tid>/validar-firma",
           endpoint="admin_validar_firma_tramite")
def admin_validar_firma_tramite(tid):
    try:
        return _render_validacion_firma_tramite(tid, es_admin=True)
    except Exception as e:
        print("Error en /admin/tramites/validar-firma:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/tramites/<int:tid>/estado", methods=["POST"], endpoint="admin_estado_tramite")
def admin_estado_tramite(tid):
    try:
        estado = request.form.get("estado", "").strip()
        estados_validos = ["Pendiente", "En Revision", "Aprobado", "Rechazado"]
        if estado not in estados_validos:
            return mostrar_error("Seleccione un estado valido para el tramite.")

        tramite = leer_tramite_por_id(tid)
        if not tramite:
            return mostrar_error("El tramite seleccionado no existe.")

        matricula = tramite.get("matricula", "")
        requiere_sin_deuda = tramite.get("tipo_tramite") in [
            "baja_colegiatura",
            "traslado_colegio",
            "certificado_habilidad",
        ]
        if (
            estado == "Aprobado"
            and requiere_sin_deuda
            and colegiado_tiene_deuda_pendiente_matricula(matricula)
        ):
            return mostrar_error("No se puede aprobar este tramite porque el colegiado tiene cuotas pendientes.")

        if (
            estado == "Aprobado"
            and tramite.get("tipo_tramite") == "certificado_habilidad"
        ):
            return mostrar_error("El certificado de habilidad solo se aprueba firmando con eDNI desde el sistema.")

        if (
            estado == "Aprobado"
            and tramite_requiere_sustento(tramite.get("tipo_tramite"))
            and not _archivo_estatico_existe(tramite.get("archivo_solicitud"))
        ):
            return mostrar_error("No se puede aprobar este tramite porque no tiene documento sustentatorio disponible.")

        archivo_respuesta = ""
        archivo = request.files.get("archivo_respuesta")
        if archivo and archivo.filename:
            archivo_respuesta = _guardar_archivo_subido(
                archivo,
                "tramites",
                EXTENSIONES_ARCHIVO
            )
            if archivo_respuesta is None:
                return mostrar_error("El archivo emitido debe ser una imagen o PDF.")
        requiere_archivo_emitido = tramite.get("tipo_tramite") in ["constancia_colegiatura"]
        if (
            estado == "Aprobado"
            and requiere_archivo_emitido
            and not archivo_respuesta
            and not tramite.get("archivo_respuesta")
        ):
            return mostrar_error("Para aprobar este tramite debe subir el archivo emitido.")

        usuario = session.get("profile", {}) or {}
        detalle_revision = request.form.get("detalle_revision", "").strip()
        resultado = actualizar_estado_tramite(
            tid,
            estado,
            usuario.get("matricula", "admin"),
            usuario.get("nombre", "Administrador CCPL"),
            detalle_revision,
            archivo_respuesta,
            "",
            None,
            ""
        )
        if resultado.get("ok"):
            mensajes_estado = {
                "Pendiente": (
                    "Tramite actualizado",
                    "Tu tramite volvio al estado pendiente."
                ),
                "En Revision": (
                    "Tramite en revision",
                    "Tu tramite esta siendo revisado por administracion."
                ),
                "Aprobado": (
                    "Tramite aprobado",
                    "Tu tramite fue aprobado. Revisa el modulo de Tramites."
                ),
                "Rechazado": (
                    "Tramite rechazado",
                    "Tu tramite fue rechazado. Revisa el historial o comunicate con soporte."
                ),
            }
            titulo, mensaje = mensajes_estado[estado]
            if archivo_respuesta:
                mensaje = "Tu tramite fue atendido y ya tiene un archivo emitido para descargar."
            insertar_notificacion_matricula(
                matricula,
                "sistema",
                titulo,
                mensaje,
                "tramites",
                "Ver tramite",
                "tramite",
                tid
            )
            return mostrar_exito("El tramite fue actualizado correctamente.",
                                 "admin_tramites",
                                 "Ver tramites")
        return mostrar_error(resultado.get("mensaje", "No se pudo actualizar el tramite."))
    except Exception:
        return render_template("error500.html")


@app.route("/admin/tickets", endpoint="admin_tickets")
def admin_tickets():
    try:
        filtro = request.args.get("estado", "").strip()
        ctx = contexto_base("Tickets de Soporte", "admin_tickets", es_admin=True)
        ctx["tickets"] = leer_tickets(filtro) or []
        ctx["filtro"] = filtro
        return render_template("admin/admin_tickets.html", **ctx)
    except Exception as e:
        print("Error en /admin/tickets:", repr(e))
        return render_template("error500.html"), 500


@app.route("/admin/tickets/<int:tid>/estado", methods=["POST"], endpoint="admin_estado_ticket")
def admin_estado_ticket(tid):
    try:
        estado = request.form.get("estado", "").strip()
        respuesta = request.form.get("respuesta", "").strip()
        estados_validos = ["Abierto", "En Revision", "En Revisión", "En atencion", "Cerrado"]
        if estado not in estados_validos:
            return mostrar_error("Seleccione un estado valido para el ticket.")
        estado = "En Revision" if estado in ["En Revisión", "En atencion"] else estado

        ticket = leer_ticket_por_id(tid)
        if not ticket:
            return mostrar_error("El ticket seleccionado no existe.")

        if ticket.get("estado") == "Cerrado" and estado != "Abierto":
            return mostrar_error("El ticket cerrado primero debe reabrirse para modificarlo.")

        respuesta_actual = (ticket.get("respuesta_admin") or "").strip()
        if estado == "Cerrado" and not respuesta and not respuesta_actual:
            return mostrar_error("Para cerrar el ticket debe registrar una respuesta para el colegiado.")

        respuesta_guardar = respuesta if respuesta else None
        if actualizar_estado_ticket(tid, estado, respuesta_guardar):
            titulos = {
                "Abierto": "Ticket actualizado",
                "En Revision": "Ticket en revision",
                "Cerrado": "Ticket cerrado",
            }
            mensajes = {
                "Abierto": "Soporte actualizo tu incidencia.",
                "En Revision": "Tu incidencia esta siendo revisada por soporte.",
                "Cerrado": "Soporte respondio y cerro tu incidencia.",
            }
            if ticket.get("estado") == "Cerrado" and estado == "Abierto":
                titulos["Abierto"] = "Ticket reabierto"
                mensajes["Abierto"] = "Tu incidencia fue reabierta por soporte."
            insertar_notificacion_matricula(
                ticket.get("matricula"),
                "ticket",
                titulos.get(estado, "Ticket actualizado"),
                mensajes.get(estado, "Tu ticket fue actualizado por soporte."),
                "perfil_soporte",
                "Ver ticket",
                "ticket",
                tid
            )
            return mostrar_exito("El estado del ticket fue actualizado.",
                                 "admin_tickets",
                                 "Ver tickets")
        return mostrar_error("No se pudo actualizar el estado del ticket.")
    except Exception as e:
        print("Error en /admin/tickets/estado:", repr(e))
        return render_template("error500.html"), 500


# ============================================================
# APIS
# ============================================================

@app.route("/api/token", methods=["POST"], endpoint="api_token")
def api_token():
    try:
        data = request.get_json(silent=True) or {}
        username = (
            data.get("username")
            or data.get("matricula")
            or data.get("usuario")
            or ""
        ).strip()
        password = (data.get("password") or data.get("clave") or "").strip()
        if not username or not password:
            return _respuesta_api(
                0,
                "Ingrese usuario/matricula y password para generar el token.",
                status=400
            )

        usuario = autenticar_usuario(username, password)
        if not usuario:
            return _respuesta_api(0, "Credenciales incorrectas.", status=401)
        if usuario.get("rol") != "admin":
            return _respuesta_api(
                0,
                "Solo el administrador puede generar token para las APIs.",
                status=403
            )

        token = _generar_token_jwt(usuario)
        token_data = {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": 28800,
            "usuario": {
                "matricula": usuario.get("matricula"),
                "nombre": usuario.get("nombre"),
                "rol": usuario.get("rol"),
            }
        }
        respuesta = jsonify({
            "access_token": token,
            "token_type": "Bearer",
            "code": 1,
            "data": token_data,
            "message": "Token generado correctamente."
        })
        return respuesta, 200
    except Exception as e:
        print("Error en /api/token:", repr(e))
        return _respuesta_api(0, str(e), status=500)

@app.route("/api/colegiados/buscar", endpoint="api_buscar_colegiados")
def api_buscar_colegiados():
    try:
        busqueda = request.args.get("q", "").strip()
        if len(busqueda) < 2:
            return jsonify({"code": 1, "data": [], "message": "Ingrese al menos 2 caracteres."})

        resultado = buscar_colegiados(busqueda, 15) or []
        return jsonify({"code": 1, "data": resultado, "message": ""})
    except Exception as e:
        print("Error en /api/colegiados/buscar:", repr(e))
        return jsonify({"code": 0, "data": [], "message": "No se pudo buscar colegiados."}), 500


@app.route("/api_listar_colegiados")
def api_listar_colegiados():
    try:
        resultado = leer_colegiados()
        return jsonify(resultado)
    except Exception:
        return {"error": "Error al listar colegiados"}


@app.route("/api_guardar_colegiado", methods=["POST"])
def api_guardar_colegiado():
    try:
        obj = clsColegiado(0,
                           request.json["nombre"],
                           request.json["matricula"],
                           request.json["documento"],
                           request.json.get("especialidad"),
                           request.json["correo"],
                           request.json.get("telefono", ""),
                           p_direccion=request.json.get("direccion", "Sin registrar"),
                           p_especialidad_id=request.json.get("especialidad_id"))
        password = request.json.get("password", "cpc123")
        if insertar_colegiado(obj, password):
            return jsonify({"code": 1, "data": {}, "message": "Colegiado insertado correctamente"})
        return jsonify({"code": 0, "data": {}, "message": "Error al insertar colegiado"})
    except Exception as e:
        return jsonify({"code": 0, "data": {}, "message": "Excepcion superior: " + repr(e)})


@app.route("/api_listar_usuarios")
def api_listar_usuarios():
    try:
        resultado = leer_usuarios()
        return jsonify(resultado)
    except Exception:
        return {"error": "Error al listar usuarios"}


@app.route("/api_guardar_usuario", methods=["POST"])
def api_guardar_usuario():
    try:
        obj = clsUsuario(0,
                         request.json["matricula"],
                         request.json["password"],
                         request.json.get("rol", "colegiado"),
                         request.json.get("activo", 1))
        if insertar_usuario(obj):
            return jsonify({"code": 1, "data": {}, "message": "Usuario insertado correctamente"})
        return jsonify({"code": 0, "data": {}, "message": "Error al insertar usuario"})
    except Exception as e:
        return jsonify({"code": 0, "data": {}, "message": "Excepcion superior: " + repr(e)})


@app.route("/api_listar_cuotas")
def api_listar_cuotas():
    try:
        matricula = request.args.get("matricula", "")
        resultado = leer_cuotas(matricula)
        return jsonify(resultado)
    except Exception:
        return {"error": "Error al listar cuotas"}


@app.route("/api_guardar_cuota", methods=["POST"])
def api_guardar_cuota():
    try:
        obj = clsCuota(0,
                       request.json["matricula"],
                       request.json["fecha"],
                       request.json["concepto"],
                       request.json["monto"],
                       request.json.get("estado", "Pendiente"))
        if insertar_cuota(obj):
            return jsonify({"code": 1, "data": {}, "message": "Cuota insertada correctamente"})
        return jsonify({"code": 0, "data": {}, "message": "Error al insertar cuota"})
    except Exception as e:
        return jsonify({"code": 0, "data": {}, "message": "Excepcion superior: " + repr(e)})


@app.route("/api_listar_medios_pago")
def api_listar_medios_pago():
    try:
        solo_activos = request.args.get("solo_activos", "0")
        resultado = leer_medios_pago(solo_activos == "1")
        return jsonify(resultado)
    except Exception:
        return {"error": "Error al listar medios de pago"}


@app.route("/api_guardar_medio_pago", methods=["POST"])
def api_guardar_medio_pago():
    try:
        obj = clsMedioPago(0,
                           request.json["nombre"],
                           request.json.get("descripcion", ""),
                           request.json["numero_cuenta"],
                           request.json["titular"],
                           request.json.get("activo", 1))
        if insertar_medio_pago(obj):
            return jsonify({"code": 1, "data": {}, "message": "Medio de pago insertado correctamente"})
        return jsonify({"code": 0, "data": {}, "message": "Error al insertar medio de pago"})
    except Exception as e:
        return jsonify({"code": 0, "data": {}, "message": "Excepcion superior: " + repr(e)})


@app.route("/api_listar_evidencias_pago")
def api_listar_evidencias_pago():
    try:
        matricula = request.args.get("matricula", "")
        estado = request.args.get("estado", "")
        resultado = leer_evidencias_pago(matricula, estado)
        return jsonify(resultado)
    except Exception:
        return {"error": "Error al listar evidencias de pago"}


@app.route("/api_guardar_evidencia_pago", methods=["POST"])
def api_guardar_evidencia_pago():
    try:
        resultado = registrar_evidencia_pago(request.json["matricula"],
                                            request.json["cuota_id"],
                                            request.json["medio_pago_id"],
                                            request.json["numero_operacion"],
                                            request.json["fecha_pago"],
                                            request.json["monto"],
                                            request.json.get("comentario", ""))
        if resultado == "ok":
            return jsonify({"code": 1, "data": {}, "message": "Evidencia de pago insertada correctamente"})
        return jsonify({"code": 0, "data": {}, "message": resultado})
    except Exception as e:
        return jsonify({"code": 0, "data": {}, "message": "Excepcion superior: " + repr(e)})


@app.route("/api_listar_cursos")
def api_listar_cursos():
    try:
        estado = request.args.get("estado", "")
        resultado = leer_cursos(estado)
        return jsonify(resultado)
    except Exception:
        return {"error": "Error al listar cursos"}


@app.route("/api_guardar_curso", methods=["POST"])
def api_guardar_curso():
    try:
        fecha_inicio = request.json.get("fecha_inicio", "")
        fecha_fin = request.json.get("fecha_fin", "")
        fecha_evento = request.json.get("fecha_evento", "")
        if not fecha_evento and fecha_inicio and fecha_fin:
            fecha_evento = _resumen_fecha_curso(fecha_inicio, fecha_fin)

        obj = clsCurso(0,
                       request.json["categoria"],
                       request.json["titulo"],
                       request.json.get("descripcion", ""),
                       fecha_evento,
                       request.json.get("estado", "Activo"),
                       request.json.get("monto", 0),
                       request.json.get("ponente", ""),
                       request.json.get("modalidad", "Virtual"),
                       request.json.get("duracion_horas", 1),
                       fecha_inicio,
                       fecha_fin,
                       request.json.get("cupos", 1),
                       request.json.get(
                           "monto_inhabil",
                           request.json.get("monto", 0)
                       ))
        if insertar_curso(obj):
            return jsonify({"code": 1, "data": {}, "message": "Curso insertado correctamente"})
        return jsonify({"code": 0, "data": {}, "message": "Error al insertar curso"})
    except Exception as e:
        return jsonify({"code": 0, "data": {}, "message": "Excepcion superior: " + repr(e)})


@app.route("/api_listar_inscripciones_curso")
def api_listar_inscripciones_curso():
    try:
        matricula = request.args.get("matricula", "")
        resultado = leer_inscripciones_curso(matricula)
        return jsonify(resultado)
    except Exception:
        return {"error": "Error al listar inscripciones de curso"}


@app.route("/api_listar_tramites")
def api_listar_tramites():
    try:
        estado = request.args.get("estado", "")
        matricula = request.args.get("matricula", "")
        tipo = request.args.get("tipo", "")
        resultado = leer_tramites(estado, matricula, tipo)
        return jsonify(resultado)
    except Exception:
        return {"error": "Error al listar tramites"}


@app.route("/api_guardar_tramite", methods=["POST"])
def api_guardar_tramite():
    try:
        tipo_tramite = request.json["tipo_tramite"]
        archivo_solicitud = request.json.get("archivo_solicitud", "")
        if tramite_requiere_sustento(tipo_tramite) and not archivo_solicitud:
            return jsonify({
                "code": 0,
                "data": {},
                "message": "Para baja o traslado debe registrar el documento sustentatorio"
            })
        obj = clsTramite(0,
                         request.json["matricula"],
                         request.json["nombre"],
                         tipo_tramite,
                         request.json["asunto"],
                         request.json["descripcion"],
                         archivo_solicitud,
                         request.json.get("estado", "Pendiente"),
                         request.json["fecha_solicitud"])
        if insertar_tramite(obj):
            return jsonify({"code": 1, "data": {}, "message": "Tramite insertado correctamente"})
        return jsonify({"code": 0, "data": {}, "message": "Error al insertar tramite"})
    except Exception as e:
        return jsonify({"code": 0, "data": {}, "message": "Excepcion superior: " + repr(e)})


@app.route("/api_guardar_ticket", methods=["POST"])
def api_guardar_ticket():
    try:
        if insertar_ticket(request.json["matricula"],
                           request.json.get("categoria", "general"),
                           request.json["asunto"],
                           request.json["descripcion"]):
            return jsonify({"code": 1, "data": {}, "message": "Ticket insertado correctamente"})
        return jsonify({"code": 0, "data": {}, "message": "Error al insertar ticket"})
    except Exception as e:
        return jsonify({"code": 0, "data": {}, "message": "Excepcion superior: " + repr(e)})


# ============================================================
# APIS CRUD POR TABLA CON JWT
# ============================================================

API_COLUMNAS_CACHE = {}
API_COLECCION_TABLAS = [
    ("Colegiados", "especialidades_colegiado", "especialidadcolegiado", "especialidadescolegiado"),
    ("Colegiados", "colegiados", "colegiado", "colegiados"),
    ("Colegiados", "usuarios", "usuario", "usuarios"),
    ("Colegiados", "recuperacion_password", "recuperacionpassword", "recuperacionespassword"),
    ("Pagos", "cuotas", "cuota", "cuotas"),
    ("Pagos", "medios_pago", "mediopago", "mediospago"),
    ("Pagos", "evidencias_pago", "evidenciapago", "evidenciaspago"),
    ("Pagos", "transacciones_pago", "transaccionpago", "transaccionespago"),
    ("Pagos", "comprobantes_pago", "comprobantepago", "comprobantespago"),
    ("Mercado Pago", "configuracion_mercado_pago", "configuracionmercadopago", "configuracionesmercadopago"),
    ("Mercado Pago", "ordenes_mercado_pago", "ordenmercadopago", "ordenesmercadopago"),
    ("Facturacion", "configuracion_facturacion", "configuracionfacturacion", "configuracionesfacturacion"),
    ("Facturacion", "comprobantes_fiscales", "comprobantefiscal", "comprobantesfiscales"),
    ("Facturacion", "comprobante_fiscal_detalle", "comprobantefiscaldetalle", "comprobantesfiscalesdetalle"),
    ("Facturacion", "facturacion_sunat_logs", "facturacionsunatlog", "facturacionsunatlogs"),
    ("Cursos", "cursos", "curso", "cursos"),
    ("Cursos", "contenido_curso", "contenidocurso", "contenidoscurso"),
    ("Cursos", "inscripciones_curso", "inscripcioncurso", "inscripcionescurso"),
    ("Tramites y soporte", "tramites", "tramite", "tramites"),
    ("Tramites y soporte", "tickets", "ticket", "tickets"),
    ("Tramites y soporte", "notificaciones", "notificacion", "notificaciones"),
]


def _api_nombre_seguro(nombre):
    if not re.fullmatch(r"[A-Za-z0-9_]+", nombre or ""):
        raise ValueError("Nombre de tabla o columna no permitido.")
    return f"`{nombre}`"


def _api_info_tabla(tabla):
    if tabla in API_COLUMNAS_CACHE:
        return API_COLUMNAS_CACHE[tabla]

    conn = obtenerconexion()
    with conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT COLUMN_NAME, COLUMN_KEY, EXTRA
                  FROM INFORMATION_SCHEMA.COLUMNS
                 WHERE TABLE_SCHEMA = DATABASE()
                   AND TABLE_NAME = %s
                 ORDER BY ORDINAL_POSITION
                """,
                (tabla,)
            )
            columnas = cursor.fetchall() or []

    if not columnas:
        return None

    pk = "id"
    for columna in columnas:
        if columna.get("COLUMN_KEY") == "PRI":
            pk = columna["COLUMN_NAME"]
            break

    info = {
        "tabla": tabla,
        "pk": pk,
        "columnas": [col["COLUMN_NAME"] for col in columnas],
        "auto": {
            col["COLUMN_NAME"]
            for col in columnas
            if "auto_increment" in (col.get("EXTRA") or "")
        },
    }
    API_COLUMNAS_CACHE[tabla] = info
    return info


def _api_valor_json(valor):
    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, (datetime, date)):
        return valor.isoformat()
    return valor


def _api_serializar_fila(fila):
    return {clave: _api_valor_json(valor) for clave, valor in dict(fila).items()}


def _api_body_json():
    data = request.get_json(silent=True)
    if data is None:
        data = request.form.to_dict()
    return data or {}


def _api_id_registro(registro_id=None):
    if registro_id is not None:
        return registro_id
    data = _api_body_json()
    return data.get("id") or request.args.get("id")


def _api_columnas_insertables(info, data):
    excluidas = set(info["auto"])
    excluidas.update([
        "creado_en", "actualizado_en", "revisado_en", "firmado_en",
        "anulado_en", "pagado_en", "enviado_en", "respondido_en",
        "leido_en", "usado_en"
    ])
    return [col for col in info["columnas"] if col in data and col not in excluidas]


def _api_columnas_actualizables(info, data):
    excluidas = set(info["auto"])
    excluidas.add(info["pk"])
    excluidas.add("creado_en")
    return [col for col in info["columnas"] if col in data and col not in excluidas]


def _api_leer_tabla(tabla):
    info = _api_info_tabla(tabla)
    if not info:
        return _respuesta_api(0, "La tabla solicitada no existe.", status=404)

    limite = request.args.get("limit", "").strip()
    sql = (
        f"SELECT * FROM {_api_nombre_seguro(info['tabla'])} "
        f"ORDER BY {_api_nombre_seguro(info['pk'])} DESC"
    )
    params = []
    if limite:
        try:
            limite_num = max(1, min(int(limite), 500))
            sql += " LIMIT %s"
            params.append(limite_num)
        except ValueError:
            return _respuesta_api(0, "El parametro limit debe ser numerico.", status=400)

    conn = obtenerconexion()
    with conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            filas = cursor.fetchall() or []

    return _respuesta_api(
        1,
        "Listado correcto.",
        [_api_serializar_fila(fila) for fila in filas]
    )


def _api_leer_tabla_xid(tabla, registro_id=None):
    info = _api_info_tabla(tabla)
    if not info:
        return _respuesta_api(0, "La tabla solicitada no existe.", status=404)

    registro_id = _api_id_registro(registro_id)
    if not registro_id:
        return _respuesta_api(0, "Debe enviar el id del registro.", status=400)

    sql = (
        f"SELECT * FROM {_api_nombre_seguro(info['tabla'])} "
        f"WHERE {_api_nombre_seguro(info['pk'])} = %s"
    )
    conn = obtenerconexion()
    with conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, (registro_id,))
            fila = cursor.fetchone()

    if not fila:
        return _respuesta_api(0, "No se encontro el registro.", status=404)
    return _respuesta_api(1, "Registro encontrado.", _api_serializar_fila(fila))


def _api_guardar_tabla(tabla):
    info = _api_info_tabla(tabla)
    if not info:
        return _respuesta_api(0, "La tabla solicitada no existe.", status=404)

    data = _api_body_json()
    columnas = _api_columnas_insertables(info, data)
    if not columnas:
        return _respuesta_api(0, "No se recibieron campos validos para guardar.", status=400)

    sql_columnas = ", ".join(_api_nombre_seguro(col) for col in columnas)
    placeholders = ", ".join(["%s"] * len(columnas))
    sql = (
        f"INSERT INTO {_api_nombre_seguro(info['tabla'])} "
        f"({sql_columnas}) VALUES ({placeholders})"
    )
    valores = [data.get(col) for col in columnas]

    try:
        conn = obtenerconexion()
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, valores)
                nuevo_id = cursor.lastrowid
            conn.commit()
        return _respuesta_api(1, "Registro guardado correctamente.", {"id": nuevo_id})
    except pymysql.err.IntegrityError as e:
        return _respuesta_api(0, "Regla de integridad: " + str(e), status=400)
    except Exception as e:
        return _respuesta_api(0, "No se pudo guardar: " + repr(e), status=500)


def _api_actualizar_tabla(tabla, registro_id=None):
    info = _api_info_tabla(tabla)
    if not info:
        return _respuesta_api(0, "La tabla solicitada no existe.", status=404)

    data = _api_body_json()
    registro_id = _api_id_registro(registro_id)
    if not registro_id:
        return _respuesta_api(0, "Debe enviar el id del registro.", status=400)

    columnas = _api_columnas_actualizables(info, data)
    if not columnas:
        return _respuesta_api(0, "No se recibieron campos validos para actualizar.", status=400)

    asignaciones = ", ".join(f"{_api_nombre_seguro(col)} = %s" for col in columnas)
    sql = (
        f"UPDATE {_api_nombre_seguro(info['tabla'])} "
        f"SET {asignaciones} "
        f"WHERE {_api_nombre_seguro(info['pk'])} = %s"
    )
    valores = [data.get(col) for col in columnas] + [registro_id]

    try:
        conn = obtenerconexion()
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, valores)
                filas = cursor.rowcount
            conn.commit()
        return _respuesta_api(1, "Registro actualizado correctamente.", {"filas_afectadas": filas})
    except pymysql.err.IntegrityError as e:
        return _respuesta_api(0, "Regla de integridad: " + str(e), status=400)
    except Exception as e:
        return _respuesta_api(0, "No se pudo actualizar: " + repr(e), status=500)


def _api_eliminar_tabla(tabla, registro_id=None):
    info = _api_info_tabla(tabla)
    if not info:
        return _respuesta_api(0, "La tabla solicitada no existe.", status=404)

    registro_id = _api_id_registro(registro_id)
    if not registro_id:
        return _respuesta_api(0, "Debe enviar el id del registro.", status=400)

    sql = (
        f"DELETE FROM {_api_nombre_seguro(info['tabla'])} "
        f"WHERE {_api_nombre_seguro(info['pk'])} = %s"
    )
    try:
        conn = obtenerconexion()
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (registro_id,))
                filas = cursor.rowcount
            conn.commit()
        return _respuesta_api(1, "Registro eliminado correctamente.", {"filas_afectadas": filas})
    except pymysql.err.IntegrityError as e:
        return _respuesta_api(0, "No se puede eliminar porque tiene registros relacionados: " + str(e), status=400)
    except Exception as e:
        return _respuesta_api(0, "No se pudo eliminar: " + repr(e), status=500)


# ============================================================
# APIS - ESPECIALIDADES_COLEGIADO
# ============================================================

@app.route("/api_guardarespecialidadcolegiado", methods=["POST"])
@jwt_required()
def api_guardarespecialidadcolegiado():
    return _api_guardar_tabla("especialidades_colegiado")


@app.route("/api_actualizarespecialidadcolegiado", methods=["PUT", "POST"])
@app.route("/api_actualizarespecialidadcolegiado/<int:registro_id>", methods=["PUT", "POST"])
@jwt_required()
def api_actualizarespecialidadcolegiado(registro_id=None):
    return _api_actualizar_tabla("especialidades_colegiado", registro_id)


@app.route("/api_eliminarespecialidadcolegiado", methods=["DELETE", "POST"])
@app.route("/api_eliminarespecialidadcolegiado/<int:registro_id>", methods=["DELETE", "POST"])
@jwt_required()
def api_eliminarespecialidadcolegiado(registro_id=None):
    return _api_eliminar_tabla("especialidades_colegiado", registro_id)


@app.route("/api_leerespecialidadcolegiadoxid", methods=["GET", "POST"])
@app.route("/api_leerespecialidadcolegiadoxid/<int:registro_id>", methods=["GET", "POST"])
@jwt_required()
def api_leerespecialidadcolegiadoxid(registro_id=None):
    return _api_leer_tabla_xid("especialidades_colegiado", registro_id)


@app.route("/api_leerespecialidadescolegiado")
@jwt_required()
def api_leerespecialidadescolegiado():
    return _api_leer_tabla("especialidades_colegiado")


# ============================================================
# APIS - COLEGIADOS
# ============================================================

@app.route("/api_guardarcolegiado", methods=["POST"])
@jwt_required()
def api_guardarcolegiado():
    return _api_guardar_tabla("colegiados")


@app.route("/api_actualizarcolegiado", methods=["PUT", "POST"])
@app.route("/api_actualizarcolegiado/<int:registro_id>", methods=["PUT", "POST"])
@jwt_required()
def api_actualizarcolegiado(registro_id=None):
    return _api_actualizar_tabla("colegiados", registro_id)


@app.route("/api_eliminarcolegiado", methods=["DELETE", "POST"])
@app.route("/api_eliminarcolegiado/<int:registro_id>", methods=["DELETE", "POST"])
@jwt_required()
def api_eliminarcolegiado(registro_id=None):
    return _api_eliminar_tabla("colegiados", registro_id)


@app.route("/api_leercolegiadoxid", methods=["GET", "POST"])
@app.route("/api_leercolegiadoxid/<int:registro_id>", methods=["GET", "POST"])
@jwt_required()
def api_leercolegiadoxid(registro_id=None):
    return _api_leer_tabla_xid("colegiados", registro_id)


@app.route("/api_leercolegiados")
@jwt_required()
def api_leercolegiados():
    return _api_leer_tabla("colegiados")


# ============================================================
# APIS - USUARIOS
# ============================================================

@app.route("/api_guardarusuario", methods=["POST"])
@jwt_required()
def api_guardarusuario():
    return _api_guardar_tabla("usuarios")


@app.route("/api_actualizarusuario", methods=["PUT", "POST"])
@app.route("/api_actualizarusuario/<int:registro_id>", methods=["PUT", "POST"])
@jwt_required()
def api_actualizarusuario(registro_id=None):
    return _api_actualizar_tabla("usuarios", registro_id)


@app.route("/api_eliminarusuario", methods=["DELETE", "POST"])
@app.route("/api_eliminarusuario/<int:registro_id>", methods=["DELETE", "POST"])
@jwt_required()
def api_eliminarusuario(registro_id=None):
    return _api_eliminar_tabla("usuarios", registro_id)


@app.route("/api_leerusuarioxid", methods=["GET", "POST"])
@app.route("/api_leerusuarioxid/<int:registro_id>", methods=["GET", "POST"])
@jwt_required()
def api_leerusuarioxid(registro_id=None):
    return _api_leer_tabla_xid("usuarios", registro_id)


@app.route("/api_leerusuarios")
@jwt_required()
def api_leerusuarios():
    return _api_leer_tabla("usuarios")


# ============================================================
# APIS - RECUPERACION_PASSWORD
# ============================================================

@app.route("/api_guardarrecuperacionpassword", methods=["POST"])
@jwt_required()
def api_guardarrecuperacionpassword():
    return _api_guardar_tabla("recuperacion_password")


@app.route("/api_actualizarrecuperacionpassword", methods=["PUT", "POST"])
@app.route("/api_actualizarrecuperacionpassword/<int:registro_id>", methods=["PUT", "POST"])
@jwt_required()
def api_actualizarrecuperacionpassword(registro_id=None):
    return _api_actualizar_tabla("recuperacion_password", registro_id)


@app.route("/api_eliminarrecuperacionpassword", methods=["DELETE", "POST"])
@app.route("/api_eliminarrecuperacionpassword/<int:registro_id>", methods=["DELETE", "POST"])
@jwt_required()
def api_eliminarrecuperacionpassword(registro_id=None):
    return _api_eliminar_tabla("recuperacion_password", registro_id)


@app.route("/api_leerrecuperacionpasswordxid", methods=["GET", "POST"])
@app.route("/api_leerrecuperacionpasswordxid/<int:registro_id>", methods=["GET", "POST"])
@jwt_required()
def api_leerrecuperacionpasswordxid(registro_id=None):
    return _api_leer_tabla_xid("recuperacion_password", registro_id)


@app.route("/api_leerrecuperacionespassword")
@jwt_required()
def api_leerrecuperacionespassword():
    return _api_leer_tabla("recuperacion_password")


# ============================================================
# APIS - CUOTAS
# ============================================================

@app.route("/api_guardarcuota", methods=["POST"])
@jwt_required()
def api_guardarcuota():
    return _api_guardar_tabla("cuotas")


@app.route("/api_actualizarcuota", methods=["PUT", "POST"])
@app.route("/api_actualizarcuota/<int:registro_id>", methods=["PUT", "POST"])
@jwt_required()
def api_actualizarcuota(registro_id=None):
    return _api_actualizar_tabla("cuotas", registro_id)


@app.route("/api_eliminarcuota", methods=["DELETE", "POST"])
@app.route("/api_eliminarcuota/<int:registro_id>", methods=["DELETE", "POST"])
@jwt_required()
def api_eliminarcuota(registro_id=None):
    return _api_eliminar_tabla("cuotas", registro_id)


@app.route("/api_leercuotaxid", methods=["GET", "POST"])
@app.route("/api_leercuotaxid/<int:registro_id>", methods=["GET", "POST"])
@jwt_required()
def api_leercuotaxid(registro_id=None):
    return _api_leer_tabla_xid("cuotas", registro_id)


@app.route("/api_leercuotas")
@jwt_required()
def api_leercuotas():
    return _api_leer_tabla("cuotas")


# ============================================================
# APIS - MEDIOS_PAGO
# ============================================================

@app.route("/api_guardarmediopago", methods=["POST"])
@jwt_required()
def api_guardarmediopago():
    return _api_guardar_tabla("medios_pago")


@app.route("/api_actualizarmediopago", methods=["PUT", "POST"])
@app.route("/api_actualizarmediopago/<int:registro_id>", methods=["PUT", "POST"])
@jwt_required()
def api_actualizarmediopago(registro_id=None):
    return _api_actualizar_tabla("medios_pago", registro_id)


@app.route("/api_eliminarmediopago", methods=["DELETE", "POST"])
@app.route("/api_eliminarmediopago/<int:registro_id>", methods=["DELETE", "POST"])
@jwt_required()
def api_eliminarmediopago(registro_id=None):
    return _api_eliminar_tabla("medios_pago", registro_id)


@app.route("/api_leermediopagoxid", methods=["GET", "POST"])
@app.route("/api_leermediopagoxid/<int:registro_id>", methods=["GET", "POST"])
@jwt_required()
def api_leermediopagoxid(registro_id=None):
    return _api_leer_tabla_xid("medios_pago", registro_id)


@app.route("/api_leermediospago")
@jwt_required()
def api_leermediospago():
    return _api_leer_tabla("medios_pago")


# ============================================================
# APIS - EVIDENCIAS_PAGO
# ============================================================

@app.route("/api_guardarevidenciapago", methods=["POST"])
@jwt_required()
def api_guardarevidenciapago():
    return _api_guardar_tabla("evidencias_pago")


@app.route("/api_actualizarevidenciapago", methods=["PUT", "POST"])
@app.route("/api_actualizarevidenciapago/<int:registro_id>", methods=["PUT", "POST"])
@jwt_required()
def api_actualizarevidenciapago(registro_id=None):
    return _api_actualizar_tabla("evidencias_pago", registro_id)


@app.route("/api_eliminarevidenciapago", methods=["DELETE", "POST"])
@app.route("/api_eliminarevidenciapago/<int:registro_id>", methods=["DELETE", "POST"])
@jwt_required()
def api_eliminarevidenciapago(registro_id=None):
    return _api_eliminar_tabla("evidencias_pago", registro_id)


@app.route("/api_leerevidenciapagoxid", methods=["GET", "POST"])
@app.route("/api_leerevidenciapagoxid/<int:registro_id>", methods=["GET", "POST"])
@jwt_required()
def api_leerevidenciapagoxid(registro_id=None):
    return _api_leer_tabla_xid("evidencias_pago", registro_id)


@app.route("/api_leerevidenciaspago")
@jwt_required()
def api_leerevidenciaspago():
    return _api_leer_tabla("evidencias_pago")


# ============================================================
# APIS - TRANSACCIONES_PAGO
# ============================================================

@app.route("/api_guardartransaccionpago", methods=["POST"])
@jwt_required()
def api_guardartransaccionpago():
    return _api_guardar_tabla("transacciones_pago")


@app.route("/api_actualizartransaccionpago", methods=["PUT", "POST"])
@app.route("/api_actualizartransaccionpago/<int:registro_id>", methods=["PUT", "POST"])
@jwt_required()
def api_actualizartransaccionpago(registro_id=None):
    return _api_actualizar_tabla("transacciones_pago", registro_id)


@app.route("/api_eliminartransaccionpago", methods=["DELETE", "POST"])
@app.route("/api_eliminartransaccionpago/<int:registro_id>", methods=["DELETE", "POST"])
@jwt_required()
def api_eliminartransaccionpago(registro_id=None):
    return _api_eliminar_tabla("transacciones_pago", registro_id)


@app.route("/api_leertransaccionpagoxid", methods=["GET", "POST"])
@app.route("/api_leertransaccionpagoxid/<int:registro_id>", methods=["GET", "POST"])
@jwt_required()
def api_leertransaccionpagoxid(registro_id=None):
    return _api_leer_tabla_xid("transacciones_pago", registro_id)


@app.route("/api_leertransaccionespago")
@jwt_required()
def api_leertransaccionespago():
    return _api_leer_tabla("transacciones_pago")


# ============================================================
# APIS - COMPROBANTES_PAGO
# ============================================================

@app.route("/api_guardarcomprobantepago", methods=["POST"])
@jwt_required()
def api_guardarcomprobantepago():
    return _api_guardar_tabla("comprobantes_pago")


@app.route("/api_actualizarcomprobantepago", methods=["PUT", "POST"])
@app.route("/api_actualizarcomprobantepago/<int:registro_id>", methods=["PUT", "POST"])
@jwt_required()
def api_actualizarcomprobantepago(registro_id=None):
    return _api_actualizar_tabla("comprobantes_pago", registro_id)


@app.route("/api_eliminarcomprobantepago", methods=["DELETE", "POST"])
@app.route("/api_eliminarcomprobantepago/<int:registro_id>", methods=["DELETE", "POST"])
@jwt_required()
def api_eliminarcomprobantepago(registro_id=None):
    return _api_eliminar_tabla("comprobantes_pago", registro_id)


@app.route("/api_leercomprobantepagoxid", methods=["GET", "POST"])
@app.route("/api_leercomprobantepagoxid/<int:registro_id>", methods=["GET", "POST"])
@jwt_required()
def api_leercomprobantepagoxid(registro_id=None):
    return _api_leer_tabla_xid("comprobantes_pago", registro_id)


@app.route("/api_leercomprobantespago")
@jwt_required()
def api_leercomprobantespago():
    return _api_leer_tabla("comprobantes_pago")


# ============================================================
# APIS - CONFIGURACION_MERCADO_PAGO
# ============================================================

@app.route("/api_guardarconfiguracionmercadopago", methods=["POST"])
@jwt_required()
def api_guardarconfiguracionmercadopago():
    return _api_guardar_tabla("configuracion_mercado_pago")


@app.route("/api_actualizarconfiguracionmercadopago", methods=["PUT", "POST"])
@app.route("/api_actualizarconfiguracionmercadopago/<int:registro_id>", methods=["PUT", "POST"])
@jwt_required()
def api_actualizarconfiguracionmercadopago(registro_id=None):
    return _api_actualizar_tabla("configuracion_mercado_pago", registro_id)


@app.route("/api_eliminarconfiguracionmercadopago", methods=["DELETE", "POST"])
@app.route("/api_eliminarconfiguracionmercadopago/<int:registro_id>", methods=["DELETE", "POST"])
@jwt_required()
def api_eliminarconfiguracionmercadopago(registro_id=None):
    return _api_eliminar_tabla("configuracion_mercado_pago", registro_id)


@app.route("/api_leerconfiguracionmercadopagoxid", methods=["GET", "POST"])
@app.route("/api_leerconfiguracionmercadopagoxid/<int:registro_id>", methods=["GET", "POST"])
@jwt_required()
def api_leerconfiguracionmercadopagoxid(registro_id=None):
    return _api_leer_tabla_xid("configuracion_mercado_pago", registro_id)


@app.route("/api_leerconfiguracionesmercadopago")
@jwt_required()
def api_leerconfiguracionesmercadopago():
    return _api_leer_tabla("configuracion_mercado_pago")


# ============================================================
# APIS - ORDENES_MERCADO_PAGO
# ============================================================

@app.route("/api_guardarordenmercadopago", methods=["POST"])
@jwt_required()
def api_guardarordenmercadopago():
    return _api_guardar_tabla("ordenes_mercado_pago")


@app.route("/api_actualizarordenmercadopago", methods=["PUT", "POST"])
@app.route("/api_actualizarordenmercadopago/<int:registro_id>", methods=["PUT", "POST"])
@jwt_required()
def api_actualizarordenmercadopago(registro_id=None):
    return _api_actualizar_tabla("ordenes_mercado_pago", registro_id)


@app.route("/api_eliminarordenmercadopago", methods=["DELETE", "POST"])
@app.route("/api_eliminarordenmercadopago/<int:registro_id>", methods=["DELETE", "POST"])
@jwt_required()
def api_eliminarordenmercadopago(registro_id=None):
    return _api_eliminar_tabla("ordenes_mercado_pago", registro_id)


@app.route("/api_leerordenmercadopagoxid", methods=["GET", "POST"])
@app.route("/api_leerordenmercadopagoxid/<int:registro_id>", methods=["GET", "POST"])
@jwt_required()
def api_leerordenmercadopagoxid(registro_id=None):
    return _api_leer_tabla_xid("ordenes_mercado_pago", registro_id)


@app.route("/api_leerordenesmercadopago")
@jwt_required()
def api_leerordenesmercadopago():
    return _api_leer_tabla("ordenes_mercado_pago")


# ============================================================
# APIS - CONFIGURACION_FACTURACION
# ============================================================

@app.route("/api_guardarconfiguracionfacturacion", methods=["POST"])
@jwt_required()
def api_guardarconfiguracionfacturacion():
    return _api_guardar_tabla("configuracion_facturacion")


@app.route("/api_actualizarconfiguracionfacturacion", methods=["PUT", "POST"])
@app.route("/api_actualizarconfiguracionfacturacion/<int:registro_id>", methods=["PUT", "POST"])
@jwt_required()
def api_actualizarconfiguracionfacturacion(registro_id=None):
    return _api_actualizar_tabla("configuracion_facturacion", registro_id)


@app.route("/api_eliminarconfiguracionfacturacion", methods=["DELETE", "POST"])
@app.route("/api_eliminarconfiguracionfacturacion/<int:registro_id>", methods=["DELETE", "POST"])
@jwt_required()
def api_eliminarconfiguracionfacturacion(registro_id=None):
    return _api_eliminar_tabla("configuracion_facturacion", registro_id)


@app.route("/api_leerconfiguracionfacturacionxid", methods=["GET", "POST"])
@app.route("/api_leerconfiguracionfacturacionxid/<int:registro_id>", methods=["GET", "POST"])
@jwt_required()
def api_leerconfiguracionfacturacionxid(registro_id=None):
    return _api_leer_tabla_xid("configuracion_facturacion", registro_id)


@app.route("/api_leerconfiguracionesfacturacion")
@jwt_required()
def api_leerconfiguracionesfacturacion():
    return _api_leer_tabla("configuracion_facturacion")


# ============================================================
# APIS - COMPROBANTES_FISCALES
# ============================================================

@app.route("/api_guardarcomprobantefiscal", methods=["POST"])
@jwt_required()
def api_guardarcomprobantefiscal():
    return _api_guardar_tabla("comprobantes_fiscales")


@app.route("/api_actualizarcomprobantefiscal", methods=["PUT", "POST"])
@app.route("/api_actualizarcomprobantefiscal/<int:registro_id>", methods=["PUT", "POST"])
@jwt_required()
def api_actualizarcomprobantefiscal(registro_id=None):
    return _api_actualizar_tabla("comprobantes_fiscales", registro_id)


@app.route("/api_eliminarcomprobantefiscal", methods=["DELETE", "POST"])
@app.route("/api_eliminarcomprobantefiscal/<int:registro_id>", methods=["DELETE", "POST"])
@jwt_required()
def api_eliminarcomprobantefiscal(registro_id=None):
    return _api_eliminar_tabla("comprobantes_fiscales", registro_id)


@app.route("/api_leercomprobantefiscalxid", methods=["GET", "POST"])
@app.route("/api_leercomprobantefiscalxid/<int:registro_id>", methods=["GET", "POST"])
@jwt_required()
def api_leercomprobantefiscalxid(registro_id=None):
    return _api_leer_tabla_xid("comprobantes_fiscales", registro_id)


@app.route("/api_leercomprobantesfiscales")
@jwt_required()
def api_leercomprobantesfiscales():
    return _api_leer_tabla("comprobantes_fiscales")


# ============================================================
# APIS - COMPROBANTE_FISCAL_DETALLE
# ============================================================

@app.route("/api_guardarcomprobantefiscaldetalle", methods=["POST"])
@jwt_required()
def api_guardarcomprobantefiscaldetalle():
    return _api_guardar_tabla("comprobante_fiscal_detalle")


@app.route("/api_actualizarcomprobantefiscaldetalle", methods=["PUT", "POST"])
@app.route("/api_actualizarcomprobantefiscaldetalle/<int:registro_id>", methods=["PUT", "POST"])
@jwt_required()
def api_actualizarcomprobantefiscaldetalle(registro_id=None):
    return _api_actualizar_tabla("comprobante_fiscal_detalle", registro_id)


@app.route("/api_eliminarcomprobantefiscaldetalle", methods=["DELETE", "POST"])
@app.route("/api_eliminarcomprobantefiscaldetalle/<int:registro_id>", methods=["DELETE", "POST"])
@jwt_required()
def api_eliminarcomprobantefiscaldetalle(registro_id=None):
    return _api_eliminar_tabla("comprobante_fiscal_detalle", registro_id)


@app.route("/api_leercomprobantefiscaldetallexid", methods=["GET", "POST"])
@app.route("/api_leercomprobantefiscaldetallexid/<int:registro_id>", methods=["GET", "POST"])
@jwt_required()
def api_leercomprobantefiscaldetallexid(registro_id=None):
    return _api_leer_tabla_xid("comprobante_fiscal_detalle", registro_id)


@app.route("/api_leercomprobantesfiscalesdetalle")
@jwt_required()
def api_leercomprobantesfiscalesdetalle():
    return _api_leer_tabla("comprobante_fiscal_detalle")


# ============================================================
# APIS - FACTURACION_SUNAT_LOGS
# ============================================================

@app.route("/api_guardarfacturacionsunatlog", methods=["POST"])
@jwt_required()
def api_guardarfacturacionsunatlog():
    return _api_guardar_tabla("facturacion_sunat_logs")


@app.route("/api_actualizarfacturacionsunatlog", methods=["PUT", "POST"])
@app.route("/api_actualizarfacturacionsunatlog/<int:registro_id>", methods=["PUT", "POST"])
@jwt_required()
def api_actualizarfacturacionsunatlog(registro_id=None):
    return _api_actualizar_tabla("facturacion_sunat_logs", registro_id)


@app.route("/api_eliminarfacturacionsunatlog", methods=["DELETE", "POST"])
@app.route("/api_eliminarfacturacionsunatlog/<int:registro_id>", methods=["DELETE", "POST"])
@jwt_required()
def api_eliminarfacturacionsunatlog(registro_id=None):
    return _api_eliminar_tabla("facturacion_sunat_logs", registro_id)


@app.route("/api_leerfacturacionsunatlogxid", methods=["GET", "POST"])
@app.route("/api_leerfacturacionsunatlogxid/<int:registro_id>", methods=["GET", "POST"])
@jwt_required()
def api_leerfacturacionsunatlogxid(registro_id=None):
    return _api_leer_tabla_xid("facturacion_sunat_logs", registro_id)


@app.route("/api_leerfacturacionsunatlogs")
@jwt_required()
def api_leerfacturacionsunatlogs():
    return _api_leer_tabla("facturacion_sunat_logs")


# ============================================================
# APIS - CURSOS
# ============================================================

@app.route("/api_guardarcurso", methods=["POST"])
@jwt_required()
def api_guardarcurso():
    return _api_guardar_tabla("cursos")


@app.route("/api_actualizarcurso", methods=["PUT", "POST"])
@app.route("/api_actualizarcurso/<int:registro_id>", methods=["PUT", "POST"])
@jwt_required()
def api_actualizarcurso(registro_id=None):
    return _api_actualizar_tabla("cursos", registro_id)


@app.route("/api_eliminarcurso", methods=["DELETE", "POST"])
@app.route("/api_eliminarcurso/<int:registro_id>", methods=["DELETE", "POST"])
@jwt_required()
def api_eliminarcurso(registro_id=None):
    return _api_eliminar_tabla("cursos", registro_id)


@app.route("/api_leercursoxid", methods=["GET", "POST"])
@app.route("/api_leercursoxid/<int:registro_id>", methods=["GET", "POST"])
@jwt_required()
def api_leercursoxid(registro_id=None):
    return _api_leer_tabla_xid("cursos", registro_id)


@app.route("/api_leercursos")
@jwt_required()
def api_leercursos():
    return _api_leer_tabla("cursos")


# ============================================================
# APIS - CONTENIDO_CURSO
# ============================================================

@app.route("/api_guardarcontenidocurso", methods=["POST"])
@jwt_required()
def api_guardarcontenidocurso():
    return _api_guardar_tabla("contenido_curso")


@app.route("/api_actualizarcontenidocurso", methods=["PUT", "POST"])
@app.route("/api_actualizarcontenidocurso/<int:registro_id>", methods=["PUT", "POST"])
@jwt_required()
def api_actualizarcontenidocurso(registro_id=None):
    return _api_actualizar_tabla("contenido_curso", registro_id)


@app.route("/api_eliminarcontenidocurso", methods=["DELETE", "POST"])
@app.route("/api_eliminarcontenidocurso/<int:registro_id>", methods=["DELETE", "POST"])
@jwt_required()
def api_eliminarcontenidocurso(registro_id=None):
    return _api_eliminar_tabla("contenido_curso", registro_id)


@app.route("/api_leercontenidocursoxid", methods=["GET", "POST"])
@app.route("/api_leercontenidocursoxid/<int:registro_id>", methods=["GET", "POST"])
@jwt_required()
def api_leercontenidocursoxid(registro_id=None):
    return _api_leer_tabla_xid("contenido_curso", registro_id)


@app.route("/api_leercontenidoscurso")
@jwt_required()
def api_leercontenidoscurso():
    return _api_leer_tabla("contenido_curso")


# ============================================================
# APIS - INSCRIPCIONES_CURSO
# ============================================================

@app.route("/api_guardarinscripcioncurso", methods=["POST"])
@jwt_required()
def api_guardarinscripcioncurso():
    return _api_guardar_tabla("inscripciones_curso")


@app.route("/api_actualizarinscripcioncurso", methods=["PUT", "POST"])
@app.route("/api_actualizarinscripcioncurso/<int:registro_id>", methods=["PUT", "POST"])
@jwt_required()
def api_actualizarinscripcioncurso(registro_id=None):
    return _api_actualizar_tabla("inscripciones_curso", registro_id)


@app.route("/api_eliminarinscripcioncurso", methods=["DELETE", "POST"])
@app.route("/api_eliminarinscripcioncurso/<int:registro_id>", methods=["DELETE", "POST"])
@jwt_required()
def api_eliminarinscripcioncurso(registro_id=None):
    return _api_eliminar_tabla("inscripciones_curso", registro_id)


@app.route("/api_leerinscripcioncursoxid", methods=["GET", "POST"])
@app.route("/api_leerinscripcioncursoxid/<int:registro_id>", methods=["GET", "POST"])
@jwt_required()
def api_leerinscripcioncursoxid(registro_id=None):
    return _api_leer_tabla_xid("inscripciones_curso", registro_id)


@app.route("/api_leerinscripcionescurso")
@jwt_required()
def api_leerinscripcionescurso():
    return _api_leer_tabla("inscripciones_curso")


# ============================================================
# APIS - TRAMITES
# ============================================================

@app.route("/api_guardartramite", methods=["POST"])
@jwt_required()
def api_guardartramite():
    return _api_guardar_tabla("tramites")


@app.route("/api_actualizartramite", methods=["PUT", "POST"])
@app.route("/api_actualizartramite/<int:registro_id>", methods=["PUT", "POST"])
@jwt_required()
def api_actualizartramite(registro_id=None):
    return _api_actualizar_tabla("tramites", registro_id)


@app.route("/api_eliminartramite", methods=["DELETE", "POST"])
@app.route("/api_eliminartramite/<int:registro_id>", methods=["DELETE", "POST"])
@jwt_required()
def api_eliminartramite(registro_id=None):
    return _api_eliminar_tabla("tramites", registro_id)


@app.route("/api_leertramitexid", methods=["GET", "POST"])
@app.route("/api_leertramitexid/<int:registro_id>", methods=["GET", "POST"])
@jwt_required()
def api_leertramitexid(registro_id=None):
    return _api_leer_tabla_xid("tramites", registro_id)


@app.route("/api_leertramites")
@jwt_required()
def api_leertramites():
    return _api_leer_tabla("tramites")


# ============================================================
# APIS - TICKETS
# ============================================================

@app.route("/api_guardarticket", methods=["POST"])
@jwt_required()
def api_guardarticket():
    return _api_guardar_tabla("tickets")


@app.route("/api_actualizarticket", methods=["PUT", "POST"])
@app.route("/api_actualizarticket/<int:registro_id>", methods=["PUT", "POST"])
@jwt_required()
def api_actualizarticket(registro_id=None):
    return _api_actualizar_tabla("tickets", registro_id)


@app.route("/api_eliminarticket", methods=["DELETE", "POST"])
@app.route("/api_eliminarticket/<int:registro_id>", methods=["DELETE", "POST"])
@jwt_required()
def api_eliminarticket(registro_id=None):
    return _api_eliminar_tabla("tickets", registro_id)


@app.route("/api_leerticketxid", methods=["GET", "POST"])
@app.route("/api_leerticketxid/<int:registro_id>", methods=["GET", "POST"])
@jwt_required()
def api_leerticketxid(registro_id=None):
    return _api_leer_tabla_xid("tickets", registro_id)


@app.route("/api_leertickets")
@jwt_required()
def api_leertickets():
    return _api_leer_tabla("tickets")


# ============================================================
# APIS - NOTIFICACIONES
# ============================================================

@app.route("/api_guardarnotificacion", methods=["POST"])
@jwt_required()
def api_guardarnotificacion():
    return _api_guardar_tabla("notificaciones")


@app.route("/api_actualizarnotificacion", methods=["PUT", "POST"])
@app.route("/api_actualizarnotificacion/<int:registro_id>", methods=["PUT", "POST"])
@jwt_required()
def api_actualizarnotificacion(registro_id=None):
    return _api_actualizar_tabla("notificaciones", registro_id)


@app.route("/api_eliminarnotificacion", methods=["DELETE", "POST"])
@app.route("/api_eliminarnotificacion/<int:registro_id>", methods=["DELETE", "POST"])
@jwt_required()
def api_eliminarnotificacion(registro_id=None):
    return _api_eliminar_tabla("notificaciones", registro_id)


@app.route("/api_leernotificacionxid", methods=["GET", "POST"])
@app.route("/api_leernotificacionxid/<int:registro_id>", methods=["GET", "POST"])
@jwt_required()
def api_leernotificacionxid(registro_id=None):
    return _api_leer_tabla_xid("notificaciones", registro_id)


@app.route("/api_leernotificaciones")
@jwt_required()
def api_leernotificaciones():
    return _api_leer_tabla("notificaciones")


@app.route("/api/postman-collection", endpoint="api_postman_collection")
def api_postman_collection():
    base_url = request.url_root.rstrip("/")
    items = [
        {
            "name": "01 - Generar token JWT",
            "request": {
                "method": "POST",
                "header": [{"key": "Content-Type", "value": "application/json"}],
                "body": {
                    "mode": "raw",
                    "raw": json.dumps({
                        "username": "admin",
                        "password": "admin2024"
                    }, indent=2)
                },
                "url": "{{base_url}}/auth"
            }
        }
    ]

    carpetas = {}
    for modulo, tabla, singular, plural in API_COLECCION_TABLAS:
        carpetas.setdefault(modulo, {"name": modulo, "item": []})
        carpetas[modulo]["item"].extend([
            {
                "name": f"api_leer{plural}",
                "request": {
                    "method": "GET",
                    "header": [{"key": "Authorization", "value": "JWT {{token}}"}],
                    "url": f"{{{{base_url}}}}/api_leer{plural}"
                }
            },
            {
                "name": f"api_leer{singular}xid",
                "request": {
                    "method": "GET",
                    "header": [{"key": "Authorization", "value": "JWT {{token}}"}],
                    "url": f"{{{{base_url}}}}/api_leer{singular}xid/1"
                }
            },
            {
                "name": f"api_guardar{singular}",
                "request": {
                    "method": "POST",
                    "header": [
                        {"key": "Authorization", "value": "JWT {{token}}"},
                        {"key": "Content-Type", "value": "application/json"}
                    ],
                    "body": {"mode": "raw", "raw": "{}"},
                    "url": f"{{{{base_url}}}}/api_guardar{singular}"
                }
            },
            {
                "name": f"api_actualizar{singular}",
                "request": {
                    "method": "PUT",
                    "header": [
                        {"key": "Authorization", "value": "JWT {{token}}"},
                        {"key": "Content-Type", "value": "application/json"}
                    ],
                    "body": {"mode": "raw", "raw": "{\n  \"id\": 1\n}"},
                    "url": f"{{{{base_url}}}}/api_actualizar{singular}/1"
                }
            },
            {
                "name": f"api_eliminar{singular}",
                "request": {
                    "method": "DELETE",
                    "header": [{"key": "Authorization", "value": "JWT {{token}}"}],
                    "url": f"{{{{base_url}}}}/api_eliminar{singular}/1"
                }
            },
        ])

    items.extend(carpetas.values())
    return jsonify({
        "info": {
            "name": "CCPL Intranet - APIs JWT",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
        },
        "variable": [
            {"key": "base_url", "value": base_url},
            {"key": "token", "value": ""}
        ],
        "item": items
    })


# ============================================================
# EJECUCION LOCAL
# ============================================================

if __name__ == "__main__":
    app.run(debug=True)
