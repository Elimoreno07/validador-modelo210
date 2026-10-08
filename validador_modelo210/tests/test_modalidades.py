import unittest

from validador_modelo210 import validar, validar_conjunto


def registro(renta="04", **cambios):
    datos = {"tipoRenta": renta, "ejercicio": 2026, "fechaDevengo": "2026-11-15",
             "modalidadPresentacion": "individual", "periodo": "0A", "resultado": "ingresar"}
    datos.update(cambios)
    return datos


def codigos(resultado, campo="errores"):
    return {e["codigo"] for e in resultado[campo]}


class Test210I(unittest.TestCase):
    def datos(self, **cambios):
        return registro("02", fechaDevengo="2026-12-31", **cambios)

    def test_modelo_y_periodo_anual(self):
        r = validar(self.datos())
        self.assertEqual((r["tipoModelo"], r["periodo"], r["estado"]), ("210I", "0A", "Correcto"))
        self.assertEqual(r["plazoPresentacion"]["inicio"], "2027-04-01")
        self.assertEqual(r["plazoPresentacion"]["finDomiciliacion"], "2027-12-23")

    def test_historico(self):
        r = validar(registro("02", ejercicio=2025, fechaDevengo="2025-12-31"))
        self.assertEqual(r["plazoPresentacion"]["inicio"], "2026-01-01")

    def test_devengo_no_anual(self):
        self.assertIn("DEVENGO_IMPUTACION", codigos(validar(registro("02"))))

    def test_no_agrupacion(self):
        r = validar(self.datos(modalidadPresentacion="agrupada"))
        self.assertIn("AGRUPACION_INCOMPATIBLE", codigos(r))

    def test_nuevos_campos_por_presentacion_no_ejercicio(self):
        r = validar(registro("02", ejercicio=2025, fechaDevengo="2025-12-31", fechaPresentacion="2027-05-01"))
        self.assertEqual({x["campo"] for x in r["errores"] if x["codigo"] == "OBLIGATORIO"},
                         {"numeroDias", "cuotaParticipacion", "claveReferenciaCatastral"})

    def test_2027_completo(self):
        r = validar(self.datos(fechaPresentacion="2027-04-01", numeroDias=365,
                              cuotaParticipacion="50,25", claveReferenciaCatastral=1,
                              situacionInmueble=1))
        self.assertEqual(r["estado"], "Correcto")

    def test_limites_dias_cuota_y_clave(self):
        for cambio, codigo in [({"numeroDias": 0}, "DIAS_INVALIDOS"),
                               ({"numeroDias": 366}, "DIAS_INVALIDOS"),
                               ({"numeroDias": 1.5}, "DIAS_INVALIDOS"),
                               ({"cuotaParticipacion": 100.01}, "CUOTA_INVALIDA"),
                               ({"cuotaParticipacion": -1}, "CUOTA_INVALIDA"),
                               ({"cuotaParticipacion": "NaN"}, "CUOTA_INVALIDA"),
                               ({"claveReferenciaCatastral": 3}, "CLAVE_CATASTRAL_INVALIDA"),
                               ({"claveReferenciaCatastral": 2, "situacionInmueble": 1}, "CLAVE_CATASTRAL_INVALIDA")]:
            with self.subTest(cambio=cambio):
                self.assertIn(codigo, codigos(validar(self.datos(**cambio))))

    def test_bisiesto_y_cuota_cero(self):
        r = validar(registro("02", ejercicio=2028, fechaDevengo="2028-12-31",
                             numeroDias=366, cuotaParticipacion=0))
        self.assertEqual(r["estado"], "Correcto")


class Test210H(unittest.TestCase):
    def test_codigos_transmision(self):
        for renta in ("28", "33", "34"):
            with self.subTest(renta=renta):
                r = validar(registro(renta))
                self.assertEqual((r["tipoModelo"], r["estado"]), ("210H", "Correcto"))
                self.assertEqual(r["plazoPresentacion"]["inicio"], "2026-12-16")
                self.assertEqual(r["plazoPresentacion"]["fin"], "2027-03-15")

    def test_periodo_no_trimestral(self):
        self.assertIn("PERIODO_INCOMPATIBLE", codigos(validar(registro("28", periodo="4T"))))

    def test_no_agrupacion(self):
        self.assertIn("AGRUPACION_INCOMPATIBLE", codigos(validar(registro("28", modalidadPresentacion="agrupada"))))

    def test_fin_mes(self):
        r = validar(registro("28", fechaDevengo="2026-01-31"))
        self.assertEqual(r["plazoPresentacion"]["inicio"], "2026-03-01")
        self.assertEqual(r["plazoPresentacion"]["fin"], "2026-05-28")

    def test_domiciliacion_excluida(self):
        self.assertIn("DOMICILIACION_NO_PERMITIDA", codigos(validar(registro("28", domiciliacion=True))))

    def test_fecha_maxima_no_rompe(self):
        self.assertIn("PLAZO_FUERA_RANGO", codigos(validar(registro("28", fechaDevengo="9999-12-31"))))


