import io
import unittest
from pathlib import Path

from app.db import conectar, exportar_csv, guardar_factura, listar_facturas
from app.extractor import parsear_fecha, parsear_monto, procesar_factura
from app.llm import normalizar_respuesta
from app.validacion import calcular_digito_cuit, cuit_valido, normalizar_cuit, validar_factura

EJEMPLOS = Path(__file__).resolve().parent.parent / "ejemplos"


class TestParseo(unittest.TestCase):
    def test_montos_formato_argentino(self):
        self.assertEqual(parsear_monto("1.234,56"), 1234.56)
        self.assertEqual(parsear_monto("$ 121.000,00"), 121000.0)
        self.assertEqual(parsear_monto("45,5"), 45.5)

    def test_montos_formato_ingles_y_sin_separador(self):
        self.assertEqual(parsear_monto("1,234.56"), 1234.56)
        self.assertEqual(parsear_monto("1234"), 1234.0)
        self.assertEqual(parsear_monto("1.234"), 1234.0)

    def test_monto_invalido(self):
        self.assertIsNone(parsear_monto(""))
        self.assertIsNone(parsear_monto(None))
        self.assertIsNone(parsear_monto("abc"))

    def test_fechas(self):
        self.assertEqual(parsear_fecha("15/09/2026"), "2026-09-15")
        self.assertEqual(parsear_fecha("2026-09-15"), "2026-09-15")
        self.assertIsNone(parsear_fecha("31/02/2026"))
        self.assertIsNone(parsear_fecha(None))


class TestCuit(unittest.TestCase):
    def test_cuit_valido(self):
        self.assertTrue(cuit_valido("20-12345678-6"))
        self.assertTrue(cuit_valido("20123456786"))

    def test_cuit_invalido(self):
        self.assertFalse(cuit_valido("20-12345678-5"))
        self.assertFalse(cuit_valido("123"))
        self.assertFalse(cuit_valido(None))

    def test_normalizar(self):
        self.assertEqual(normalizar_cuit("20123456786"), "20-12345678-6")
        self.assertIsNone(normalizar_cuit("12"))

    def test_digito_calculado(self):
        self.assertEqual(calcular_digito_cuit("2012345678"), 6)


class TestValidacion(unittest.TestCase):
    def test_importes_que_no_cierran(self):
        datos = {
            "numero": "0001-00000001", "fecha": "2026-01-01", "proveedor": "X",
            "cuit_proveedor": "20-12345678-6", "neto": 100.0, "iva": 21.0, "total": 130.0,
        }
        advertencias = validar_factura(datos)
        self.assertTrue(any("no cierran" in a for a in advertencias))

    def test_campos_faltantes(self):
        advertencias = validar_factura({})
        self.assertGreaterEqual(len(advertencias), 5)

    def test_factura_correcta_sin_advertencias(self):
        datos = {
            "numero": "0001-00000001", "fecha": "2026-01-01", "proveedor": "X",
            "cuit_proveedor": "20-12345678-6", "neto": 100.0, "iva": 21.0, "total": 121.0,
        }
        self.assertEqual(validar_factura(datos), [])


class TestExtraccionPDF(unittest.TestCase):
    def test_factura_01(self):
        d = procesar_factura(str(EJEMPLOS / "factura_01.pdf"), "factura_01.pdf")
        self.assertEqual(d["tipo"], "A")
        self.assertEqual(d["numero"], "0001-00001234")
        self.assertEqual(d["fecha"], "2026-09-15")
        self.assertEqual(d["proveedor"], "Distribuidora Norte Demo S.R.L.")
        self.assertEqual(d["neto"], 100000.0)
        self.assertEqual(d["iva"], 21000.0)
        self.assertEqual(d["total"], 121000.0)
        self.assertEqual(d["advertencias"], [])

    def test_factura_02_usa_subtotal_como_neto(self):
        d = procesar_factura(str(EJEMPLOS / "factura_02.pdf"), "factura_02.pdf")
        self.assertEqual(d["neto"], 45500.50)
        self.assertEqual(d["total"], 55055.61)
        self.assertEqual(d["advertencias"], [])

    def test_factura_03_detecta_total_incorrecto(self):
        d = procesar_factura(str(EJEMPLOS / "factura_03.pdf"), "factura_03.pdf")
        self.assertTrue(any("no cierran" in a for a in d["advertencias"]))

    def test_acepta_archivo_en_memoria(self):
        contenido = (EJEMPLOS / "factura_01.pdf").read_bytes()
        d = procesar_factura(io.BytesIO(contenido), "subida.pdf")
        self.assertEqual(d["numero"], "0001-00001234")

    def test_modo_invalido(self):
        with self.assertRaises(ValueError):
            procesar_factura(str(EJEMPLOS / "factura_01.pdf"), "x.pdf", modo="otro")


class TestBaseDeDatos(unittest.TestCase):
    def setUp(self):
        self.conexion = conectar(":memory:")
        self.datos = procesar_factura(str(EJEMPLOS / "factura_01.pdf"), "factura_01.pdf")

    def tearDown(self):
        self.conexion.close()

    def test_guarda_y_detecta_duplicado(self):
        id1, creada1 = guardar_factura(self.conexion, self.datos)
        id2, creada2 = guardar_factura(self.conexion, self.datos)
        self.assertTrue(creada1)
        self.assertFalse(creada2)
        self.assertEqual(id1, id2)
        self.assertEqual(len(listar_facturas(self.conexion)), 1)

    def test_exporta_csv(self):
        guardar_factura(self.conexion, self.datos)
        salida = io.StringIO()
        exportar_csv(listar_facturas(self.conexion), salida)
        lineas = salida.getvalue().strip().splitlines()
        self.assertEqual(len(lineas), 2)
        self.assertIn("0001-00001234", lineas[1])


class TestRespuestaIA(unittest.TestCase):
    def test_normaliza_respuesta_del_modelo(self):
        crudo = {
            "tipo": "a", "numero": "0001-00001234", "fecha": "15/09/2026",
            "proveedor": "Demo", "cuit_proveedor": "20123456786", "cuit_cliente": None,
            "neto": "100.000,00", "iva": 21000, "total": 121000.0,
        }
        d = normalizar_respuesta(crudo)
        self.assertEqual(d["tipo"], "A")
        self.assertEqual(d["fecha"], "2026-09-15")
        self.assertEqual(d["cuit_proveedor"], "20-12345678-6")
        self.assertEqual(d["neto"], 100000.0)
        self.assertIsNone(d["cuit_cliente"])


if __name__ == "__main__":
    unittest.main()
