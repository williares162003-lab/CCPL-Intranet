import base64
import os
import re
import subprocess
import sys
import traceback
from io import BytesIO
from pathlib import Path

from flask import Flask, jsonify, request


app = Flask(__name__)


BASE_DIR = Path(__file__).resolve().parent
FIRMADOR_HOST = os.environ.get("EDNI_FIRMADOR_HOST", "127.0.0.1")
FIRMADOR_PORT = int(os.environ.get("EDNI_FIRMADOR_PORT", "8765"))
ORIGENES_PERMITIDOS = [
    origen.strip()
    for origen in os.environ.get(
        "EDNI_CORS_ORIGINS",
        "http://127.0.0.1:5000,http://localhost:5000,https://trabajodaweb.pythonanywhere.com"
    ).split(",")
    if origen.strip()
]
OPENSC_CONF_LOCAL = BASE_DIR / "opensc-dnie-peru.conf"
if OPENSC_CONF_LOCAL.exists() and not os.environ.get("OPENSC_CONF"):
    os.environ["OPENSC_CONF"] = str(OPENSC_CONF_LOCAL)

PKCS11_CANDIDATOS = [
    os.environ.get("EDNI_PKCS11_DLL", ""),
    r"C:\Program Files\IDEMIA\IDPlugClassic\DLLs\idplug-pkcs11.dll",
    r"C:\Program Files (x86)\IDEMIA\IDPlugClassic\DLLs\idplug-pkcs11.dll",
    r"C:\Program Files\OpenSC Project\OpenSC\pkcs11\onepin-opensc-pkcs11.dll",
    r"C:\Program Files\OpenSC Project\OpenSC\pkcs11\opensc-pkcs11.dll",
    r"C:\Program Files (x86)\OpenSC Project\OpenSC\pkcs11\opensc-pkcs11.dll",
    r"C:\Windows\System32\opensc-pkcs11.dll",
]
TOKEN_LABEL_FIRMA = os.environ.get("EDNI_TOKEN_LABEL", "PKI Application (Signature PIN)")


def _origen_permitido(origen):
    if not origen:
        return False
    if origen in ORIGENES_PERMITIDOS:
        return True
    return origen.startswith("http://127.0.0.1:") or origen.startswith("http://localhost:")


@app.after_request
def agregar_cors_local(response):
    origen = request.headers.get("Origin", "")
    if _origen_permitido(origen):
        response.headers["Access-Control-Allow-Origin"] = origen
        response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


def buscar_pkcs11():
    for ruta in PKCS11_CANDIDATOS:
        if ruta and Path(ruta).exists():
            return ruta
    return ""


def preparar_dependencias_pkcs11(ruta_pkcs11):
    carpeta_dll = Path(ruta_pkcs11).parent
    if hasattr(os, "add_dll_directory") and carpeta_dll.exists():
        os.add_dll_directory(str(carpeta_dll))


def agregar_site_packages_python_actual():
    version = f"Python{sys.version_info.major}{sys.version_info.minor}"
    candidatos = [
        Path(sys.prefix) / "Lib" / "site-packages",
        Path(sys.base_prefix) / "Lib" / "site-packages",
        Path.home() / "AppData" / "Local" / "Programs" / "Python" / version / "Lib" / "site-packages",
    ]
    for ruta in candidatos:
        texto = str(ruta)
        if ruta.exists() and texto not in sys.path:
            sys.path.append(texto)


def importar_pkcs11():
    agregar_site_packages_python_actual()
    import pkcs11
    return pkcs11


def texto_pkcs11(valor):
    if valor is None:
        return ""
    if isinstance(valor, bytes):
        for encoding in ("utf-8", "latin-1"):
            try:
                return valor.decode(encoding, errors="ignore").strip()
            except Exception:
                continue
        return valor.hex()
    return str(valor).strip()


def bytes_pkcs11(valor):
    if valor is None:
        return None
    if isinstance(valor, bytes):
        return valor
    try:
        return bytes(valor)
    except Exception:
        return None


def es_token_firma(token):
    label = texto_pkcs11(getattr(token, "label", ""))
    return "signature" in label.lower() or "firma" in label.lower()


def elegir_token_firma(slots_con_token):
    tokens = []
    for slot in slots_con_token:
        token = slot.get_token()
        tokens.append(token)
        if es_token_firma(token):
            return token
    return tokens[0] if tokens else None