class Test210R(unittest.TestCase):
    def test_ejemplo_4T_requiere_agrupacion(self):
        r = validar(registro(modalidadPresentacion="agrupada", periodo="4T"))
        self.assertEqual((r["tipoModelo"], r["periodo"], r["estado"]), ("210R", "4T", "Correcto"))

    def test_individual_0A_no_trimestre(self):
        r = validar(registro(periodo="4T"))
        self.assertEqual(r["periodo"], "0A")
        self.assertIn("PERIODO_INCOMPATIBLE", codigos(r))

    def test_cuatro_trimestres_y_fronteras(self):
        for fecha, periodo in [("2026-03-31", "1T"), ("2026-04-01", "2T"),
                               ("2026-06-30", "2T"), ("2026-07-01", "3T"),
                               ("2026-09-30", "3T"), ("2026-10-01", "4T")]:
            with self.subTest(fecha=fecha):
                r = validar(registro(fechaDevengo=fecha, modalidadPresentacion="agrupada", periodo=periodo))
                self.assertEqual(r["estado"], "Correcto")

    def test_agrupacion_sin_fecha_casilla(self):
        r = validar(registro(fechaDevengo=None, devengos=["2026-10-01", "2026-12-31"],
                             modalidadPresentacion="agrupada", periodo="4T"))
        self.assertEqual(r["estado"], "Correcto")

    def test_trimestres_mezclados(self):
        r = validar(registro(fechaDevengo=None, devengos=["2026-09-30", "2026-10-01"],
                             modalidadPresentacion="agrupada", periodo="4T"))
        self.assertIn("TRIMESTRES_MEZCLADOS", codigos(r))

    def test_agrupacion_trimestral_sin_fechas(self):
        r = validar(registro(fechaDevengo=None, modalidadPresentacion="agrupada", periodo="4T"))
        self.assertIn("DEVENGOS_REQUERIDOS", codigos(r))

    def test_alquiler_anual_desde2024(self):
        for ejercicio in (2024, 2025, 2026):
            with self.subTest(ejercicio=ejercicio):
                r = validar(registro("01", ejercicio=ejercicio, fechaDevengo=None,
                                     modalidadPresentacion="agrupada", periodo="0A"))
                self.assertEqual(r["periodo"], "0A")
                self.assertEqual(r["plazoPresentacion"]["inicio"], f"{ejercicio+1}-{'04' if ejercicio == 2026 else '01'}-01")

    def test_alquiler_2023_trimestral(self):
        r = validar(registro("01", ejercicio=2023, fechaDevengo="2023-11-15",
                             modalidadPresentacion="agrupada", periodo="4T"))
        self.assertEqual(r["periodo"], "4T")

    def test_transicion_alquiler_separado2026(self):
        for dia, inicio in (("2026-09-30", "2026-10-01"), ("2026-10-01", "2027-04-01")):
            with self.subTest(dia=dia):
                r = validar(registro("01", fechaDevengo=dia))
                self.assertEqual(r["plazoPresentacion"]["inicio"], inicio)
                self.assertEqual(r["periodo"], "0A")

    def test_clave35_necesita_agrupacion(self):
        self.assertIn("RENTA35_REQUIERE_AGRUPACION", codigos(validar(registro("35"))))

    def test_devolver_anual(self):
        r = validar(registro(modalidadPresentacion="agrupada", resultado="devolver", periodo="0A"))
        self.assertEqual(r["periodo"], "0A")
        self.assertIsNone(r["plazoPresentacion"]["fin"])
        self.assertIn("FIN_DEVOLUCION_DESCONOCIDO", codigos(r, "advertencias"))

    def test_fin_devolucion_con_retencion(self):
        r = validar(registro(resultado=-50, fechaFinPeriodoRetencion="2027-01-20"))
        self.assertEqual(r["plazoPresentacion"]["fin"], "2031-01-20")

    def test_cuota_cero(self):
        r = validar(registro(resultado=0, modalidadPresentacion="agrupada", periodo="0A"))
        self.assertEqual(r["plazoPresentacion"]["inicio"], "2027-01-01")

    def test_sin_resultado_no_adivina(self):
        self.assertIn("OBLIGATORIO", codigos(validar(registro(resultado=None))))


