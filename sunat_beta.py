import base64
import io
import json
import re
import zipfile
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from xml.etree import ElementTree as ET


SUNAT_BETA_ENDPOINT = "https://e-beta.sunat.gob.pe/ol-ti-itcpfegem-beta/billService"

NS = {
    "": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
}

SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
SUNAT_NS = "http://service.sunat.gob.pe"

for prefix, uri in NS.items():
    ET.register_namespace(prefix, uri)


class SunatBetaError(Exception):
    pass


def _q(prefix, tag):
    return "{" + NS[prefix] + "}" + tag


def _money(value):
    numero = Decimal(str(value or "0")).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )
    return format(numero, ".2f")


def _decimal(value):
    return Decimal(str(value or "0")).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


def _tributo_igv(igv):
    if _decimal(igv) > Decimal("0.00"):
        return {
            "categoria": "S",
            "porcentaje": "18.00",
            "afectacion": "10",
            "tributo_id": "1000",
            "tributo_nombre": "IGV",
            "tributo_tipo": "VAT",
        }
    return {
        "categoria": "O",
        "porcentaje": "0.00",
        "afectacion": "30",
        "tributo_id": "9998",
        "tributo_nombre": "INA",
        "tributo_tipo": "FRE",
    }


def _text(parent, prefix, tag, value, attrs=None):
    child = ET.SubElement(parent, _q(prefix, tag), attrs or {})
    child.text = str(value or "")
    return child


def _tipo_comprobante_codigo(tipo):
    tipo = (tipo or "").strip().lower()
    if tipo == "factura":
        return "01"
    return "03"


def _tipo_documento_codigo(tipo_documento, numero):
    tipo = (tipo_documento or "").upper()
    numero = str(numero or "").strip()
    if tipo == "RUC" or (numero.isdigit() and len(numero) == 11):
        return "6"
    if tipo == "DNI" or (numero.isdigit() and len(numero) == 8):
        return "1"
    return "0"


def _numero_comprobante(fila):
    return str(fila.get("serie") or "") + "-" + str(fila.get("numero") or 0).zfill(8)


def _nombre_archivo_base(config, comprobante):
    ruc = re.sub(r"\D", "", str(config.get("ruc") or ""))
    tipo = _tipo_comprobante_codigo(comprobante.get("tipo_comprobante"))
    return ruc + "-" + tipo + "-" + _numero_comprobante(comprobante)


def _validar_config_beta(config):
    ruc = re.sub(r"\D", "", str(config.get("ruc") or ""))
    if len(ruc) != 11 or ruc == "00000000000":
        raise SunatBetaError("Configure el RUC real del emisor para SUNAT beta.")
    if not (config.get("usuario_sol") or "").strip():
        raise SunatBetaError("Configure el usuario SOL secundario.")
    if not (config.get("clave_sol") or "").strip():
        raise SunatBetaError("Configure la clave SOL del usuario secundario.")
    certificado = Path(str(config.get("certificado_ruta") or "").strip())
    if not certificado.exists():
        raise SunatBetaError("Configure la ruta del certificado digital .pfx/.p12.")
    if not (config.get("certificado_clave") or "").strip():
        raise SunatBetaError("Configure la clave del certificado digital.")


