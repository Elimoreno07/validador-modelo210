"""Adaptadores de las reglas incluidas al contrato extensible del motor."""
from . import reglas_210H, reglas_210I, reglas_210R
from .comun import incidencia
from .detector_periodo import detectar_periodo
from .motor_reglas import ReglaAEAT, ResultadoRegla


def _periodo(c):
    periodo, errores, reglas = detectar_periodo(c.modelo, c.renta, c.ejercicio,
                                              c.agrupada, c.resultado, c.fechas)
    return ResultadoRegla(periodo=periodo, errores=errores, reglas=reglas)


def _imputacion(c):
    plazo, errores, avisos, reglas = reglas_210I.aplicar(c.datos, c.ejercicio, c.fechas, c.fecha_presentacion)
    return ResultadoRegla(errores, avisos, reglas, plazo=plazo)


def _transmision(c):
    try:
        plazo, errores, avisos, reglas = reglas_210H.aplicar(c.datos, c.fechas, c.renta)
    except (ValueError, OverflowError):
        return ResultadoRegla(errores=[incidencia("PLAZO_FUERA_RANGO", "fechaDevengo",
            "La fecha no permite calcular el plazo dentro del rango de fechas soportado.")])
    return ResultadoRegla(errores, avisos, reglas, plazo=plazo)


def _rendimientos(c):
    plazo, errores, avisos, reglas = reglas_210R.aplicar(c.datos, c.renta, c.ejercicio,
                                                     c.agrupada, c.resultado, c.fechas, c.periodo)
    return ResultadoRegla(errores, avisos, reglas, plazo=plazo)


def registrar(registro):
    registro.registrar(ReglaAEAT("AEAT_PERIODO", "Cálculo del período fiscal.", _periodo, prioridad=-100))
    for modelo, funcion in (("210I", _imputacion), ("210H", _transmision), ("210R", _rendimientos)):
        registro.registrar(ReglaAEAT("AEAT_" + modelo, "Reglas de " + modelo,
                                    funcion, modelos=frozenset({modelo}), version="2026-10-08", prioridad=0))
