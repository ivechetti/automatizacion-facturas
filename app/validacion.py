"""Validaciones de los datos extraídos de una factura."""
from __future__ import annotations

import re

_PESOS_CUIT = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]


def normalizar_cuit(valor: str | None) -> str | None:
    """Devuelve el CUIT con formato XX-XXXXXXXX-X o None si no tiene 11 dígitos."""
    if not valor:
        return None
    digitos = re.sub(r"\D", "", valor)
    if len(digitos) != 11:
        return None
    return f"{digitos[:2]}-{digitos[2:10]}-{digitos[10]}"


def cuit_valido(valor: str | None) -> bool:
    """Valida el dígito verificador del CUIT/CUIL (módulo 11)."""
    cuit = normalizar_cuit(valor)
    if cuit is None:
        return False
    digitos = [int(c) for c in cuit if c.isdigit()]
    suma = sum(d * p for d, p in zip(digitos[:10], _PESOS_CUIT))
    resto = 11 - (suma % 11)
    if resto == 11:
        resto = 0
    if resto == 10:
        return False
    return resto == digitos[10]


def calcular_digito_cuit(base10: str) -> int | None:
    """Calcula el dígito verificador para los primeros 10 dígitos de un CUIT."""
    digitos = [int(c) for c in base10]
    suma = sum(d * p for d, p in zip(digitos, _PESOS_CUIT))
    resto = 11 - (suma % 11)
    if resto == 11:
        return 0
    if resto == 10:
        return None
    return resto


def validar_factura(datos: dict) -> list[str]:
    """Devuelve una lista de advertencias sobre los datos de la factura."""
    advertencias: list[str] = []

    for campo in ("numero", "fecha", "proveedor", "cuit_proveedor", "total"):
        if not datos.get(campo):
            advertencias.append(f"Falta el campo '{campo}'")

    if datos.get("cuit_proveedor") and not cuit_valido(datos["cuit_proveedor"]):
        advertencias.append("El CUIT del proveedor no tiene un dígito verificador válido")

    if datos.get("cuit_cliente") and not cuit_valido(datos["cuit_cliente"]):
        advertencias.append("El CUIT del cliente no tiene un dígito verificador válido")

    neto, iva, total = datos.get("neto"), datos.get("iva"), datos.get("total")
    if neto is not None and iva is not None and total is not None:
        if abs((neto + iva) - total) > 0.01:
            advertencias.append(
                f"Los importes no cierran: neto {neto:.2f} + IVA {iva:.2f} != total {total:.2f}"
            )

    return advertencias
