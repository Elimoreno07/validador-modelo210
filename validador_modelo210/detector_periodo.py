"""Período fiscal AEAT: independiente del trimestre de cobro y del plazo."""
from .comun import incidencia, regla


def detectar_periodo(modelo, renta, ejercicio, agrupada, resultado, fechas):
    if agrupada is None or modelo not in {"210I", "210H", "210R"}:
        return None, [], []
    if not agrupada:
        return "0A", [], [regla("PERIODO_INDIVIDUAL", "Declaración separada: período 0A.")]
    if modelo in {"210I", "210H"}:
        return None, [incidencia("AGRUPACION_INCOMPATIBLE", "modalidadPresentacion",
                                 f"{modelo} no permite agrupación de rentas.")], []
    if resultado is None or ejercicio is None:
        return None, [], []
    if resultado in {"devolver", "cuota_cero"} or (renta in {"01", "35"} and ejercicio >= 2024):
        return "0A", [], [regla("AGRUPACION_ANUAL", "Agrupación anual según renta, resultado y ejercicio.")]
    trimestres = {(f.month - 1) // 3 + 1 for f in fechas}
    if not trimestres:
        return None, [incidencia("DEVENGOS_REQUERIDOS", "devengos",
                                 "Informe fechas para calcular el trimestre de la agrupación.")], []
    if len(trimestres) != 1:
        return None, [incidencia("TRIMESTRES_MEZCLADOS", "devengos",
                                 "La agrupación trimestral contiene devengos de distintos trimestres.")], []
    return f"{next(iter(trimestres))}T", [], [regla("AGRUPACION_TRIMESTRAL", "Agrupación a ingresar del mismo trimestre.")]
