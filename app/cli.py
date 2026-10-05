"""Procesa facturas en PDF desde la línea de comandos.

Uso:
    python -m app.cli ejemplos                      # carpeta con PDFs
    python -m app.cli ejemplos/factura_01.pdf       # un PDF
    python -m app.cli ejemplos --csv salida.csv     # y exporta todo a CSV
    python -m app.cli ejemplos --modo ia            # extracción con IA (requiere API key)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .db import RUTA_POR_DEFECTO, conectar, exportar_csv, guardar_factura, listar_facturas
from .extractor import procesar_factura


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Carga automática de facturas en PDF")
    parser.add_argument("ruta", help="Archivo PDF o carpeta con PDFs")
    parser.add_argument("--modo", choices=["reglas", "ia"], default="reglas")
    parser.add_argument("--db", default=RUTA_POR_DEFECTO, help="Archivo SQLite de destino")
    parser.add_argument("--csv", help="Exporta todas las facturas guardadas a este CSV")
    args = parser.parse_args(argv)

    ruta = Path(args.ruta)
    pdfs = sorted(ruta.glob("*.pdf")) if ruta.is_dir() else [ruta]
    if not pdfs:
        print("No se encontraron archivos PDF.")
        return 1

    conexion = conectar(args.db)
    errores = 0
    for pdf in pdfs:
        try:
            datos = procesar_factura(str(pdf), pdf.name, args.modo)
        except Exception as error:  # noqa: BLE001 - se informa y se sigue con el resto
            print(f"[ERROR] {pdf.name}: {error}")
            errores += 1
            continue

        id_factura, creada = guardar_factura(conexion, datos)
        estado = "guardada" if creada else "duplicada (ya existía)"
        print(
            f"[{estado}] {pdf.name}: {datos.get('proveedor')} | {datos.get('tipo')} "
            f"{datos.get('numero')} | {datos.get('fecha')} | total {datos.get('total')}"
        )
        for advertencia in datos["advertencias"]:
            print(f"    ! {advertencia}")

    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as archivo:
            exportar_csv(listar_facturas(conexion), archivo)
        print(f"CSV exportado en {args.csv}")

    conexion.close()
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