def generar_xml_ubl(config, comprobante, detalle):
    root = ET.Element(_q("", "Invoice"))

    extensions = ET.SubElement(root, _q("ext", "UBLExtensions"))
    extension = ET.SubElement(extensions, _q("ext", "UBLExtension"))
    ET.SubElement(extension, _q("ext", "ExtensionContent"))

    _text(root, "cbc", "UBLVersionID", "2.1")
    _text(root, "cbc", "CustomizationID", "2.0")
    _text(root, "cbc", "ID", _numero_comprobante(comprobante))
    _text(root, "cbc", "IssueDate", comprobante.get("fecha_emision") or date.today().isoformat())
    _text(root, "cbc", "InvoiceTypeCode", _tipo_comprobante_codigo(comprobante.get("tipo_comprobante")), {
        "listID": "0101",
        "listAgencyName": "PE:SUNAT",
        "listName": "Tipo de Documento",
        "listURI": "urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo01",
    })
    _text(root, "cbc", "DocumentCurrencyCode", comprobante.get("moneda") or "PEN")

    _agregar_emisor(root, config)
    _agregar_cliente(root, comprobante)
    _agregar_impuestos(root, comprobante.get("igv"), comprobante.get("subtotal"))
    _agregar_totales(root, comprobante)

    lineas = detalle or []
    if not lineas:
        lineas = [{
            "descripcion": comprobante.get("concepto"),
            "cantidad": 1,
            "valor_unitario": comprobante.get("subtotal") or comprobante.get("total"),
            "subtotal": comprobante.get("subtotal") or comprobante.get("total"),
            "igv": comprobante.get("igv") or 0,
            "total": comprobante.get("total") or 0,
        }]
    for index, item in enumerate(lineas, start=1):
        _agregar_linea(root, index, item, comprobante.get("moneda") or "PEN")

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _agregar_emisor(root, config):
    supplier = ET.SubElement(root, _q("cac", "AccountingSupplierParty"))
    party = ET.SubElement(supplier, _q("cac", "Party"))
    party_id = ET.SubElement(party, _q("cac", "PartyIdentification"))
    _text(party_id, "cbc", "ID", config.get("ruc"), {"schemeID": "6"})
    legal = ET.SubElement(party, _q("cac", "PartyLegalEntity"))
    _text(legal, "cbc", "RegistrationName", config.get("razon_social"))
    address = ET.SubElement(legal, _q("cac", "RegistrationAddress"))
    _text(address, "cbc", "AddressTypeCode", "0000")
    address_line = ET.SubElement(address, _q("cac", "AddressLine"))
    _text(address_line, "cbc", "Line", config.get("direccion") or "Lambayeque")


def _agregar_cliente(root, comprobante):
    customer = ET.SubElement(root, _q("cac", "AccountingCustomerParty"))
    party = ET.SubElement(customer, _q("cac", "Party"))
    numero = comprobante.get("numero_documento_cliente")
    tipo = _tipo_documento_codigo(comprobante.get("tipo_documento_cliente"), numero)
    party_id = ET.SubElement(party, _q("cac", "PartyIdentification"))
    _text(party_id, "cbc", "ID", numero, {"schemeID": tipo})
    legal = ET.SubElement(party, _q("cac", "PartyLegalEntity"))
    _text(legal, "cbc", "RegistrationName", comprobante.get("cliente_nombre"))


def _agregar_impuestos(root, igv, subtotal):
    tributo = _tributo_igv(igv)
    tax_total = ET.SubElement(root, _q("cac", "TaxTotal"))
    _text(tax_total, "cbc", "TaxAmount", _money(igv), {"currencyID": "PEN"})
    subtotal_node = ET.SubElement(tax_total, _q("cac", "TaxSubtotal"))
    _text(subtotal_node, "cbc", "TaxableAmount", _money(subtotal), {"currencyID": "PEN"})
    _text(subtotal_node, "cbc", "TaxAmount", _money(igv), {"currencyID": "PEN"})
    category = ET.SubElement(subtotal_node, _q("cac", "TaxCategory"))
    _text(category, "cbc", "ID", tributo["categoria"], {
        "schemeID": "UN/ECE 5305",
        "schemeName": "Tax Category Identifier",
        "schemeAgencyName": "United Nations Economic Commission for Europe",
    })
    _text(category, "cbc", "Percent", tributo["porcentaje"])
    _text(category, "cbc", "TaxExemptionReasonCode", tributo["afectacion"], {
        "listAgencyName": "PE:SUNAT",
        "listName": "Afectacion del IGV",
        "listURI": "urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo07",
    })
    scheme = ET.SubElement(category, _q("cac", "TaxScheme"))
    _text(scheme, "cbc", "ID", tributo["tributo_id"], {
        "schemeID": "UN/ECE 5153",
        "schemeName": "Codigo de tributos",
        "schemeAgencyName": "PE:SUNAT",
    })
    _text(scheme, "cbc", "Name", tributo["tributo_nombre"])
    _text(scheme, "cbc", "TaxTypeCode", tributo["tributo_tipo"])


