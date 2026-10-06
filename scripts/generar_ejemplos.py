"""Genera facturas PDF de ejemplo con datos FICTICIOS para probar el prototipo.

Uso (desde la raíz del proyecto):  python scripts/generar_ejemplos.py
Requiere reportlab:               pip install reportlab
"""
from pathlib import Path
import sys

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.validacion import calcular_digito_cuit  # noqa: E402


def cuit_ficticio(base10: str) -> str:
    digito = calcular_digito_cuit(base10)
    return f"{base10[:2]}-{base10[2:]}-{digito}"


def fmt(valor: float) -> str:
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


FACTURAS = [
    {
        "archivo": "factura_01.pdf",
        "proveedor": "Distribuidora Norte Demo S.R.L.",
        "cuit": cuit_ficticio("3070000001"),
        "pv": "0001", "nro": "00001234", "fecha": "15/09/2026",
        "cliente": "Comercial Ejemplo S.A.", "cuit_cliente": cuit_ficticio("3070000099"),
        "items": [("Mercaderia varia - lote A", 1, 60000.00), ("Flete y logistica", 1, 40000.00)],
        "etiqueta_neto": "Importe Neto Gravado", "iva_pct": 21,
        "neto": 100000.00, "iva": 21000.00, "total": 121000.00,
    },
    {
        "archivo": "factura_02.pdf",
        "proveedor": "Servicios Tucuman Demo S.A.",
        "cuit": cuit_ficticio("3070000002"),
        "pv": "0003", "nro": "00000087", "fecha": "02/10/2026",
        "cliente": "Comercial Ejemplo S.A.", "cuit_cliente": cuit_ficticio("3070000099"),
        "items": [("Servicio de mantenimiento mensual", 1, 45500.50)],
        "etiqueta_neto": "Subtotal", "iva_pct": 21,
        "neto": 45500.50, "iva": 9555.11, "total": 55055.61,
    },
    {
        # Esta factura tiene un total que NO cierra, a propósito, para mostrar las advertencias.
        "archivo": "factura_03.pdf",
        "proveedor": "Ferreteria Demo S.R.L.",
        "cuit": cuit_ficticio("3070000003"),
        "pv": "0002", "nro": "00000455", "fecha": "28/09/2026",
        "cliente": "Comercial Ejemplo S.A.", "cuit_cliente": cuit_ficticio("3070000099"),
        "items": [("Herramientas y repuestos", 1, 20000.00)],
        "etiqueta_neto": "Importe Neto Gravado", "iva_pct": 21,
        "neto": 20000.00, "iva": 4200.00, "total": 25000.00,
    },
]


def generar(datos: dict, destino: Path) -> None:
    c = canvas.Canvas(str(destino), pagesize=A4)
    _, alto = A4
    y = alto - 60

    def linea(texto, x=50, salto=18, fuente="Helvetica", tam=11):
        nonlocal y
        c.setFont(fuente, tam)
        c.drawString(x, y, texto)
        y -= salto

    linea("FACTURA A", fuente="Helvetica-Bold", tam=18, salto=28)
    linea(f"Razon Social: {datos['proveedor']}")
    linea(f"CUIT: {datos['cuit']}")
    linea(f"Punto de Venta: {datos['pv']}   Comp. Nro: {datos['nro']}")
    linea(f"Fecha de emision: {datos['fecha']}")
    linea("Condicion frente al IVA: Responsable Inscripto", salto=30)

    linea(f"Cliente: {datos['cliente']}")
    linea(f"CUIT: {datos['cuit_cliente']}", salto=30)

    linea("Descripcion                         Cant.          Importe", fuente="Helvetica-Bold", salto=20)
    for descripcion, cantidad, importe in datos["items"]:
        linea(f"{descripcion}", salto=0)
        c.drawString(330, y, str(cantidad))
        c.drawString(420, y, fmt(importe))
        y -= 18
    y -= 14

    linea(f"{datos['etiqueta_neto']}: $ {fmt(datos['neto'])}")
    linea(f"IVA {datos['iva_pct']}%: $ {fmt(datos['iva'])}")
    linea(f"Importe Total: $ {fmt(datos['total'])}", fuente="Helvetica-Bold", salto=40)

    linea("Documento de ejemplo - datos ficticios", fuente="Helvetica-Oblique", tam=9)
    c.save()


if __name__ == "__main__":
    carpeta = Path(__file__).resolve().parent.parent / "ejemplos"
    carpeta.mkdir(exist_ok=True)
    for factura in FACTURAS:
        generar(factura, carpeta / factura["archivo"])
        print("Generada:", carpeta / factura["archivo"])
