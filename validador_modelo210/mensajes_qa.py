"""Orientaciones de revisión separadas de los códigos estables de validación."""
ACCIONES = {
    "OBLIGATORIO": "Completa el campo indicado en los datos de la liquidación y repite la validación.",
    "PERIODO_INCOMPATIBLE": "Revisa si las rentas se declaran individualmente o agrupadas y compara el período con el esperado.",
    "RENTA_MODELO_INCOMPATIBLE": "Comprueba la clave de renta seleccionada y el apartado I, H o R que aparece en el impreso.",
    "EJERCICIO_DEVENGO": "Corrige el ejercicio o las fechas: el ejercicio es el año del devengo, no el de presentación.",
    "FECHA_INVALIDA": "Comprueba la fecha completa y que el día exista en ese mes y año.",
    "AGRUPACION_INCOMPATIBLE": "Desmarca la agrupación para imputaciones o transmisiones inmobiliarias.",
    "PRESENTACION_ANTICIPADA": "Compara la fecha prevista con el inicio del plazo calculado.",
    "PLAZO_INCOMPATIBLE": "Compara el plazo calculado por Sage con el nominal esperado y revisa la campaña y el tipo de renta.",
    "FUERA_DE_PLAZO": "Revisa si es una presentación extemporánea y, si se domicilia, si esa forma de pago sigue disponible.",
    "CALENDARIO_NOMINAL": "Contrasta las fechas con el calendario AEAT de la campaña antes de dar por válido el plazo.",
    "FORMATO_SIN_FECHA": "Indica la fecha de presentación prevista para comprobar la versión del formulario.",
    "REGLA_NO_EJECUTADA": "Comunica la regla fallida al responsable técnico; la declaración queda bloqueada para QA.",
}


def completar_informe(informe):
    for grupo in ("errores", "advertencias"):
        for aviso in informe[grupo]:
            aviso.setdefault("accionQA", ACCIONES.get(aviso["codigo"],
                "Revisa el campo indicado y la regla aplicada; corrige los datos o documenta el resultado de la revisión."))
    informe["estadoQA"] = ("Bloqueado" if informe["errores"] else
                           "Revisar" if informe["advertencias"] else "Preparado")
    return informe
