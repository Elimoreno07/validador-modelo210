"""Orquestación: cada declaración produce un informe sin modificar la entrada."""
from collections.abc import Mapping
from datetime import date

from .comun import VERSION, decimal, entero, fecha, incidencia, normalizar, vacio
from .detector_modelo import detectar_modelo
from .mensajes_qa import completar_informe
from .motor_reglas import ContextoValidacion, crear_registro


def _agrupacion(datos, errores):
    modalidad = datos.get("modalidadPresentacion")
    agrupacion = datos.get("agrupacion")
    if vacio(modalidad) and agrupacion is None:
        errores.append(incidencia("OBLIGATORIO", "modalidadPresentacion", "Informe individual/agrupada o agrupacion."))
        return None
    valores = []
    if not vacio(modalidad):
        valor = str(modalidad).strip().lower()
        if valor not in {"individual", "agrupada"}:
            errores.append(incidencia("MODALIDAD_INVALIDA", "modalidadPresentacion", "Use individual o agrupada; el canal telemático/papel es un campo separado."))
        else:
            valores.append(valor == "agrupada")
    if agrupacion is not None:
        if isinstance(agrupacion, bool):
            valores.append(agrupacion)
        elif str(agrupacion).strip().lower() in {"1", "-1", "true", "x"}:
            valores.append(True)
        elif str(agrupacion).strip().lower() in {"0", "false", ""}:
            valores.append(False)
        else:
            errores.append(incidencia("AGRUPACION_INVALIDA", "agrupacion", "Use booleano, 0/1/-1 o X."))
    if len(set(valores)) > 1:
        errores.append(incidencia("AGRUPACION_CONFLICTIVA", "modalidadPresentacion", "Modalidad y agrupacion contradictorias."))
        return None
    return valores[0] if valores else None


def _resultado(valor):
    texto = str(valor).strip().lower()
    if texto in {"ingresar", "devolver", "cuota_cero"}:
        return texto
    importe = decimal(valor)
    return "ingresar" if importe > 0 else "devolver" if importe < 0 else "cuota_cero"


