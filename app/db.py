"""Persistencia en SQLite y exportación a CSV."""
from __future__ import annotations

import csv
import os
import sqlite3
from typing import Iterable, TextIO

RUTA_POR_DEFECTO = os.getenv("FACTURAS_DB", "facturas.db")

ESQUEMA = """
CREATE TABLE IF NOT EXISTS facturas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    archivo TEXT,
    tipo TEXT,
    numero TEXT,
    fecha TEXT,
    proveedor TEXT,
    cuit_proveedor TEXT,
    cuit_cliente TEXT,
    neto REAL,
    iva REAL,
    total REAL,
    metodo TEXT,
    advertencias TEXT,
    creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (cuit_proveedor, tipo, numero)
)
"""

COLUMNAS = [
    "id", "archivo", "tipo", "numero", "fecha", "proveedor", "cuit_proveedor",
    "cuit_cliente", "neto", "iva", "total", "metodo", "advertencias", "creado_en",
]


def conectar(ruta: str = RUTA_POR_DEFECTO) -> sqlite3.Connection:
    conexion = sqlite3.connect(ruta)
    conexion.row_factory = sqlite3.Row
    conexion.execute(ESQUEMA)
    return conexion


def guardar_factura(conexion: sqlite3.Connection, datos: dict) -> tuple[int | None, bool]:
    """Inserta la factura. Devuelve (id, creada). Si ya existía, creada=False."""
    try:
        cursor = conexion.execute(
            """INSERT INTO facturas
               (archivo, tipo, numero, fecha, proveedor, cuit_proveedor, cuit_cliente,
                neto, iva, total, metodo, advertencias)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                datos.get("archivo"), datos.get("tipo"), datos.get("numero"), datos.get("fecha"),
                datos.get("proveedor"), datos.get("cuit_proveedor"), datos.get("cuit_cliente"),
                datos.get("neto"), datos.get("iva"), datos.get("total"), datos.get("metodo"),
                "; ".join(datos.get("advertencias", [])),
            ),
        )
        conexion.commit()
        return cursor.lastrowid, True
    except sqlite3.IntegrityError:
        fila = conexion.execute(
            "SELECT id FROM facturas WHERE cuit_proveedor IS ? AND tipo IS ? AND numero IS ?",
            (datos.get("cuit_proveedor"), datos.get("tipo"), datos.get("numero")),
        ).fetchone()
        return (fila["id"] if fila else None), False


def listar_facturas(conexion: sqlite3.Connection) -> list[dict]:
    filas = conexion.execute("SELECT * FROM facturas ORDER BY id").fetchall()
    return [dict(f) for f in filas]


def obtener_factura(conexion: sqlite3.Connection, id_factura: int) -> dict | None:
    fila = conexion.execute("SELECT * FROM facturas WHERE id = ?", (id_factura,)).fetchone()
    return dict(fila) if fila else None


def exportar_csv(facturas: Iterable[dict], destino: TextIO) -> None:
    escritor = csv.DictWriter(destino, fieldnames=COLUMNAS, extrasaction="ignore")
    escritor.writeheader()
    for factura in facturas:
        escritor.writerow(factura)