def _agregar_totales(root, comprobante):
    total = ET.SubElement(root, _q("cac", "LegalMonetaryTotal"))
    moneda = comprobante.get("moneda") or "PEN"
    _text(total, "cbc", "LineExtensionAmount", _money(comprobante.get("subtotal")), {"currencyID": moneda})
    _text(total, "cbc", "TaxInclusiveAmount", _money(comprobante.get("total")), {"currencyID": moneda})
    _text(total, "cbc", "PayableAmount", _money(comprobante.get("total")), {"currencyID": moneda})


def _agregar_linea(root, index, item, moneda):
    line = ET.SubElement(root, _q("cac", "InvoiceLine"))
    _text(line, "cbc", "ID", index)
    _text(line, "cbc", "InvoicedQuantity", _money(item.get("cantidad") or 1), {"unitCode": "NIU"})
    _text(line, "cbc", "LineExtensionAmount", _money(item.get("subtotal")), {"currencyID": moneda})

    pricing = ET.SubElement(line, _q("cac", "PricingReference"))
    alt = ET.SubElement(pricing, _q("cac", "AlternativeConditionPrice"))
    _text(alt, "cbc", "PriceAmount", _money(item.get("total")), {"currencyID": moneda})
    _text(alt, "cbc", "PriceTypeCode", "01")

    _agregar_impuestos(line, item.get("igv"), item.get("subtotal"))

    item_node = ET.SubElement(line, _q("cac", "Item"))
    _text(item_node, "cbc", "Description", item.get("descripcion"))
    price = ET.SubElement(line, _q("cac", "Price"))
    _text(price, "cbc", "PriceAmount", _money(item.get("valor_unitario")), {"currencyID": moneda})


def firmar_xml(xml_bytes, certificado_ruta, certificado_clave):
    try:
        from cryptography.hazmat.primitives.serialization import Encoding, pkcs12
        from lxml import etree
        from signxml import XMLSigner, methods
    except Exception as exc:
        raise SunatBetaError(
            "Falta soporte de firma XML. Instale signxml con: pip install signxml"
        ) from exc

    cert_path = Path(certificado_ruta)
    password = str(certificado_clave or "").encode("utf-8")
    key, cert, extra_certs = pkcs12.load_key_and_certificates(cert_path.read_bytes(), password)
    if key is None or cert is None:
        raise SunatBetaError("El certificado .pfx/.p12 no contiene llave privada y certificado.")

    parser = etree.XMLParser(remove_blank_text=True)
    root = etree.fromstring(xml_bytes, parser=parser)
    signer = XMLSigner(
        method=methods.enveloped,
        signature_algorithm="rsa-sha256",
        digest_algorithm="sha256",
        c14n_algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315",
    )
    signed = signer.sign(
        root,
        key=key,
        cert=cert.public_bytes(Encoding.PEM),
        always_add_key_value=False,
    )

    ds_signature = signed.find("{http://www.w3.org/2000/09/xmldsig#}Signature")
    extension_content = signed.find(
        ".//{urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2}ExtensionContent"
    )
    if ds_signature is not None and extension_content is not None:
        signed.remove(ds_signature)
        extension_content.append(ds_signature)

    return etree.tostring(signed, encoding="utf-8", xml_declaration=True)


def crear_zip(nombre_xml, xml_bytes):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr(nombre_xml, xml_bytes)
    return buffer.getvalue()


