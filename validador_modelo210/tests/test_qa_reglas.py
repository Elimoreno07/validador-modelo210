import csv
import io
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from validador_modelo210 import ReglaAEAT, RegistroReglas, ResultadoRegla, crear_registro, validar
from validador_modelo210.comun import incidencia, plazo
from validador_modelo210.informe import generar_csv, generar_html
from validador_modelo210.tests.test_modalidades import codigos, registro


class TestMotorReglas(unittest.TestCase):
    def motor(self, **campos):
        motor = crear_registro(descubrir_plugins=False)
        motor.registrar(ReglaAEAT("TEST_EXTENSION", "Regla de prueba", **campos))
        return motor

    def test_añadir_regla_sin_modificar_nucleo(self):
        motor = self.motor(evaluar=lambda c: ResultadoRegla(errores=[incidencia("QA_TEST", "idCaso", "Falta evidencia QA.")]))
        r = validar(registro(), registro_reglas=motor)
        self.assertIn("QA_TEST", codigos(r))
        self.assertEqual(r["estadoQA"], "Bloqueado")
        self.assertIn("TEST_EXTENSION", {x["codigo"] for x in r["reglasEjecutadas"]})

    def test_vigencias_anteriores_posteriores_y_bordes(self):
        motor = self.motor(evaluar=lambda c: ResultadoRegla(advertencias=[incidencia("QA_TEST", "idCaso", "Revisión.")]),
                           ejercicio_desde=2026, ejercicio_hasta=2026,
                           presentacion_desde=date(2027, 1, 1), presentacion_hasta=date(2027, 12, 31))
        for dia, esperada in ((None, False), ("2026-12-31", False), ("2027-01-01", True),
                              ("2027-12-31", True), ("2028-01-01", False)):
            with self.subTest(dia=dia):
                r = validar(registro(fechaPresentacion=dia), registro_reglas=motor)
                self.assertEqual("QA_TEST" in codigos(r, "advertencias"), esperada)

    def test_modelo_no_aplicable(self):
        motor = self.motor(evaluar=lambda c: ResultadoRegla(errores=[incidencia("QA_TEST", "idCaso", "Error.")]),
                           modelos=frozenset({"210H"}))
        self.assertNotIn("QA_TEST", codigos(validar(registro(), registro_reglas=motor)))

    def test_duplicados_y_vigencia_invertida(self):
        motor = RegistroReglas()
        regla = ReglaAEAT("X", "Prueba", lambda c: ResultadoRegla())
        motor.registrar(regla)
        with self.assertRaises(ValueError):
            motor.registrar(regla)
        with self.assertRaises(ValueError):
            motor.registrar(ReglaAEAT("Y", "Prueba", lambda c: ResultadoRegla(), ejercicio_desde=2027, ejercicio_hasta=2026))

    def test_fallo_extension_no_oculta_errores_ni_rompe_lote(self):
        def fallar(c):
            raise RuntimeError("Detalle interno que no debe aparecer en el informe.")
        r = validar(registro(), registro_reglas=self.motor(evaluar=fallar))
        self.assertIn("REGLA_NO_EJECUTADA", codigos(r))
        self.assertEqual(r["estadoQA"], "Bloqueado")
        self.assertNotIn("Detalle interno", json.dumps(r))

    def test_resultado_mal_formado_bloquea(self):
        for salida in (None, ResultadoRegla(errores=[{"codigo": "X"}]),
                       ResultadoRegla(periodo="5T"), ResultadoRegla(plazo={"inicio": "fecha"})):
            with self.subTest(salida=salida):
                r = validar(registro(), registro_reglas=self.motor(evaluar=lambda c: salida))
                self.assertIn("REGLA_NO_EJECUTADA", codigos(r))

    def test_reemplazo_periodo_y_plazo_explicito(self):
        motor = self.motor(evaluar=lambda c: ResultadoRegla(periodo="2T", plazo=plazo(date(2027, 2, 1), date(2027, 2, 20))),
                           reemplazar_periodo=True, reemplazar_plazo=True)
        r = validar(registro(periodo="2T"), registro_reglas=motor)
        self.assertEqual(r["estado"], "Correcto")
        self.assertEqual(r["periodo"], "2T")
        self.assertEqual(r["plazoPresentacion"]["inicio"], "2027-02-01")

    def test_conflicto_no_sobrescribe_base(self):
        motor = self.motor(evaluar=lambda c: ResultadoRegla(periodo="2T"))
        r = validar(registro(), registro_reglas=motor)
        self.assertIn("REGLA_NO_EJECUTADA", codigos(r))
        self.assertEqual(r["periodo"], "0A")

    def test_entrada_original_no_se_modifica(self):
        def tocar(c):
            c.datos["clavesRenta"].append("05")
            return ResultadoRegla()
        datos = registro(clavesRenta=["04"])
        validar(datos, registro_reglas=self.motor(evaluar=tocar))
        self.assertEqual(datos["clavesRenta"], ["04"])

    def test_modulo_extension_ejemplo(self):
        motor = crear_registro(modulos=["validador_modelo210.ejemplos.reglas_qa:registrar"], descubrir_plugins=False)
        self.assertIn("QA_SIN_ID_CASO", codigos(validar(registro(), registro_reglas=motor), "advertencias"))

    def test_entrypoint_sin_cambio_nucleo(self):
        def registrar(motor):
            motor.registrar(ReglaAEAT("PAQUETE", "Prueba", lambda c: ResultadoRegla()))
        plugin = SimpleNamespace(name="prueba", load=lambda: registrar)
        with patch("validador_modelo210.motor_reglas.metadata.entry_points", return_value=[plugin]):
            r = validar(registro())
        self.assertIn("PAQUETE", {x["codigo"] for x in r["reglasEjecutadas"]})

    def test_plugin_no_cargable(self):
        with self.assertRaises(ValueError):
            crear_registro(modulos=["modulo_inexistente:registrar"], descubrir_plugins=False)


