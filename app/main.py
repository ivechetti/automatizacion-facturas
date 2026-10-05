"""API REST para cargar facturas en PDF y consultarlas.

Levantar:  uvicorn app.main:app --reload
Docs:      http://127.0.0.1:8000/docs
"""
from __future__ import annotations

import io

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse

from .db import conectar, exportar_csv, guardar_factura, listar_facturas, obtener_factura
from .extractor import procesar_factura

TAMANO_MAXIMO = 10 * 1024 * 1024  # 10 MB

app = FastAPI(
    title="Automatización de carga de facturas",
    description="Sube facturas en PDF, extrae sus datos y los guarda en SQLite.",
)


@app.post("/facturas", status_code=201)
async def subir_factura(
    archivo: UploadFile = File(...),
    modo: str = Query("reglas", pattern="^(reglas|ia)$"),
):
    nombre = archivo.filename or "factura.pdf"
    if not nombre.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos PDF")

    contenido = await archivo.read()
    if len(contenido) > TAMANO_MAXIMO:
        raise HTTPException(status_code=413, detail="El archivo supera los 10 MB")

    try:
        datos = procesar_factura(io.BytesIO(contenido), nombre, modo)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error))

    conexion = conectar()
    try:
        id_factura, creada = guardar_factura(conexion, datos)
    finally:
        conexion.close()

    if not creada:
        raise HTTPException(
            status_code=409, detail=f"La factura ya fue cargada (id {id_factura})"
        )
    datos["id"] = id_factura
    return datos


@app.get("/facturas")
def listar():
    conexion = conectar()
    try:
        return listar_facturas(conexion)
    finally:
        conexion.close()


@app.get("/facturas/exportar/csv")
def exportar():
    conexion = conectar()
    try:
        facturas = listar_facturas(conexion)
    finally:
        conexion.close()

    salida = io.StringIO()
    exportar_csv(facturas, salida)
    salida.seek(0)
    return StreamingResponse(
        iter([salida.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=facturas.csv"},
    )


@app.get("/facturas/{id_factura}")
def detalle(id_factura: int):
    conexion = conectar()
    try:
        factura = obtener_factura(conexion, id_factura)
    finally:
        conexion.close()
    if factura is None:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    return factura
