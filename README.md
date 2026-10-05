# Automatización de carga de facturas

Prototipo en Python que lee facturas en PDF, extrae sus datos (proveedor, CUIT, número, fecha, neto, IVA y total), los valida y los guarda en una base SQLite, con exportación a CSV. Se puede usar desde la línea de comandos o como API REST con FastAPI.

Surgió de una necesidad real: la carga manual de facturas de proveedores en una empresa familiar. Es un **prototipo**: todos los ejemplos del repositorio son facturas ficticias.

## Qué hace

- Extrae el texto del PDF (`pdfplumber`) y obtiene los campos con expresiones regulares.
- Entiende el formato numérico argentino (`1.234,56`) y normaliza fechas a ISO.
- **Valida** el resultado: dígito verificador del CUIT (módulo 11) y que `neto + IVA = total`. Si algo no cierra, lo informa como advertencia en lugar de ocultarlo.
- Guarda en SQLite y **evita cargar dos veces** la misma factura (mismo CUIT, tipo y número).
- Exporta todo a CSV.
- Modo opcional `ia`: delega la extracción en un modelo de lenguaje (API de Claude). Su respuesta pasa por las mismas validaciones.

## Tecnologías

Python 3, FastAPI, SQLite (`sqlite3`), pdfplumber, unittest. Opcional: SDK de Anthropic.

## Instalación

Requiere Python 3.10 o superior.

```bash
git clone https://github.com/ivechetti/automatizacion-facturas.git
cd automatizacion-facturas
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

En Linux o macOS: `python3 -m venv .venv` y `source .venv/bin/activate`.

## Uso desde la línea de comandos

```bash
python -m app.cli ejemplos                    # procesa todos los PDF de la carpeta
python -m app.cli ejemplos/factura_01.pdf     # procesa un solo PDF
python -m app.cli ejemplos --csv salida.csv   # y exporta todo a CSV
```

Salida de ejemplo:

```
[guardada] factura_01.pdf: Distribuidora Norte Demo S.R.L. | A 0001-00001234 | 2026-09-15 | total 121000.0
[guardada] factura_03.pdf: Ferreteria Demo S.R.L. | A 0002-00000455 | 2026-09-28 | total 25000.0
    ! Los importes no cierran: neto 20000.00 + IVA 4200.00 != total 25000.00
```

Si se vuelve a correr sobre los mismos archivos, informa `duplicada (ya existía)` y no inserta de nuevo. `factura_03.pdf` tiene un total incorrecto a propósito para mostrar las advertencias.

## Uso como API

```bash
py -m uvicorn app.main:app --reload
```

Abrí http://127.0.0.1:8000/docs (Swagger) para probar los endpoints:

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/facturas?modo=reglas` | Sube un PDF, extrae y guarda los datos |
| GET | `/facturas` | Lista las facturas guardadas |
| GET | `/facturas/{id}` | Detalle de una factura |
| GET | `/facturas/exportar/csv` | Descarga todo en CSV |

Códigos de respuesta: `201` creada, `400` no es PDF, `409` factura duplicada, `413` archivo mayor a 10 MB, `422` PDF sin texto o ilegible.

## Modo IA (opcional)

```bash
pip install anthropic
set ANTHROPIC_API_KEY=tu_clave
python -m app.cli ejemplos --modo ia
```

El modelo se puede cambiar con la variable `ANTHROPIC_MODEL`. Requiere una clave de API propia y envía el texto de la factura a un servicio externo, algo a tener en cuenta con datos reales de una empresa.

## Tests

```bash
python -m unittest discover -s tests -t . -v
```

Cubren el parseo de montos y fechas, la validación de CUIT, la extracción sobre los PDF de ejemplo, la persistencia (incluido el duplicado) y la exportación a CSV.

## Limitaciones

- Solo PDF con texto seleccionable. **No hace OCR**: un escaneo se rechaza con un mensaje claro.
- Las reglas están pensadas para facturas con etiquetas como `Razón Social`, `CUIT`, `Importe Total`. Un diseño muy distinto puede requerir ajustar las expresiones regulares o usar el modo `ia`.
- Toma un solo total por factura y no extrae el detalle de ítems.
- La API no tiene autenticación: es un prototipo para uso local.

## Posibles mejoras

- OCR (Tesseract) para facturas escaneadas.
- Extraer el detalle de ítems y múltiples alícuotas de IVA.
- Interfaz web para revisar y corregir las advertencias antes de guardar.
- Autenticación y despliegue con Docker.
