"""Transmisión de inmueble: plazo de tres meses tras transcurrir uno."""
from datetime import timedelta

from .comun import ORDEN, incidencia, plazo, regla, sumar_meses


def aplicar(datos, fechas, renta):
    errores = []
    if datos.get("domiciliacion") is True and renta == "28":
        errores.append(incidencia("DOMICILIACION_NO_PERMITIDA", "domiciliacion", "El tipo de renta 28 está excluido de domiciliación."))
    if not fechas:
        return None, errores, [], []
    un_mes = sumar_meses(fechas[0], 1)
    limites = plazo(un_mes + timedelta(days=1), sumar_meses(un_mes, 3))
    return limites, errores, [], [regla("H_PLAZO_TRANSMISION", "Tres meses de presentación tras transcurrir un mes desde transmisión.", ORDEN)]
