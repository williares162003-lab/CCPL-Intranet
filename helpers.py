import re
from datetime import date


def _validar_dni_peru(dni: str) -> bool:
    return bool(re.fullmatch(r"\d{8}", (dni or "").strip()))


def _validar_nombre_peru(nombre: str) -> bool:
    patron = r"[A-Za-z\u00e1\u00e9\u00ed\u00f3\u00fa\u00c1\u00c9\u00cd\u00d3\u00da\u00fc\u00dc\u00f1\u00d1\s\.\-]{3,100}"
    return bool(re.fullmatch(patron, (nombre or "").strip()))


def _validar_telefono_peru(tel: str) -> bool:
    if not (tel or "").strip():
        return True
    return bool(re.fullmatch(r"9\d{8}", tel.strip()))


def _validar_correo(correo: str) -> bool:
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", (correo or "").strip()))


def _correo_oculto(correo):
    correo = (correo or "").strip()
    if "@" not in correo:
        return ""
    usuario, dominio = correo.split("@", 1)
    visible = usuario[:2] if len(usuario) > 2 else usuario[:1]
    return visible + "***@" + dominio


def _leer_fecha_iso(valor: str):
    try:
        return date.fromisoformat((valor or "").strip())
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