def es_certificado_firma(certificado):
    texto = " ".join([
        certificado.get("label", ""),
        certificado.get("titular", ""),
        certificado.get("documento", ""),
    ]).upper()
    return " FIR " in f" {texto} " or "SIGNATURE" in texto or "FIRMA" in texto


def buscar_certificado_firma(session):
    agregar_site_packages_python_actual()
    from pkcs11 import Attribute, ObjectClass

    certificados = []
    for objeto in session.get_objects({Attribute.CLASS: ObjectClass.CERTIFICATE}):
        try:
            label = texto_pkcs11(objeto[Attribute.LABEL])
            cert_id = bytes_pkcs11(objeto[Attribute.ID])
            certificados.append({"label": label, "id": cert_id})
        except Exception:
            continue

    for certificado in certificados:
        label = certificado["label"]
        if " FIR " in f" {label.upper()} " or "SIGNATURE" in label.upper():
            return certificado
    for certificado in certificados:
        texto = certificado["label"].upper()
        if " AUT " not in f" {texto} " and "CA " not in texto and "ROOT" not in texto:
            return certificado
    return certificados[0] if certificados else {}


def respuesta(code, message, **extra):
    data = {"code": code, "message": message}
    data.update(extra)
    return jsonify(data)


def preparar_salida_oculta():
    if sys.stdout is None or getattr(sys.stdout, "closed", False):
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None or getattr(sys.stderr, "closed", False):
        sys.stderr = open(os.devnull, "w")


