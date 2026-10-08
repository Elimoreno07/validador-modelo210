# Validación previa para QA de Impresos Sage 200

Herramienta Python para revisar declaraciones del **Modelo 210** antes de las
pruebas de Impresos Sage 200. Detecta **210I**, **210H** y **210R**, valida modalidad,
período, ejercicio y plazo de presentación, y genera informes **HTML, CSV y JSON**.
Las incidencias incluyen una explicación funcional y una acción de revisión para QA.

Python 3.11 o superior. Sin dependencias externas en tiempo de ejecución.

## Uso

Desde la raíz del repositorio:

```shell
python -m validador_modelo210 entrada.json --salida resultado.json --informe informe.txt
```

Para generar todos los informes de QA:

```shell
python -m validador_modelo210 entrada.json --directorio-informes output/qa
```

Se crean `resultados.json`, `informe.html` e `informe.csv`. El HTML muestra resumen,
datos de cada caso, errores, advertencias y reglas. El CSV incluye una fila por
declaración, separador `;` y UTF-8 con BOM para Excel.

El resultado QA distingue **Bloqueado** (errores), **Revisar** (advertencias) y
**Preparado** (sin incidencias). Con `--estricto-qa`, las advertencias también
producen código de salida 1. No se valida el diseño visual del impreso ni se
ejecuta una presentación tributaria.

Ejemplo incluido:

```shell
python -m validador_modelo210 validador_modelo210/ejemplos/declaraciones.json
```

El ejemplo contiene tres declaraciones correctas y una incompatible. El comando
termina con código 1 porque detecta ese error. Códigos de salida: **0** sin
errores, **1** errores de validación, **2** error de entrada.

## API

```python
from validador_modelo210 import validar

resultado = validar({
    "tipoRenta": "04",
    "ejercicio": 2026,
    "periodo": "4T",
    "fechaDevengo": "2026-11-15",
    "modalidadPresentacion": "agrupada",
    "resultado": "ingresar",
})
print(resultado)
```

También están disponibles `validar_conjunto` y `validar_fichero`.

## Entradas y períodos

- JSON, JSONL y CSV.
- ASCII o `.210` mediante un descriptor de posiciones explícito y versionado.
- Una declaración individual utiliza `0A`; el trimestre depende de una
  agrupación compatible. El mes de presentación es un dato diferente.
- El código de renta determina el modelo. Las rentas correspondientes a `210G`
  se identifican y rechazan como fuera del alcance I/H/R.

El contrato completo de campos, alias, formatos y configuración ASCII se
documenta en [README.txt](validador_modelo210/README.txt).

## Arquitectura

```text
validador_modelo210/
  detector_modelo.py
  detector_periodo.py
  reglas_210I.py
  reglas_210H.py
  reglas_210R.py
  validador.py
  entrada.py
  informe.py
  motor_reglas.py
  reglas_base.py
  mensajes_qa.py
  tests/
```

## Pruebas

```shell
python -m unittest discover -s validador_modelo210/tests -v
```

Se incluyen 78 pruebas y un flujo de GitHub Actions para Linux y Windows.

## Extender reglas sin cambiar el núcleo

Las reglas se registran con identificador, versión, fuente, modelo, vigencia y
prioridad. Pueden añadir controles o sustituir el período y el plazo de forma
explícita. Los fallos de una regla generan un error bloqueante y trazable.

Ejemplo de módulo de revisión QA incluido:

```shell
python -m validador_modelo210 entrada.json --directorio-informes output/qa --reglas validador_modelo210.ejemplos.reglas_qa:registrar
```

También se descubren paquetes instalados mediante el grupo de entry points
`validador_modelo210.reglas`. Solo deben cargarse módulos Python de confianza.

- [Documentación técnica y contrato de extensiones](docs/arquitectura.md).
- [Guía funcional para QA](docs/guia_qa.md).
- [Ejemplo de informe HTML](docs/ejemplo/informe.html).
- [Ejemplo de informe CSV](docs/ejemplo/informe.csv).

## Alcance normativo

Reglas revisadas a **08/10/2026**, incluidas las transiciones de la Orden
HAC/623/2026. Los ejercicios posteriores generan una advertencia para revisar
posibles cambios normativos.

- [Instrucciones y catálogo AEAT](https://sede.agenciatributaria.gob.es/Sede/todas-gestiones/impuestos-tasas/impuesto-sobre-renta-no-residentes/modelo-210-irnr______a-no-residentes-permanente_/instrucciones.html).
- [Orden HAC/623/2026](https://www.boe.es/eli/es/o/2026/06/12/hac623).

La herramienta comprueba modalidad, período y plazos nominales; no calcula el
impuesto ni valida íntegramente la declaración. Los plazos no incorporan ajustes
por días inhábiles. El estado `Correcto` se refiere a los controles implementados
y no garantiza aceptación por la AEAT. No se incluye un layout oficial ASCII
2027 sin verificar sus posiciones.