class TestInformesQA(unittest.TestCase):
    def test_html_con_resumen_y_accion_funcional(self):
        html = generar_html([validar(registro()), validar(registro(periodo="4T"))])
        self.assertIn("Impresos Sage 200", html)
        self.assertIn("Bloqueados: <strong>1</strong>", html)
        self.assertIn("Qué revisar:", html)
        self.assertIn("PERIODO_INCOMPATIBLE", html)
        self.assertEqual(html.count("<section>"), 2)

    def test_html_escapa_datos_y_fuentes(self):
        r = validar(registro(idCaso='<script>alert(1)</script>'))
        r["reglasAplicadas"].append({"codigo": "TEST", "descripcion": '<img src=x>', "fuente": "javascript:alert(1)"})
        r["reglasAplicadas"].append({"codigo": "URL_INVALIDA", "descripcion": 'Fuente no disponible', "fuente": "https://["})
        html = generar_html(r)
        self.assertNotIn("<script>", html)
        self.assertNotIn('<img src=x>', html)
        self.assertNotIn('href="javascript:', html)
        self.assertIn("&lt;script&gt;", html)

    def test_csv_unicode_columnas_y_filas(self):
        csv_texto = generar_csv([validar(registro()), validar(registro(periodo="4T"))])
        self.assertTrue(csv_texto.startswith("\ufeff"))
        filas = list(csv.DictReader(io.StringIO(csv_texto.lstrip("\ufeff")), delimiter=";"))
        self.assertEqual(len(filas), 2)
        self.assertEqual(filas[1]["estado_qa"], "Bloqueado")
        self.assertIn("PERIODO_INCOMPATIBLE", filas[1]["errores"])
        self.assertEqual(json.loads(filas[1]["reglas_aplicadas"])[0]["codigo"], "MODELO_POR_RENTA")

    def test_csv_no_ejecuta_formulas_y_conserva_comillas(self):
        for identificador in ('=HYPERLINK("url")', '  +SUM(1)', '@prueba', '-prueba', '\t=1'):
            with self.subTest(identificador=identificador):
                texto = generar_csv(validar(registro(idCaso=identificador)))
                fila = next(csv.DictReader(io.StringIO(texto.lstrip("\ufeff")), delimiter=";"))
                self.assertEqual(fila["id_caso"], "'" + identificador)

    def test_plazo_informado_comparado(self):
        r = validar(registro(plazoInformado={"inicio": "2027-01-01", "fin": "2027-01-20"}))
        self.assertNotIn("PLAZO_INCOMPATIBLE", codigos(r))
        r = validar(registro(plazoInformado={"inicio": "2026-04-01", "fin": "2027-01-20"}))
        self.assertIn("PLAZO_INCOMPATIBLE", codigos(r))

    def test_estados_qa_y_plazo(self):
        self.assertEqual(validar(registro())["estadoQA"], "Revisar")
        self.assertEqual(validar(registro(fechaPresentacion="2027-01-15"))["estadoPlazo"], "En plazo nominal")
        self.assertEqual(validar(registro(fechaPresentacion="2027-02-01"))["estadoPlazo"], "Fuera de plazo nominal")
        self.assertEqual(validar(registro(resultado="devolver", fechaPresentacion="2027-03-01"))["estadoPlazo"], "No comprobado")


class TestCLIQa(unittest.TestCase):
    def ejecutar(self, entrada, *args):
        return subprocess.run([sys.executable, "-m", "validador_modelo210", str(entrada), *map(str, args)],
                              cwd=Path(__file__).resolve().parents[2], capture_output=True,
                              text=True, encoding="utf-8")

    def test_directorio_informes_y_extension(self):
        with tempfile.TemporaryDirectory() as carpeta:
            entrada, destino = Path(carpeta) / "datos.json", Path(carpeta) / "informes"
            entrada.write_text(json.dumps(registro()), encoding="utf-8")
            proceso = self.ejecutar(entrada, "--directorio-informes", destino, "--reglas",
                                   "validador_modelo210.ejemplos.reglas_qa:registrar")
            self.assertEqual(proceso.returncode, 0, proceso.stderr)
            self.assertTrue((destino / "informe.html").exists())
            self.assertTrue((destino / "informe.csv").exists())
            self.assertIn("QA_SIN_ID_CASO", (destino / "resultados.json").read_text(encoding="utf-8"))

    def test_estricto_qa_bloquea_advertencias(self):
        with tempfile.TemporaryDirectory() as carpeta:
            entrada = Path(carpeta) / "datos.json"
            entrada.write_text(json.dumps(registro()), encoding="utf-8")
            self.assertEqual(self.ejecutar(entrada, "--estricto-qa").returncode, 1)

    def test_informe_no_sobrescribe_entrada(self):
        with tempfile.TemporaryDirectory() as carpeta:
            entrada = Path(carpeta) / "datos.json"
            texto = json.dumps(registro())
            entrada.write_text(texto, encoding="utf-8")
            self.assertEqual(self.ejecutar(entrada, "--informe-html", entrada).returncode, 2)
            self.assertEqual(entrada.read_text(encoding="utf-8"), texto)