def estado_opensc_herramienta():
    herramienta = Path(r"C:\Program Files\OpenSC Project\OpenSC\tools\opensc-tool.exe")
    if not herramienta.exists():
        return {}

    try:
        env = os.environ.copy()
        if OPENSC_CONF_LOCAL.exists():
            env.setdefault("OPENSC_CONF", str(OPENSC_CONF_LOCAL))
        proceso = subprocess.run(
            [str(herramienta), "-l", "-v"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
            env=env,
        )
    except Exception:
        return {}

    salida = (proceso.stdout or "") + "\n" + (proceso.stderr or "")
    lineas = [linea.strip() for linea in salida.splitlines() if linea.strip()]
    lectores = 0
    dni_insertado = False
    tarjeta_responde = None
    lector_nombre = ""
    atr = ""
    driver_detectado = ""

    for linea in lineas:
        if re.match(r"^\d+\s+", linea):
            lectores += 1
            partes = linea.split()
            dni_insertado = len(partes) > 1 and partes[1].lower() == "yes"
            lector_nombre = " ".join(partes[3:]) if len(partes) > 3 else lector_nombre
        if re.match(r"^[0-9a-f]{2}:", linea.lower()):
            partes = linea.split()
            atr = partes[0]
            driver_detectado = " ".join(partes[1:]) if len(partes) > 1 else ""
        if "unresponsive card" in linea.lower():
            tarjeta_responde = False

    if lectores == 0:
        return {}

    if dni_insertado and tarjeta_responde is False:
        return {
            "code": 0,
            "message": "Lector conectado. El DNIe esta insertado, pero no responde.",
            "lectores": lectores,
            "dni_insertado": True,
            "tarjeta_responde": False,
            "lector_nombre": lector_nombre,
            "atr": atr,
            "driver_detectado": driver_detectado,
        }
    if dni_insertado:
        return {
            "code": 0,
            "message": "DNIe detectado. Falta un middleware compatible para exponer el certificado al firmador.",
            "lectores": lectores,
            "dni_insertado": True,
            "tarjeta_responde": True,
            "lector_nombre": lector_nombre,
            "atr": atr,
            "driver_detectado": driver_detectado,
            "requiere_middleware": True,
        }
    return {
        "code": 0,
        "message": "Lector conectado. Inserte el DNIe para continuar.",
        "lectores": lectores,
        "dni_insertado": False,
        "tarjeta_responde": None,
        "lector_nombre": lector_nombre,
        "atr": atr,
        "driver_detectado": driver_detectado,
    }


def _texto_atributo(certificado, oid):
    valores = certificado.subject.get_attributes_for_oid(oid)
    return valores[0].value if valores else ""


def _fecha_certificado(valor):
    return valor.strftime("%Y-%m-%d") if valor else ""


def _dni_desde_texto(*valores):
    for valor in valores:
        coincidencia = re.search(r"\b\d{8}\b", valor or "")
        if coincidencia:
            return coincidencia.group(0)
    return ""


def leer_certificados_token(token):
    agregar_site_packages_python_actual()
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from pkcs11 import Attribute, ObjectClass

    certificados = []
    session = token.open()
    try:
        objetos = session.get_objects({Attribute.CLASS: ObjectClass.CERTIFICATE})
        for objeto in objetos:
            try:
                try:
                    label = texto_pkcs11(objeto[Attribute.LABEL])
                except Exception:
                    label = ""
                valor = objeto[Attribute.VALUE]
                cert = x509.load_der_x509_certificate(bytes(valor))
                nombre = _texto_atributo(cert, NameOID.COMMON_NAME)
                documento = _texto_atributo(cert, NameOID.SERIAL_NUMBER)
                dni = _dni_desde_texto(documento, nombre, cert.subject.rfc4514_string())
                no_antes = cert.not_valid_before_utc if hasattr(cert, "not_valid_before_utc") else cert.not_valid_before
                no_despues = cert.not_valid_after_utc if hasattr(cert, "not_valid_after_utc") else cert.not_valid_after
                certificados.append({
                    "label": label,
                    "titular": nombre,
                    "documento": documento,
                    "dni": dni,
                    "serie": format(cert.serial_number, "X"),
                    "vigente_desde": _fecha_certificado(no_antes),
                    "vigente_hasta": _fecha_certificado(no_despues),
                    "emisor": cert.issuer.rfc4514_string(),
                })
            except Exception as exc:
                certificados.append({
                    "label": "Certificado no legible",
                    "error": str(exc),
                })
    finally:
        session.close()
    return certificados


@app.get("/estado")
def estado():
    ruta_pkcs11 = buscar_pkcs11()
    if not ruta_pkcs11:
        return respuesta(
            0,
            "No se encontro la libreria PKCS#11 del DNIe. Instale el driver RENIEC o configure EDNI_PKCS11_DLL."
        )

    try:
        pkcs11 = importar_pkcs11()
        preparar_dependencias_pkcs11(ruta_pkcs11)
        lib = pkcs11.lib(ruta_pkcs11)
        slots = list(lib.get_slots())
        slots_con_token = list(lib.get_slots(token_present=True))
        if not slots:
            return respuesta(
                0,
                "No se detecto lector de tarjetas inteligentes.",
                pkcs11=ruta_pkcs11,
                lectores=0,
                dni_insertado=False
            )
        if not slots_con_token:
            return respuesta(
                0,
                "Lector detectado. Inserte el DNIe para continuar.",
                pkcs11=ruta_pkcs11,
                lectores=len(slots),
                dni_insertado=False
            )

        token = elegir_token_firma(slots_con_token)
        if token is None:
            return respuesta(
                0,
                "Lector detectado. Inserte el DNIe para continuar.",
                pkcs11=ruta_pkcs11,
                lectores=len(slots),
                dni_insertado=False
            )

        certificados = []
        try:
            certificados = leer_certificados_token(token)
        except Exception as exc:
            return respuesta(
                0,
                "DNIe detectado. Falta un middleware compatible para leer el certificado digital.",
                detalle=str(exc),
                pkcs11=ruta_pkcs11,
                lectores=len(slots),
                dni_insertado=True,
                requiere_middleware=True,
                token={
                    "label": texto_pkcs11(token.label),
                    "serie": texto_pkcs11(token.serial),
                    "fabricante": texto_pkcs11(token.manufacturer_id),
                },
                certificados=[]
            )

        if not certificados:
            return respuesta(
                0,
                "DNIe detectado, pero el certificado no esta disponible para firma.",
                pkcs11=ruta_pkcs11,
                lectores=len(slots),
                dni_insertado=True,
                requiere_middleware=True,
                token={
                    "label": texto_pkcs11(token.label),
                    "serie": texto_pkcs11(token.serial),
                    "fabricante": texto_pkcs11(token.manufacturer_id),
                },
                certificados=[]
            )

        return respuesta(
            1,
            "DNIe y certificado digital detectados.",
            pkcs11=ruta_pkcs11,
            lectores=len(slots),
            dni_insertado=True,
            token_firma=es_token_firma(token),
            certificado_firma_detectado=any(es_certificado_firma(cert) for cert in certificados),
            token={
                "label": texto_pkcs11(token.label),
                "serie": texto_pkcs11(token.serial),
                "fabricante": texto_pkcs11(token.manufacturer_id),
            },
            certificados=certificados
        )
    except Exception as exc:
        estado_fisico = estado_opensc_herramienta()
        if estado_fisico:
            estado_fisico["detalle"] = str(exc)
            estado_fisico["pkcs11"] = ruta_pkcs11
            return respuesta(**estado_fisico)
        return respuesta(
            0,
            "No se detecto lector de tarjetas inteligentes.",
            detalle=str(exc),
            pkcs11=ruta_pkcs11,
            lectores=0,
            dni_insertado=False
        )


@app.post("/firmar")
def firmar():
    data = request.get_json(silent=True) or {}
    pin = (data.get("pin") or "").strip()
    pdf_base64 = data.get("archivo_pdf_base64") or ""
    nombre_archivo = data.get("nombre_archivo") or "certificado_firmado.pdf"

    if not pin:
        return respuesta(0, "Ingrese el PIN del DNIe para firmar."), 400
    if not pdf_base64:
        return respuesta(0, "No se recibio el PDF base para firmar."), 400

    ruta_pkcs11 = buscar_pkcs11()
    if not ruta_pkcs11:
        return respuesta(0, "No se encontro la libreria PKCS#11 del DNIe."), 400

    try:
        agregar_site_packages_python_actual()
        from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
        from pyhanko.sign import fields, signers
        from pyhanko.sign.pkcs11 import PKCS11Signer, open_pkcs11_session
        from pyhanko.stamp import TextStampStyle

        preparar_dependencias_pkcs11(ruta_pkcs11)
        pdf_bytes = base64.b64decode(pdf_base64)
        writer = IncrementalPdfFileWriter(BytesIO(pdf_bytes))
        salida = BytesIO()

        session = open_pkcs11_session(ruta_pkcs11, token_label=TOKEN_LABEL_FIRMA, user_pin=pin)
        try:
            certificado_firma = buscar_certificado_firma(session)
            cert_label_env = os.environ.get("EDNI_CERT_LABEL") or None
            cert_id = certificado_firma.get("id")
            signer = PKCS11Signer(
                pkcs11_session=session,
                cert_label=cert_label_env,
                key_label=os.environ.get("EDNI_KEY_LABEL") or None,
                cert_id=cert_id,
                key_id=cert_id,
            )
            meta = signers.PdfSignatureMetadata(
                field_name="FirmaDecanaCCPL",
                reason="Certificado de habilidad CCPL",
                location="Chiclayo, Peru",
            )
            estilo_firma = TextStampStyle(
                stamp_text=(
                    "FIRMA DIGITAL eDNI\n"
                    "Firmado por: %(firmante)s\n"
                    "Fecha: %(ts)s"
                ),
                timestamp_format="%d/%m/%Y %H:%M:%S",
                border_width=1,
            )
            campo_visible = fields.SigFieldSpec(
                sig_field_name="FirmaDecanaCCPL",
                on_page=0,
                box=(135, 150, 460, 222),
            )
            pdf_signer = signers.PdfSigner(
                meta,
                signer=signer,
                stamp_style=estilo_firma,
                new_field_spec=campo_visible,
            )
            pdf_signer.sign_pdf(
                writer,
                output=salida,
                appearance_text_params={
                    "firmante": certificado_firma.get("label") or "Certificado RENIEC",
                },
            )
        finally:
            session.close()

        pdf_firmado = base64.b64encode(salida.getvalue()).decode("ascii")
        nombre_firmado = nombre_archivo.replace(".pdf", "_firmado.pdf")
        return respuesta(
            1,
            "PDF firmado correctamente.",
            nombre_archivo=nombre_firmado,
            archivo_pdf_base64=pdf_firmado
        )
    except Exception as exc:
        detalle = str(exc) or repr(exc) or type(exc).__name__
        return respuesta(
            0,
            "No se pudo firmar. Verifique DNIe insertado, certificado activo y PIN correcto.",
            detalle=detalle,
            tipo_error=type(exc).__name__
        ), 500


if __name__ == "__main__":
    preparar_salida_oculta()
    try:
        app.run(host=FIRMADOR_HOST, port=FIRMADOR_PORT, debug=False)
    except Exception:
        (BASE_DIR / "firmador_edni_error.log").write_text(
            traceback.format_exc(),
            encoding="utf-8"
        )
        raise
