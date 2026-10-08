"""Imputación inmobiliaria: devengo anual, plazo y campos desde 2027."""
from datetime import date

from .comun import ORDEN, decimal, entero, incidencia, plazo, regla, vacio


def aplicar(datos, ejercicio, fechas, fecha_presentacion):
    errores, advertencias = [], []
    reglas = [regla("I_DEVENGO_ANUAL", "Devengo de imputación el 31 de diciembre.")]
    if any(f.month != 12 or f.day != 31 for f in fechas):
        errores.append(incidencia("DEVENGO_IMPUTACION", "fechaDevengo", "210I debe devengarse el 31 de diciembre."))
    limites = None
    if ejercicio is not None:
        mes = 4 if ejercicio >= 2026 else 1
        limites = plazo(date(ejercicio + 1, mes, 1), date(ejercicio + 1, 12, 31),
                        date(ejercicio + 1, 12, 23))
        reglas.append(regla("I_PLAZO_2026" if ejercicio >= 2026 else "I_PLAZO_HISTORICO",
                            "Plazo de imputación determinado por el ejercicio de devengo.", ORDEN))
    if fecha_presentacion and fecha_presentacion >= date(2027, 1, 1):
        reglas.append(regla("I_CAMPOS_2027", "Nuevos campos exigibles por fecha de presentación.", ORDEN))
        for campo in ("numeroDias", "cuotaParticipacion", "claveReferenciaCatastral"):
            if vacio(datos.get(campo)):
                errores.append(incidencia("OBLIGATORIO", campo, "Campo necesario para el formato desde 2027."))
    elif fecha_presentacion is None:
        advertencias.append(incidencia("FORMATO_SIN_FECHA", "fechaPresentacion", "No se puede determinar la obligatoriedad de los campos introducidos en 2027."))
    if not vacio(datos.get("numeroDias")):
        try:
            dias = entero(datos["numeroDias"])
            maximo = (date(ejercicio + 1, 1, 1) - date(ejercicio, 1, 1)).days if ejercicio else 366
            if not 1 <= dias <= maximo:
                raise ValueError("Días fuera del rango del ejercicio.")
        except ValueError as exc:
            errores.append(incidencia("DIAS_INVALIDOS", "numeroDias", str(exc)))
    if not vacio(datos.get("cuotaParticipacion")):
        try:
            if not 0 <= decimal(datos["cuotaParticipacion"]) <= 100:
                raise ValueError("La cuota debe estar entre 0 y 100.")
        except ValueError as exc:
            errores.append(incidencia("CUOTA_INVALIDA", "cuotaParticipacion", str(exc)))
    if not vacio(datos.get("claveReferenciaCatastral")):
        try:
            clave = entero(datos["claveReferenciaCatastral"])
            if clave not in {1, 2}:
                raise ValueError("La clave debe ser 1 o 2.")
            if not vacio(datos.get("situacionInmueble")):
                situacion = entero(datos["situacionInmueble"])
                if situacion not in {1, 2, 3, 4}:
                    raise ValueError("Situación fuera del catálogo territorial soportado.")
                if clave != (1 if situacion == 1 else 2):
                    raise ValueError("Clave incompatible con el mapeo territorial Sage solicitado.")
                reglas.append(regla("SAGE_CLAVE_CATASTRAL", "Mapeo territorial configurado según requisito Sage.", "Requisito funcional del usuario"))
            else:
                advertencias.append(incidencia("MAPEO_NO_COMPROBADO", "situacionInmueble", "Falta situación para contrastar el mapeo territorial Sage."))
        except ValueError as exc:
            errores.append(incidencia("CLAVE_CATASTRAL_INVALIDA", "claveReferenciaCatastral", str(exc)))
    return limites, errores, advertencias, reglas
