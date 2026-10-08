"""Detección por catálogo explícito, nunca por defecto 210R."""
from .comun import codigo_renta, incidencia, regla, vacio

RENTAS_I = {"02"}
RENTAS_H = {"28", "33", "34"}
RENTAS_G = {"24", "25", "26", "31", "36", "38"}
RENTAS_R = {f"{n:02}" for n in range(1, 23)} - RENTAS_I
RENTAS_R |= {"27", "29", "30", "32", "35", "37"}


def detectar_modelo(datos):
    errores, reglas = [], []
    if vacio(datos.get("tipoRenta")):
        return None, None, [incidencia("OBLIGATORIO", "tipoRenta", "Informe el tipo de renta.")], []
    try:
        renta = codigo_renta(datos["tipoRenta"])
    except ValueError as exc:
        return None, None, [incidencia("TIPO_RENTA_INVALIDO", "tipoRenta", str(exc))], []
    modelo = next((m for m, catalogo in (("210I", RENTAS_I), ("210H", RENTAS_H),
                                       ("210R", RENTAS_R), ("210G", RENTAS_G))
                   if renta in catalogo), None)
    reglas.append(regla("MODELO_POR_RENTA", "Clasificación mediante catálogo de tipos de renta."))
    if modelo is None:
        errores.append(incidencia("TIPO_RENTA_DESCONOCIDO", "tipoRenta", "Código fuera del catálogo soportado."))
    elif modelo == "210G":
        errores.append(incidencia("MODALIDAD_NO_SOPORTADA", "tipoRenta", "La renta corresponde a 210G, fuera del alcance I/H/R."))
    declarado = datos.get("tipoModelo")
    if not vacio(declarado):
        declarado = str(declarado).strip().upper()
        if declarado in {"I", "H", "R", "G"}:
            declarado = "210" + declarado
        if declarado not in {"210I", "210H", "210R", "210G"}:
            errores.append(incidencia("MODELO_INVALIDO", "tipoModelo", "Modalidad desconocida."))
        elif modelo and declarado != modelo:
            errores.append(incidencia("RENTA_MODELO_INCOMPATIBLE", "tipoModelo", f"El tipo de renta {renta} corresponde a {modelo}."))
    claves = datos.get("clavesRenta")
    if claves is not None:
        try:
            if not isinstance(claves, list) or not claves:
                raise ValueError("Informe una lista no vacía de claves de renta.")
            if any(codigo_renta(c) != renta for c in claves):
                raise ValueError("Todas las rentas de una declaración deben tener la misma clave.")
        except ValueError as exc:
            errores.append(incidencia("CLAVES_INCOMPATIBLES", "clavesRenta", str(exc)))
    return modelo, renta, errores, reglas
