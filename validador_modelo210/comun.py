"""Normalización estricta y utilidades compartidas, sin dependencias externas."""
import calendar
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

AEAT = "https://sede.agenciatributaria.gob.es/Sede/todas-gestiones/impuestos-tasas/impuesto-sobre-renta-no-residentes/modelo-210-irnr______a-no-residentes-permanente_/instrucciones.html"
ORDEN = "https://www.boe.es/eli/es/o/2026/06/12/hac623"
VERSION = "2026-10-08"


def incidencia(codigo, campo, mensaje):
    return {"codigo": codigo, "campo": campo, "mensaje": mensaje}


def regla(codigo, descripcion, fuente=AEAT):
    return {"codigo": codigo, "descripcion": descripcion, "fuente": fuente}


def vacio(valor):
    return valor is None or (isinstance(valor, str) and not valor.strip())


def entero(valor):
    if isinstance(valor, bool) or not re.fullmatch(r"\d+", str(valor).strip()):
        raise ValueError("Debe ser un entero.")
    return int(valor)


def codigo_renta(valor):
    n = entero(valor)
    if not 1 <= n <= 99:
        raise ValueError("Tipo de renta fuera de rango.")
    return f"{n:02}"


def fecha(valor):
    if isinstance(valor, datetime):
        raise ValueError("Use una fecha sin hora.")
    if isinstance(valor, date):
        return valor
    if not isinstance(valor, str):
        raise ValueError("Fecha incorrecta.")
    for patron, formato in ((r"\d{4}-\d{2}-\d{2}", "%Y-%m-%d"),
                            (r"\d{2}/\d{2}/\d{4}", "%d/%m/%Y"),
                            (r"\d{8}", "%d%m%Y")):
        if re.fullmatch(patron, valor.strip()):
            try:
                return datetime.strptime(valor.strip(), formato).date()
            except ValueError:
                break
    raise ValueError("Use YYYY-MM-DD, DD/MM/YYYY o DDMMAAAA, con fecha válida.")


def decimal(valor):
    if isinstance(valor, bool):
        raise ValueError("Importe incorrecto.")
    try:
        numero = Decimal(str(valor).strip().replace(",", "."))
    except InvalidOperation as exc:
        raise ValueError("Importe incorrecto.") from exc
    if not numero.is_finite():
        raise ValueError("Importe no finito.")
    return numero


def sumar_meses(dia, meses):
    total = dia.year * 12 + dia.month - 1 + meses
    anio, mes0 = divmod(total, 12)
    return date(anio, mes0 + 1, min(dia.day, calendar.monthrange(anio, mes0 + 1)[1]))


def plazo(inicio, fin, domiciliacion=None):
    return {"inicio": inicio.isoformat(), "fin": fin.isoformat() if fin else None,
            "finDomiciliacion": domiciliacion.isoformat() if domiciliacion else None,
            "calendario": "Fechas normativas nominales; no ajustadas por días inhábiles."}


ALIASES = {
    "ejercicio": ("Ejercicio",), "fechaDevengo": ("FechaDevengo",),
    "tipoRenta": ("claveRenta", "INRTipoRenta"), "tipoModelo": ("INRTipoMod",),
    "periodo": ("periodoInformado",), "agrupacion": ("INRAgrupar",),
    "resultado": ("Resultado",), "numeroDias": ("RENNumeroDias",),
    "cuotaParticipacion": ("INRPorPropiedadDec",),
    "claveReferenciaCatastral": ("INRClaveRefCatastral",),
    "situacionInmueble": ("ClaveSituacion",),
}


def normalizar(datos):
    salida = dict(datos)
    errores = []
    for destino, alternativas in ALIASES.items():
        presentes = [k for k in (destino, *alternativas) if k in datos]
        if presentes:
            valor = datos[presentes[0]]
            if any(datos[k] != valor for k in presentes[1:]):
                errores.append(incidencia("ALIAS_CONFLICTIVO", destino,
                                          "Se han recibido valores contradictorios del mismo campo."))
            salida[destino] = valor
    return salida, errores