class TestTransversales(unittest.TestCase):
    def test_modelo_incompatible(self):
        self.assertIn("RENTA_MODELO_INCOMPATIBLE", codigos(validar(registro(tipoModelo="210I"))))

    def test_G_fuera_de_alcance(self):
        r = validar(registro("24"))
        self.assertEqual(r["tipoModelo"], "210G")
        self.assertIn("MODALIDAD_NO_SOPORTADA", codigos(r))

    def test_codigo_desconocido(self):
        self.assertIn("TIPO_RENTA_DESCONOCIDO", codigos(validar(registro("99"))))

    def test_ejercicio_mal(self):
        for valor in (True, 2026.5, "2026.0", 2010, 9999, None):
            with self.subTest(valor=valor):
                self.assertIn("EJERCICIO_INVALIDO", codigos(validar(registro(ejercicio=valor))))

    def test_ejercicio_fecha_incompatible(self):
        self.assertIn("EJERCICIO_DEVENGO", codigos(validar(registro(ejercicio=2025))))

    def test_fechas_invalidas(self):
        for valor in ("2026-02-29", "2026-13-01", "2026-11-31", "26-11-15", [], 0):
            with self.subTest(valor=valor):
                self.assertIn("FECHA_INVALIDA", codigos(validar(registro(fechaDevengo=valor))))

    def test_fecha_espanola_y_ascii(self):
        for valor in ("15/11/2026", "15112026"):
            with self.subTest(valor=valor):
                self.assertEqual(validar(registro(fechaDevengo=valor))["fechaDevengo"], "2026-11-15")

    def test_no_confunde_canal_y_agrupacion(self):
        self.assertIn("MODALIDAD_INVALIDA", codigos(validar(registro(modalidadPresentacion="telematica"))))

    def test_campos_vacios(self):
        for campo in ("ejercicio", "periodo", "tipoRenta", "modalidadPresentacion", "fechaDevengo"):
            with self.subTest(campo=campo):
                self.assertEqual(validar(registro(**{campo: ""}))["estado"], "Incorrecto")

    def test_alias_sage(self):
        r = validar({"Ejercicio": 2026, "FechaDevengo": "2026-11-15", "INRTipoRenta": "04",
                     "INRTipoMod": "R", "INRAgrupar": -1, "periodo": "4T", "Resultado": 100})
        self.assertEqual(r["estado"], "Correcto")

    def test_alias_conflictivo(self):
        self.assertIn("ALIAS_CONFLICTIVO", codigos(validar(registro(Ejercicio=2025))))

    def test_agrupacion_conflictiva(self):
        self.assertIn("AGRUPACION_CONFLICTIVA", codigos(validar(registro(agrupacion=True))))

    def test_claves_mixtas(self):
        self.assertIn("CLAVES_INCOMPATIBLES", codigos(validar(registro(clavesRenta=["04", "05"]))))

    def test_fecha_referencia_explicita(self):
        self.assertIn("DEVENGO_FUTURO", codigos(validar(registro(), fecha_referencia="2026-10-08")))

    def test_presentacion_temprana_y_tardia(self):
        self.assertIn("PRESENTACION_ANTICIPADA", codigos(validar(registro(fechaPresentacion="2026-12-01"))))
        self.assertIn("FUERA_DE_PLAZO", codigos(validar(registro(fechaPresentacion="2027-02-01")), "advertencias"))

    def test_domiciliacion_sin_ingreso(self):
        self.assertIn("DOMICILIACION_SIN_INGRESO", codigos(validar(registro(resultado=0, domiciliacion=True))))

    def test_lote_aisla_errores(self):
        datos = [registro(), None, registro("99")]
        r = validar_conjunto(datos)
        self.assertEqual([x["estado"] for x in r], ["Correcto", "Incorrecto", "Incorrecto"])
        self.assertEqual(datos[0], registro())


if __name__ == "__main__":
    unittest.main()