def validar(registro, *, fecha_referencia=None, registro_reglas=None):
    """Acepta un mapping; resultado fiscal separado del período informado.

    fecha_referencia es opcional: no se compara implícitamente con el reloj.
    El estado Correcto expresa los controles implementados, no aceptación AEAT.
    """
    informe = {"tipoModelo": None, "ejercicio": None, "periodo": None,
               "periodoInformado": None, "fechaDevengo": None, "estado": "Incorrecto",
               "errores": [], "advertencias": [], "reglasAplicadas": [],
               "plazoPresentacion": None, "versionNormativa": VERSION,
               "idCaso": None, "reglasEjecutadas": [], "estadoPlazo": "No comprobado",
               "fechaPresentacion": None, "modalidadPresentacion": None, "tipoRenta": None}
    errores, advertencias, reglas = informe["errores"], informe["advertencias"], informe["reglasAplicadas"]
    if isinstance(registro, str):
        from .entrada import leer_json
        try:
            registro = leer_json(registro)
        except ValueError as exc:
            errores.append(incidencia("REGISTRO_INVALIDO", "registro", str(exc)))
            return completar_informe(informe)
    if not isinstance(registro, Mapping):
        errores.append(incidencia("REGISTRO_INVALIDO", "registro", "Se espera un objeto de datos."))
        return completar_informe(informe)
    datos, conflictos = normalizar(registro)
    informe["idCaso"] = str(datos["idCaso"]) if datos.get("idCaso") is not None else None
    errores.extend(conflictos)
    modelo, renta, problemas, aplicadas = detectar_modelo(datos)
    informe["tipoModelo"] = modelo
    informe["tipoRenta"] = renta
    errores.extend(problemas)
    reglas.extend(aplicadas)
    ejercicio = None
    try:
        if vacio(datos.get("ejercicio")):
            raise ValueError("Informe el ejercicio.")
        ejercicio = entero(datos["ejercicio"])
        # Modelo actual desde 2011; H puede extender el plazo al año siguiente.
        if not 2011 <= ejercicio <= 9998:
            raise ValueError("Ejercicio fuera del rango soportado 2011–9998.")
        informe["ejercicio"] = ejercicio
    except ValueError as exc:
        ejercicio = None
        errores.append(incidencia("EJERCICIO_INVALIDO", "ejercicio", str(exc)))
    agrupada = _agrupacion(datos, errores)
    informe["modalidadPresentacion"] = ("agrupada" if agrupada else "individual") if agrupada is not None else None
    resultado = None
    if not vacio(datos.get("resultado")):
        try:
            resultado = _resultado(datos["resultado"])
        except ValueError as exc:
            errores.append(incidencia("RESULTADO_INVALIDO", "resultado", str(exc)))
    elif modelo == "210R":
        errores.append(incidencia("OBLIGATORIO", "resultado", "Informe ingresar, devolver, cuota_cero o el importe."))
    fechas = []
    devengo = None
    if not vacio(datos.get("fechaDevengo")):
        try:
            devengo = fecha(datos["fechaDevengo"])
            fechas.append(devengo)
            informe["fechaDevengo"] = devengo.isoformat()
        except ValueError as exc:
            errores.append(incidencia("FECHA_INVALIDA", "fechaDevengo", str(exc)))
    elif agrupada is False:
        errores.append(incidencia("OBLIGATORIO", "fechaDevengo", "Informe fecha de devengo para declaración individual."))
    lista = datos.get("devengos")
    if lista is not None:
        if not isinstance(lista, list) or not lista:
            errores.append(incidencia("DEVENGOS_INVALIDOS", "devengos", "Se espera una lista no vacía de fechas."))
        else:
            for i, valor in enumerate(lista):
                try:
                    fechas.append(fecha(valor))
                except ValueError as exc:
                    errores.append(incidencia("FECHA_INVALIDA", f"devengos[{i}]", str(exc)))
    if agrupada is False and lista is not None:
        errores.append(incidencia("DEVENGOS_EN_INDIVIDUAL", "devengos", "Una declaración individual utiliza una única fechaDevengo."))
    if agrupada:
        advertencias.append(incidencia("AGRUPACION_PARCIAL", "agrupacion", "Se valida período y clave; faltan comprobaciones de pagador, bien, contribuyente, gravamen y no compensación."))
        if devengo:
            advertencias.append(incidencia("FECHA_AUXILIAR_AGRUPACION", "fechaDevengo", "Fecha usada para análisis; la casilla fecha de devengo no se cumplimenta en una agrupación."))
        if not fechas:
            advertencias.append(incidencia("DEVENGOS_NO_CONTRASTADOS", "devengos", "Sin detalle de fechas no se comprueba la pertenencia de todos los devengos al ejercicio."))
    if ejercicio is not None and any(f.year != ejercicio for f in fechas):
        errores.append(incidencia("EJERCICIO_DEVENGO", "ejercicio", "Las fechas de devengo deben pertenecer al ejercicio."))
    referencia = None
    if fecha_referencia is not None:
        try:
            referencia = fecha(fecha_referencia)
            if any(f > referencia for f in fechas):
                errores.append(incidencia("DEVENGO_FUTURO", "fechaDevengo", "Devengo posterior a la fecha de referencia."))
        except ValueError as exc:
            errores.append(incidencia("REFERENCIA_INVALIDA", "fechaReferencia", str(exc)))
    fecha_presentacion = None
    if not vacio(datos.get("fechaPresentacion")):
        try:
            fecha_presentacion = fecha(datos["fechaPresentacion"])
            informe["fechaPresentacion"] = fecha_presentacion.isoformat()
            if fechas and fecha_presentacion < max(fechas):
                errores.append(incidencia("PRESENTACION_ANTES_DEVENGO", "fechaPresentacion", "Presentación anterior al devengo."))
        except ValueError as exc:
            errores.append(incidencia("FECHA_INVALIDA", "fechaPresentacion", str(exc)))
    if "domiciliacion" in datos and not isinstance(datos["domiciliacion"], bool):
        errores.append(incidencia("DOMICILIACION_INVALIDA", "domiciliacion", "Use true/false."))
    if datos.get("domiciliacion") is True and resultado in {"devolver", "cuota_cero"}:
        errores.append(incidencia("DOMICILIACION_SIN_INGRESO", "domiciliacion", "La domiciliación requiere resultado a ingresar."))
    canal = datos.get("canalPresentacion")
    if not vacio(canal) and str(canal).lower() not in {"telematica", "papel"}:
        errores.append(incidencia("CANAL_INVALIDO", "canalPresentacion", "Use telematica o papel."))
    motor = registro_reglas if registro_reglas is not None else crear_registro()
    contexto = ContextoValidacion(datos, modelo, renta, ejercicio, agrupada, resultado,
                                 tuple(fechas), fecha_presentacion)
    salida_reglas, ejecutadas = motor.evaluar(contexto)
    periodo, limites = salida_reglas.periodo, salida_reglas.plazo
    if modelo in {"210I", "210H", "210R"} and periodo is None and not errores and not salida_reglas.errores:
        errores.append(incidencia("REGLAS_INCOMPLETAS", "periodo", "No se ha podido determinar el período con las reglas disponibles."))
    informe["periodo"] = periodo
    informe["reglasEjecutadas"] = ejecutadas
    errores.extend(salida_reglas.errores)
    advertencias.extend(salida_reglas.advertencias)
    reglas.extend(salida_reglas.reglas)
    informado = datos.get("periodo")
    if vacio(informado):
        errores.append(incidencia("OBLIGATORIO", "periodo", "Informe el período que desea contrastar."))
    else:
        informado = str(informado).strip().upper()
        informe["periodoInformado"] = informado
        if informado not in {"0A", "1T", "2T", "3T", "4T"}:
            errores.append(incidencia("PERIODO_INVALIDO", "periodo", "Período fiscal válido: 0A o 1T–4T."))
        elif periodo and informado != periodo:
            errores.append(incidencia("PERIODO_INCOMPATIBLE", "periodo", f"Período esperado: {periodo}; informado: {informado}."))
    informe["plazoPresentacion"] = limites
    plazo_informado = datos.get("plazoInformado")
    if plazo_informado is not None:
        if not isinstance(plazo_informado, Mapping):
            errores.append(incidencia("PLAZO_INFORMADO_INVALIDO", "plazoInformado", "Informe inicio y fin como un objeto de fechas."))
        elif limites is None:
            errores.append(incidencia("PLAZO_NO_CONTRASTABLE", "plazoInformado", "No se ha podido calcular el plazo para compararlo."))
        else:
            for campo in ("inicio", "fin"):
                try:
                    valor = fecha(plazo_informado.get(campo)).isoformat()
                    if limites[campo] is None:
                        advertencias.append(incidencia("PLAZO_NO_CONTRASTABLE", "plazoInformado." + campo, "Faltan datos para contrastar esta fecha del plazo."))
                    elif valor != limites[campo]:
                        errores.append(incidencia("PLAZO_INCOMPATIBLE", "plazoInformado." + campo,
                            f"La fecha informada es {valor}; la fecha nominal esperada es {limites[campo]}."))
                except ValueError:
                    errores.append(incidencia("FECHA_INVALIDA", "plazoInformado." + campo, "Informe una fecha válida para el plazo."))
    if limites:
        advertencias.append(incidencia("CALENDARIO_NOMINAL", "plazoPresentacion", "Los plazos no incorporan prórrogas ni ajustes del calendario oficial por días inhábiles."))
        if fecha_presentacion:
            informe["estadoPlazo"] = "En plazo nominal"
            if fecha_presentacion < date.fromisoformat(limites["inicio"]):
                informe["estadoPlazo"] = "Anterior al plazo"
                errores.append(incidencia("PRESENTACION_ANTICIPADA", "fechaPresentacion", "Presentación anterior al inicio del plazo."))
            fin = limites["finDomiciliacion"] if datos.get("domiciliacion") is True else limites["fin"]
            if fin is None and fecha_presentacion >= date.fromisoformat(limites["inicio"]):
                informe["estadoPlazo"] = "No comprobado"
            if datos.get("domiciliacion") is True and fin is None:
                advertencias.append(incidencia("DOMICILIACION_NO_CALCULADA", "domiciliacion", "No se calcula el plazo de domiciliación para este supuesto."))
            if fin and fecha_presentacion > date.fromisoformat(fin):
                informe["estadoPlazo"] = "Fuera de plazo nominal"
                advertencias.append(incidencia("FUERA_DE_PLAZO", "fechaPresentacion", "Fecha posterior al plazo nominal; revisar presentación extemporánea o forma de pago."))
    if ejercicio is not None and ejercicio > 2026:
        advertencias.append(incidencia("NORMATIVA_FUTURA", "ejercicio", "Reglas conocidas a 08/10/2026; revisar modificaciones posteriores."))
    informe["estado"] = "Incorrecto" if errores else "Correcto"
    return completar_informe(informe)


def validar_conjunto(registros, **opciones):
    if not isinstance(registros, (list, tuple)) or not registros:
        raise ValueError("Se espera una lista no vacía de declaraciones independientes.")
    if "registro_reglas" not in opciones:
        opciones["registro_reglas"] = crear_registro()
    return [validar(r, **opciones) for r in registros]


def validar_fichero(ruta, *, layout=None, encoding="utf-8-sig", **opciones):
    from .entrada import cargar_fichero
    datos = cargar_fichero(ruta, layout=layout, encoding=encoding)
    return (validar_conjunto if isinstance(datos, list) else validar)(datos, **opciones)