def enviar_zip_sunat(config, nombre_zip, zip_bytes):
    try:
        import requests
    except Exception as exc:
        raise SunatBetaError(
            "Falta instalar requests en el entorno virtual. Ejecute: python -m pip install -r requirements.txt"
        ) from exc

    usuario = str(config.get("ruc") or "") + str(config.get("usuario_sol") or "")
    clave = str(config.get("clave_sol") or "")
    endpoint = (config.get("endpoint_beta") or SUNAT_BETA_ENDPOINT).strip()
    contenido = base64.b64encode(zip_bytes).decode("ascii")
    envelope = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="{SOAP_NS}" xmlns:ser="{SUNAT_NS}">
  <soapenv:Header/>
  <soapenv:Body>
    <ser:sendBill>
      <fileName>{nombre_zip}</fileName>
      <contentFile>{contenido}</contentFile>
    </ser:sendBill>
  </soapenv:Body>
</soapenv:Envelope>"""
    response = requests.post(
        endpoint,
        data=envelope.encode("utf-8"),
        headers={
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "sendBill",
        },
        auth=(usuario, clave),
        timeout=40,
    )
    return _interpretar_respuesta_sunat(response)


def _interpretar_respuesta_sunat(response):
    respuesta = {
        "status_code": response.status_code,
        "raw": response.text[:4000],
        "aceptado": False,
        "ticket": "",
        "codigo": "",
        "cdr_estado": "",
        "cdr_descripcion": "",
        "cdr_base64": "",
    }
    try:
        root = ET.fromstring(response.content)
    except ET.ParseError:
        respuesta["cdr_estado"] = "Error"
        respuesta["cdr_descripcion"] = "SUNAT no devolvio XML valido."
        return respuesta

    fault = root.find(".//faultstring")
    if fault is not None and fault.text:
        respuesta["cdr_estado"] = "Rechazado"
        respuesta["cdr_descripcion"] = fault.text
        respuesta["codigo"] = "SOAP_FAULT"
        return respuesta

    application_response = None
    for node in root.iter():
        if node.tag.endswith("applicationResponse"):
            application_response = node
            break
    if application_response is None or not application_response.text:
        respuesta["cdr_estado"] = "Observado"
        respuesta["cdr_descripcion"] = "SUNAT no devolvio CDR en la respuesta."
        return respuesta

    respuesta["aceptado"] = response.status_code == 200
    respuesta["ticket"] = "CDR-" + date.today().strftime("%Y%m%d")
    respuesta["codigo"] = "CDR_RECIBIDO"
    respuesta["cdr_estado"] = "Aceptado" if respuesta["aceptado"] else "Observado"
    respuesta["cdr_descripcion"] = "SUNAT devolvio CDR para el comprobante."
    respuesta["cdr_base64"] = application_response.text
    return respuesta


def enviar_comprobante_sunat_beta(config, comprobante, detalle, carpeta_salida):
    _validar_config_beta(config)
    carpeta = Path(carpeta_salida)
    carpeta.mkdir(parents=True, exist_ok=True)

    base = _nombre_archivo_base(config, comprobante)
    nombre_xml = base + ".xml"
    nombre_zip = base + ".zip"
    nombre_cdr = "R-" + nombre_zip

    xml = generar_xml_ubl(config, comprobante, detalle)
    xml_firmado = firmar_xml(
        xml,
        config.get("certificado_ruta"),
        config.get("certificado_clave"),
    )
    zip_bytes = crear_zip(nombre_xml, xml_firmado)

    (carpeta / nombre_xml).write_bytes(xml_firmado)
    (carpeta / nombre_zip).write_bytes(zip_bytes)

    respuesta = enviar_zip_sunat(config, nombre_zip, zip_bytes)
    if respuesta.get("cdr_base64"):
        try:
            (carpeta / nombre_cdr).write_bytes(base64.b64decode(respuesta["cdr_base64"]))
        except Exception:
            pass

    respuesta.update({
        "modo": "SUNAT_BETA",
        "xml_archivo": "uploads/sunat/" + nombre_xml,
        "zip_archivo": "uploads/sunat/" + nombre_zip,
        "cdr_archivo": "uploads/sunat/" + nombre_cdr if respuesta.get("cdr_base64") else "",
        "nombre_zip": nombre_zip,
    })
    respuesta["json"] = json.dumps(respuesta, ensure_ascii=False)
    return respuesta
