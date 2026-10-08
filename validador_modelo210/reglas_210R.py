"""Rendimientos: resultado, agrupación y transición normativa 2026."""
from datetime import date

from .comun import ORDEN, fecha, incidencia, plazo, regla, sumar_meses, vacio


def aplicar(datos, renta, ejercicio, agrupada, resultado, fechas, periodo):
    if ejercicio is None or resultado is None or agrupada is None:
        return None, [], [], []
    errores, advertencias = [], []
    if renta == "35" and not agrupada:
        errores.append(incidencia("RENTA35_REQUIERE_AGRUPACION", "tipoRenta", "La clave 35 corresponde a alquileres agrupados de varios pagadores."))
    if resultado == "cuota_cero":
        return plazo(date(ejercicio + 1, 1, 1), date(ejercicio + 1, 1, 20)), errores, [], [regla("R_CUOTA_CERO", "Plazo para resultado de cuota cero.")]
    if resultado == "devolver":
        fin = None
        if not vacio(datos.get("fechaFinPeriodoRetencion")):
            try:
                fin_retencion = fecha(datos["fechaFinPeriodoRetencion"])
                if fin_retencion.year > 9995:
                    raise ValueError("Fecha de retención fuera del rango calculable.")
                fin = sumar_meses(fin_retencion, 48)
                if fin < date(ejercicio + 1, 2, 1):
                    raise ValueError("El fin calculado es anterior al inicio de devolución.")
            except ValueError as exc:
                errores.append(incidencia("RETENCION_INVALIDA", "fechaFinPeriodoRetencion", str(exc)))
                fin = None
        else:
            advertencias.append(incidencia("FIN_DEVOLUCION_DESCONOCIDO", "fechaFinPeriodoRetencion", "Falta el fin del período de declaración e ingreso de la retención para calcular los cuatro años."))
        return plazo(date(ejercicio + 1, 2, 1), fin), errores, advertencias, [regla("R_DEVOLUCION", "Inicio y prescripción de solicitud de devolución.")]
    alquiler = renta in {"01", "35"}
    nuevo = alquiler and (ejercicio >= 2027 or (ejercicio == 2026 and
                        (agrupada or (fechas and min(fechas) >= date(2026, 10, 1)))))
    if nuevo:
        return plazo(date(ejercicio + 1, 4, 1), date(ejercicio + 1, 4, 20), date(ejercicio + 1, 4, 15)), errores, [], [regla("R_ALQUILER_PLAZO_2026", "Nuevo plazo de alquileres; transición separada desde cuarto trimestre 2026.", ORDEN)]
    if alquiler and agrupada and ejercicio >= 2024:
        return plazo(date(ejercicio + 1, 1, 1), date(ejercicio + 1, 1, 20), date(ejercicio + 1, 1, 15)), errores, [], [regla("R_ALQUILER_2024", "Agrupación anual de alquileres: régimen de plazo anterior a 2026.")]
    trimestre = int(periodo[0]) if periodo and periodo.endswith("T") else ((fechas[0].month - 1) // 3 + 1 if fechas else None)
    if trimestre is None:
        return None, errores, [], []
    anio, mes = (ejercicio + 1, 1) if trimestre == 4 else (ejercicio, trimestre * 3 + 1)
    return plazo(date(anio, mes, 1), date(anio, mes, 20), date(anio, mes, 15)), errores, [], [regla("R_PLAZO_TRIMESTRAL", "Plazo ordinario posterior al trimestre de devengo.")]
