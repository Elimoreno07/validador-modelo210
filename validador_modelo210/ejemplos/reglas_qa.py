"""Extensión de ejemplo: control interno QA, no una norma fiscal nueva."""
from validador_modelo210 import ReglaAEAT, ResultadoRegla
from validador_modelo210.comun import incidencia, vacio


def comprobar_identificador(contexto):
    if vacio(contexto.datos.get("idCaso")):
        return ResultadoRegla(advertencias=[incidencia("QA_SIN_ID_CASO", "idCaso",
            "Indica el identificador del caso de prueba para enlazar la revisión con QA.")])
    return ResultadoRegla()


def registrar(registro):
    registro.registrar(ReglaAEAT("QA_IDENTIFICADOR", "Trazabilidad del caso de QA.",
                                comprobar_identificador, fuente="Política interna QA de ejemplo"))
