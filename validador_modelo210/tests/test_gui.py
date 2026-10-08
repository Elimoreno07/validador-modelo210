import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from validador_modelo210.entrada_gui import cargar_subida
from validador_modelo210.servicio_gui import ejecutar_validacion, incidencias, leer_historial, cargar_validacion
from validador_modelo210.validador import validar_conjunto

RAIZ = Path(__file__).resolve().parents[2]


class PruebasEscritorio(unittest.TestCase):
    def test_ejemplos_y_equivalencia_motor(self):
        with tempfile.TemporaryDirectory() as tmp:
            for nombre, modelo, correcto in [('210I_correcto', '210I', True), ('210I_error', '210I', False),
                                             ('210H_correcto', '210H', True), ('210R_correcto', '210R', True)]:
                contenido = (RAIZ / 'ejemplos' / (nombre + '.json')).read_bytes()
                entrega = ejecutar_validacion(contenido, nombre + '.json', destino=tmp)
                esperado = validar_conjunto([json.loads(contenido)])
                self.assertEqual(entrega['resultados'], esperado)
                self.assertEqual(esperado[0]['tipoModelo'], modelo)
                self.assertEqual(not esperado[0]['errores'], correcto)
                self.assertTrue(entrega['archivos']['informe.pdf'].startswith(b'%PDF-'))
                self.assertEqual(cargar_validacion(entrega['meta']['id'], tmp), entrega)
            self.assertEqual(len(leer_historial(tmp)), 4)

    def test_json_txt_jsonl_xml(self):
        datos = {'tipoRenta': '04', 'ejercicio': '2026', 'periodo': '0A'}
        for nombre in ('a.json', 'a.txt'):
            self.assertEqual(cargar_subida(json.dumps(datos).encode(), nombre), [datos])
        self.assertEqual(len(cargar_subida((json.dumps(datos)+'\n'+json.dumps(datos)).encode(), 'a.txt')), 2)
        xml = b'<declaraciones><declaracion><tipoRenta>04</tipoRenta><ejercicio>2026</ejercicio><periodo>0A</periodo></declaracion></declaraciones>'
        self.assertEqual(cargar_subida(xml, 'a.xml'), [datos])
        self.assertEqual(cargar_subida(xml, 'a.txt'), [datos])

    def test_xml_listas_namespace_bool(self):
        datos = cargar_subida(b'<declaracion xmlns="urn:qa"><domiciliacion>false</domiciliacion><fechasDevengo><fecha>2026-11-15</fecha><fecha>2026-12-01</fecha></fechasDevengo></declaracion>', 'a.xml')[0]
        self.assertIs(datos['domiciliacion'], False)
        self.assertEqual(len(datos['fechasDevengo']), 2)

    def test_entradas_invalidas_no_guardan_historial(self):
        with tempfile.TemporaryDirectory() as tmp:
            for contenido, nombre in [(b'', 'a.json'), (b'[]', 'a.json'), (b'[1]', 'a.json'),
                                      (b'<otra/>', 'a.xml'), (b'{"a":1,"a":2}', 'a.json'),
                                      (b'<declaracion><a>1</a><a>2</a></declaracion>', 'a.xml'),
                                      (b'<!DOCTYPE a><declaracion/>', 'a.xml'), (b'1234', 'a.210')]:
                with self.assertRaises(ValueError):
                    ejecutar_validacion(contenido, nombre, destino=tmp)
            self.assertEqual(leer_historial(tmp), [])

    def test_ascii_layout_y_encoding(self):
        layout = {'version':'qa-demo', 'longitudRegistro':6, 'campos':{'tipoRenta':{'inicio':1,'longitud':2},'ejercicio':{'inicio':3,'longitud':4}}}
        self.assertEqual(cargar_subida(b'022026\r\n282026', 'a.210', layout=layout)[0], {'tipoRenta':'02','ejercicio':'2026'})
        with self.assertRaises(ValueError):
            cargar_subida(b'022026', 'a.210')
        self.assertEqual(cargar_subida('{"idCaso":"España"}'.encode('cp1252'), 'a.txt', encoding='cp1252')[0]['idCaso'], 'España')

    def test_historial_concurrencia_y_seguridad_rutas(self):
        with tempfile.TemporaryDirectory() as tmp:
            contenido = (RAIZ/'ejemplos/210I_correcto.json').read_bytes()
            a = ejecutar_validacion(contenido, '../../a.json', destino=tmp)
            b = ejecutar_validacion(contenido, '../../a.json', destino=tmp)
            self.assertNotEqual(a['meta']['id'], b['meta']['id'])
            self.assertEqual(a['meta']['fichero'], 'a.json')
            with self.assertRaises(ValueError):
                cargar_validacion('../fuera', tmp)
            (Path(tmp)/'roto').mkdir()
            (Path(tmp)/'roto/validacion.json').write_text('{')
            self.assertEqual(len(leer_historial(tmp)), 2)

    def test_fallo_pdf_no_deja_resultado_parcial(self):
        with tempfile.TemporaryDirectory() as tmp, patch('validador_modelo210.servicio_gui.generar_pdf', side_effect=OSError('fallo')):
            with self.assertRaises(OSError):
                ejecutar_validacion((RAIZ/'ejemplos/210I_correcto.json').read_bytes(), 'a.json', destino=tmp)
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_tabla_qa(self):
        r = validar_conjunto([json.loads((RAIZ/'ejemplos/210I_error.json').read_bytes())])
        fila = incidencias(r)[0]
        self.assertEqual(set(fila), {'Caso', 'Código', 'Tipo', 'Campo', 'Descripción', 'Solución'})
        self.assertEqual(fila['Tipo'], 'Error')

    def test_pdf_texto_y_paginacion(self):
        from validador_modelo210.informe_pdf import generar_pdf
        from pypdf import PdfReader
        import io
        r = validar_conjunto([json.loads((RAIZ/'ejemplos/210I_error.json').read_bytes())])
        pdf = PdfReader(io.BytesIO(generar_pdf(r * 3)))
        self.assertGreaterEqual(len(pdf.pages), 3)
        texto = ''.join(p.extract_text() for p in pdf.pages)
        self.assertIn('210I', texto)
        self.assertIn(r[0]['errores'][0]['codigo'], texto)


class PruebasStreamlit(unittest.TestCase):
    def test_pantalla_e_historial(self):
        from streamlit.testing.v1 import AppTest
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'MODELO210_INFORMES':tmp}):
            app = AppTest.from_file(str(RAIZ/'app.py')).run(timeout=30)
            self.assertFalse(app.exception)
            self.assertTrue(app.button[0].disabled)
            entrega = ejecutar_validacion((RAIZ/'ejemplos/210I_error.json').read_bytes(), 'a.json', destino=tmp)
            app.session_state['actual'] = entrega
            app.run(timeout=30)
            self.assertFalse(app.exception)
            self.assertIn('Validación incorrecta', app.error[0].value)
            self.assertEqual(len(app.get('download_button')), 3)
            self.assertGreaterEqual(len(app.dataframe), 3)
