"""Registro de reglas con vigencia, prioridad y plugins explícitos."""
from copy import deepcopy
from dataclasses import dataclass, field, replace
from datetime import date
from importlib import import_module, metadata
from types import MappingProxyType
from typing import Callable, Mapping

from .comun import AEAT, incidencia, regla


@dataclass(frozen=True)
class ContextoValidacion:
    datos: Mapping
    modelo: str | None
    renta: str | None
    ejercicio: int | None
    agrupada: bool | None
    resultado: str | None
    fechas: tuple[date, ...]
    fecha_presentacion: date | None
    periodo: str | None = None


@dataclass
class ResultadoRegla:
    errores: list[dict] = field(default_factory=list)
    advertencias: list[dict] = field(default_factory=list)
    reglas: list[dict] = field(default_factory=list)
    periodo: str | None = None
    plazo: dict | None = None


@dataclass(frozen=True)
class ReglaAEAT:
    codigo: str
    descripcion: str
    evaluar: Callable[[ContextoValidacion], ResultadoRegla]
    modelos: frozenset[str] = frozenset({"210I", "210H", "210R"})
    version: str = "1"
    fuente: str = AEAT
    ejercicio_desde: int | None = None
    ejercicio_hasta: int | None = None
    presentacion_desde: date | None = None
    presentacion_hasta: date | None = None
    prioridad: int = 100
    reemplazar_periodo: bool = False
    reemplazar_plazo: bool = False

    def aplica(self, contexto):
        if contexto.modelo not in self.modelos:
            return False
        for valor, minimo, maximo in (
            (contexto.ejercicio, self.ejercicio_desde, self.ejercicio_hasta),
            (contexto.fecha_presentacion, self.presentacion_desde, self.presentacion_hasta),
        ):
            if (minimo is not None or maximo is not None) and valor is None:
                return False
            if minimo is not None and valor < minimo:
                return False
            if maximo is not None and valor > maximo:
                return False
        return True


class RegistroReglas:
    def __init__(self):
        self._reglas = {}

    def registrar(self, nueva):
        if not isinstance(nueva, ReglaAEAT) or not nueva.codigo or not callable(nueva.evaluar):
            raise ValueError("Definición de regla inválida.")
        if nueva.codigo in self._reglas:
            raise ValueError(f"Regla duplicada: {nueva.codigo}.")
        for inicio, fin in ((nueva.ejercicio_desde, nueva.ejercicio_hasta),
                            (nueva.presentacion_desde, nueva.presentacion_hasta)):
            if inicio is not None and fin is not None and inicio > fin:
                raise ValueError("Vigencia de regla invertida.")
        self._reglas[nueva.codigo] = nueva

    def evaluar(self, contexto):
        acumulado = ResultadoRegla()
        ejecutadas = []
        contexto = replace(contexto, datos=MappingProxyType(deepcopy(dict(contexto.datos))))
        for actual in sorted(self._reglas.values(), key=lambda r: (r.prioridad, r.codigo)):
            try:
                if not actual.aplica(contexto):
                    continue
                salida = actual.evaluar(contexto)
                if not isinstance(salida, ResultadoRegla):
                    raise ValueError("La regla no devuelve ResultadoRegla.")
                for grupo in (salida.errores, salida.advertencias):
                    if not isinstance(grupo, list) or any(not isinstance(x, dict) or
                            not all(k in x for k in ("codigo", "campo", "mensaje")) for x in grupo):
                        raise ValueError("Incidencia de regla mal formada.")
                if not isinstance(salida.reglas, list) or any(not isinstance(x, dict) or
                        not all(k in x for k in ("codigo", "descripcion", "fuente")) for x in salida.reglas):
                    raise ValueError("Trazabilidad de regla mal formada.")
                if salida.periodo is not None:
                    if salida.periodo not in {"0A", "1T", "2T", "3T", "4T"}:
                        raise ValueError("Período calculado inválido.")
                    if acumulado.periodo is not None and not actual.reemplazar_periodo:
                        raise ValueError("Conflicto de período sin reemplazo explícito.")
                if salida.plazo is not None:
                    if not isinstance(salida.plazo, dict):
                        raise ValueError("Plazo inválido.")
                    inicio = date.fromisoformat(salida.plazo["inicio"])
                    fin = salida.plazo["fin"]
                    dom = salida.plazo["finDomiciliacion"]
                    if fin and date.fromisoformat(fin) < inicio:
                        raise ValueError("Plazo invertido.")
                    if dom and (date.fromisoformat(dom) < inicio or
                                (fin and date.fromisoformat(dom) > date.fromisoformat(fin))):
                        raise ValueError("Domiciliación fuera del plazo.")
                    if acumulado.plazo is not None and not actual.reemplazar_plazo:
                        raise ValueError("Conflicto de plazo sin reemplazo explícito.")
                # Aplicación atómica: una regla inválida no deja valores parciales.
                acumulado.errores.extend(salida.errores)
                acumulado.advertencias.extend(salida.advertencias)
                acumulado.reglas.extend(salida.reglas or [regla(actual.codigo, actual.descripcion, actual.fuente)])
                if salida.periodo is not None:
                    acumulado.periodo = salida.periodo
                    contexto = replace(contexto, periodo=salida.periodo)
                if salida.plazo is not None:
                    acumulado.plazo = salida.plazo
                ejecutadas.append({"codigo": actual.codigo, "version": actual.version,
                                   "fuente": actual.fuente, "estado": "Ejecutada"})
            except Exception:
                acumulado.errores.append(incidencia("REGLA_NO_EJECUTADA", "reglas",
                    f"No se ha podido completar la comprobación {actual.codigo}. QA debe revisar la regla antes de aceptar la declaración."))
                ejecutadas.append({"codigo": actual.codigo, "version": actual.version,
                                   "fuente": actual.fuente, "estado": "Fallida"})
        return acumulado, ejecutadas


def crear_registro(*, modulos=(), descubrir_plugins=True):
    from .reglas_base import registrar
    registro = RegistroReglas()
    registrar(registro)
    if descubrir_plugins:
        for plugin in sorted(metadata.entry_points(group="validador_modelo210.reglas"), key=lambda p: p.name):
            try:
                plugin.load()(registro)
            except Exception as exc:
                raise ValueError(f"No se pudo cargar el paquete de reglas {plugin.name}.") from exc
    for ruta in modulos:
        try:
            modulo, separador, nombre = ruta.partition(":")
            if not separador or not modulo or not nombre:
                raise ValueError("Use modulo:registrar.")
            getattr(import_module(modulo), nombre)(registro)
        except Exception as exc:
            raise ValueError(f"No se pudo cargar el módulo de reglas {ruta}.") from exc
    return registro
