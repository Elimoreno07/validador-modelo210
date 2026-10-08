import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from validador_modelo210 import validar, validar_fichero
from validador_modelo210.entrada import cargar_fichero, leer_json, leer_registro_fijo
from validador_modelo210.informe import generar_informe
from validador_modelo210.tests.test_modalidades import registro

ROOT = Path(__file__).resolve().parents[2]


class TestEntrada(unittest.TestCase):
    def test_json_texto(self):
        self.assertEqual(validar(json.dumps(registro()))["estado"], "Correcto")

    def test_json_duplicado_y_nan(self):
        for texto in ('{"ejercicio":2025,"ejercicio":2026}', '{"resultado":NaN}'):
            with self.subTest(texto=texto), self.assertRaises(ValueError):
                leer_json(texto)

    def test_json_incorrecto_sin_excepcion_api(self):
        self.assertEqual(validar("no es json")["errores"][0]["codigo"], "REGISTRO_INVALIDO")

    def test_layout_sintetico_versionado(self):
        layout = {"version": "TEST_NO_AEAT", "longitudRegistro": 14,
                  "campos": {"tipoRenta": {"inicio": 1, "longitud": 2},
                             "ejercicio": {"inicio": 3, "longitud": 4},
                             "fechaDevengo": {"inicio": 7, "longitud": 8}}}
        self.assertEqual(leer_registro_fijo("04202615112026", layout),
                         {"tipoRenta": "04", "ejercicio": "2026", "fechaDevengo": "15112026"})

    def test_layout_no_asume_longitud_o_posiciones(self):
        for layout in ({}, {"version": "test", "longitudRegistro": 4, "campos": {
                "a": {"inicio": 1, "longitud": 3}, "b": {"inicio": 2, "longitud": 3}}},
                {"version": "test", "longitudRegistro": 4, "campos": {
                "a": {"inicio": 1, "longitud": 999999999}}}):
            with self.subTest(layout=layout), self.assertRaises(ValueError):
                leer_registro_fijo("2026", layout)

    def test_layout_devengo_cero_agrupado(self):
        layout = {"version": "test", "longitudRegistro": 8,
                  "campos": {"fechaDevengo": {"inicio": 1, "longitud": 8, "valoresVacios": ["00000000"]}}}
        self.assertIsNone(leer_registro_fijo("00000000", layout)["fechaDevengo"])

    def test_archivos_json_jsonl_csv(self):
        with tempfile.TemporaryDirectory() as directorio:
            for extension in ("json", "jsonl", "csv"):
                with self.subTest(extension=extension):
                    ruta = Path(directorio) / f"entrada.{extension}"
                    if extension == "json":
                        texto = json.dumps(registro())
                    elif extension == "jsonl":
                        texto = json.dumps(registro()) + "\n" + json.dumps(registro("99"))
                    else:
                        texto = "tipoRenta;ejercicio;fechaDevengo;modalidadPresentacion;periodo;resultado\n04;2026;2026-11-15;individual;0A;ingresar\n"
                    ruta.write_text(texto, encoding="utf-8")
                    salida = validar_fichero(ruta)
                    salida = salida if isinstance(salida, list) else [salida]
                    self.assertEqual(salida[0]["estado"], "Correcto")

    def test_ascii_sin_layout_rechazado(self):
        with tempfile.TemporaryDirectory() as directorio:
            ruta = Path(directorio) / "entrada.210"
            ruta.write_text("04202615112026", encoding="utf-8")
            with self.assertRaises(ValueError):
                cargar_fichero(ruta)

    def test_csv_domiciliacion_booleana(self):
        with tempfile.TemporaryDirectory() as directorio:
            ruta = Path(directorio) / "entrada.csv"
            ruta.write_text("tipoRenta;ejercicio;fechaDevengo;modalidadPresentacion;periodo;resultado;domiciliacion\n04;2026;2026-11-15;individual;0A;ingresar;true\n", encoding="utf-8")
            self.assertEqual(validar_fichero(ruta)[0]["estado"], "Correcto")

    def test_informe_incluye_todos_los_resultados(self):
        texto = generar_informe([validar(registro()), validar(registro("99"))])
        for campo in ("Modelo detectado: 210R", "Período calculado: 0A", "Reglas aplicadas:",
                      "TIPO_RENTA_DESCONOCIDO", "Advertencias:"):
            self.assertIn(campo, texto)


class TestCLI(unittest.TestCase):
    def ejecutar(self, entrada, *args):
        return subprocess.run([sys.executable, "-m", "validador_modelo210", str(entrada), *map(str, args)],
                              cwd=ROOT, capture_output=True, text=True, encoding="utf-8")

    def test_salida_y_reporte(self):
        with tempfile.TemporaryDirectory() as directorio:
            ruta = Path(directorio) / "entrada.json"
            salida, informe = Path(directorio) / "salida.json", Path(directorio) / "informe.txt"
            ruta.write_text(json.dumps(registro()), encoding="utf-8")
            proceso = self.ejecutar(ruta, "--salida", salida, "--informe", informe)
            self.assertEqual(proceso.returncode, 0, proceso.stderr)
            self.assertEqual(json.loads(salida.read_text(encoding="utf-8"))["estado"], "Correcto")
            self.assertIn("Modelo detectado: 210R", informe.read_text(encoding="utf-8"))

    def test_exit_validacion_y_error_entrada(self):
        with tempfile.TemporaryDirectory() as directorio:
            ruta = Path(directorio) / "entrada.json"
            ruta.write_text(json.dumps(registro(periodo="4T")), encoding="utf-8")
            proceso = self.ejecutar(ruta)
            self.assertEqual(proceso.returncode, 1)
            self.assertEqual(json.loads(proceso.stdout)["errores"][0]["codigo"], "PERIODO_INCOMPATIBLE")
            ruta.write_text("{", encoding="utf-8")
            proceso = self.ejecutar(ruta)
            self.assertEqual(proceso.returncode, 2)
            self.assertEqual(json.loads(proceso.stderr)["estado"], "ErrorEntrada")


if __name__ == "__main__":
    unittest.main()
