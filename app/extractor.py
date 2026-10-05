"""Extracción de datos de facturas en PDF mediante reglas (expresiones regulares)."""
from __future__ import annotations

import re
from datetime import datetime
from typing import BinaryIO

from .validacion import normalizar_cuit, validar_factura


def extraer_texto(fuente: str | BinaryIO) -> str:
    """Lee el texto de un PDF (ruta o archivo en memoria). No hace OCR."""
    import pdfplumber

    paginas = []
    with pdfplumber.open(fuente) as pdf:
        for pagina in pdf.pages:
            paginas.append(pagina.extract_text() or "")
    return "\n".join(paginas)


def parsear_monto(texto: str | None) -> float | None:
    """Convierte '1.234,56', '$ 1234,56' o '1,234.56' en float."""
    if not texto:
        return None
    limpio = re.sub(r"[^\d.,]", "", texto)
    if not limpio:
        return None
    if "," in limpio and "." in limpio:
        # El último separador es el decimal.
        if limpio.rfind(",") > limpio.rfind("."):
            limpio = limpio.replace(".", "").replace(",", ".")
        else:
            limpio = limpio.replace(",", "")
    elif "," in limpio:
        limpio = limpio.replace(",", ".")
    elif "." in limpio:
        # Un solo tipo de separador: decimal si tiene exactamente 2 dígitos al final.
        if not re.search(r"\.\d{2}$", limpio):
            limpio = limpio.replace(".", "")
    try:
        return round(float(limpio), 2)
    except ValueError:
        return None


def parsear_fecha(texto: str | None) -> str | None:
    """Convierte DD/MM/AAAA (o AAAA-MM-DD) a formato ISO AAAA-MM-DD."""
    if not texto:
        return None
    texto = texto.strip()
    for formato in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto, formato).date().isoformat()
        except ValueError:
            continue
    return None


_MONTO = r"\$?[ \t]*([\d.]+,\d{2})"


def extraer_con_reglas(texto: str) -> dict:
    """Extrae los campos principales de una factura a partir de su texto."""
    datos: dict = {}

    m = re.search(r"Factura\s+([ABCEM])\b", texto, re.IGNORECASE)
    datos["tipo"] = m.group(1).upper() if m else None

    m = re.search(r"Punto de Venta:?[ \t]*(\d{1,5}).*?Comp\.?[ \t]*Nro\.?:?[ \t]*(\d{1,8})", texto, re.IGNORECASE)
    if m:
        datos["numero"] = f"{m.group(1).zfill(4)}-{m.group(2).zfill(8)}"
    else:
        m = re.search(r"\b(\d{4,5}-\d{8})\b", texto)
        datos["numero"] = m.group(1) if m else None

    m = re.search(r"Fecha(?: de emisi[oó]n)?:?[ \t]*(\d{2}[/-]\d{2}[/-]\d{4})", texto, re.IGNORECASE)
    datos["fecha"] = parsear_fecha(m.group(1)) if m else None

    m = re.search(r"Raz[oó]n Social:?[ \t]*(.+)", texto, re.IGNORECASE)
    datos["proveedor"] = m.group(1).strip() if m else None

    cuits = re.findall(r"CUIT:?[ \t]*(\d{2}-?\d{8}-?\d)", texto, re.IGNORECASE)
    datos["cuit_proveedor"] = normalizar_cuit(cuits[0]) if len(cuits) > 0 else None
    datos["cuit_cliente"] = normalizar_cuit(cuits[1]) if len(cuits) > 1 else None

    m = re.search(r"Importe Neto(?: Gravado)?:?[ \t]*" + _MONTO, texto, re.IGNORECASE)
    if not m:
        m = re.search(r"Subtotal:?[ \t]*" + _MONTO, texto, re.IGNORECASE)
    datos["neto"] = parsear_monto(m.group(1)) if m else None

    m = re.search(r"IVA(?:[ \t]*\d{1,2}(?:[.,]\d+)?[ \t]*%)?:?[ \t]*" + _MONTO, texto, re.IGNORECASE)
    datos["iva"] = parsear_monto(m.group(1)) if m else None

    # Se toma el último "Total" que no sea "Subtotal".
    totales = re.findall(r"(?<!sub)total:?[ \t]*" + _MONTO, texto, re.IGNORECASE)
    datos["total"] = parsear_monto(totales[-1]) if totales else None

    return datos


def procesar_factura(fuente: str | BinaryIO, nombre_archivo: str, modo: str = "reglas") -> dict:
    """Extrae y valida los datos de una factura. Modo: 'reglas' o 'ia'."""
    texto = extraer_texto(fuente)
    if not texto.strip():
        raise ValueError(
            "El PDF no contiene texto (puede ser un escaneo). Este prototipo no hace OCR."
        )

    if modo == "ia":
        from .llm import extraer_con_llm

        datos = extraer_con_llm(texto)
    elif modo == "reglas":
        datos = extraer_con_reglas(texto)
    else:
        raise ValueError("Modo inválido: usá 'reglas' o 'ia'")

    datos["archivo"] = nombre_archivo
    datos["metodo"] = modo
    datos["advertencias"] = validar_factura(datos)
    return datos
