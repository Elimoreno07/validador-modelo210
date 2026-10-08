# Documentación técnica

La aplicación valida datos de declaraciones del Modelo 210 como paso previo
de QA de Impresos Sage 200. Python 3.11+, biblioteca estándar, sin conexión a Sage
ni a servicios AEAT durante la validación.

## Flujo

1. `entrada.py` lee JSON, JSONL, CSV o registro fijo con layout versionado.
2. `validador.py` normaliza alias y valida estructura, fechas, ejercicio y modalidad.
3. `detector_modelo.py` clasifica el tipo de renta mediante un catálogo explícito.
4. `motor_reglas.py` selecciona y ejecuta las reglas registradas.
5. `reglas_base.py` adapta período y reglas I/H/R al contrato del motor.
6. El validador contrasta período y plazo informados con los resultados del motor.
7. `mensajes_qa.py` incorpora acciones de revisión y calcula el estado QA.
8. `informe.py` genera HTML, CSV o texto a partir del mismo resultado JSON.

El período fiscal se mantiene separado del mes y ventana de presentación.
El catálogo de modelos permanece en su módulo específico; las ampliaciones de
controles, vigencias, cálculo de período y plazo se realizan con extensiones.

## Compatibilidad y nuevos datos

Se conservan `validar`, `validar_conjunto`, `validar_fichero` y los campos de la
salida 0.1. Se añaden:

| Campo | Uso |
|---|---|
| `idCaso` | Identificador opcional de la prueba QA, propagado al informe. |
| `tipoRenta` y `modalidadPresentacion` | Datos normalizados de la declaración. |
| `fechaPresentacion` | Fecha prevista o real recibida para contrastar el plazo. |
| `estadoPlazo` | No comprobado, en plazo nominal, anterior al plazo o fuera de plazo nominal. |
| `estadoQA` | Bloqueado, Revisar o Preparado. |
| `reglasEjecutadas` | Identificador, versión, fuente y resultado de cada módulo. |
| `accionQA` | Orientación añadida a cada error o advertencia. |

La entrada opcional `plazoInformado` acepta `inicio` y `fin` como fechas.
Se compara con el plazo nominal calculado, después de aplicar las extensiones.
Sin fecha de presentación, la comprobación de esa fecha queda como
`No comprobado`; no se deduce del reloj del equipo.

## Contrato de reglas

`ReglaAEAT` contiene `codigo`, `descripcion`, función `evaluar`, `modelos`,
`version`, `fuente`, rango de ejercicios, rango de fechas de presentación,
`prioridad`, `reemplazar_periodo` y `reemplazar_plazo`.

La función recibe un `ContextoValidacion` con datos normalizados, modelo, clave
de renta, ejercicio, agrupación, resultado, fechas de devengo, presentación y
período calculado hasta ese punto. Devuelve `ResultadoRegla` con listas de
errores, advertencias, trazabilidad y, opcionalmente, período o plazo.

```python
from validador_modelo210 import ReglaAEAT, ResultadoRegla
from validador_modelo210.comun import incidencia

def comprobar_evidencia(contexto):
    if not contexto.datos.get("idCaso"):
        return ResultadoRegla(advertencias=[
            incidencia("QA_SIN_EVIDENCIA", "idCaso", "Falta el identificador del caso QA.")
        ])
    return ResultadoRegla()

def registrar(registro):
    registro.registrar(ReglaAEAT(
        codigo="QA_EVIDENCIA",
        descripcion="Identificación del caso de prueba.",
        evaluar=comprobar_evidencia,
        fuente="Política interna QA",
        version="1",
    ))
```

Este ejemplo es una política QA, no una nueva norma tributaria. Para una regla
AEAT real, registrar su fuente verificada y vigencia, y añadir pruebas de los
límites de entrada en vigor antes de activar el paquete.

## Carga sin modificar el núcleo

Un módulo se carga explícitamente con `--reglas paquete.modulo:registrar`.
La API admite `crear_registro(modulos=[...])` y
`validar(datos, registro_reglas=registro)`. Para un paquete instalado:

```toml
[project.entry-points."validador_modelo210.reglas"]
campania = "mi_paquete.reglas:registrar"
```

Los entry points se descubren con `importlib.metadata`. Para una ejecución
determinista sin plugins instalados, usar `crear_registro(descubrir_plugins=False)`
en la API. Los módulos son código Python de confianza: no se importan nombres
de módulos a partir del fichero de declaraciones.

## Orden, vigencia y sustituciones

Las reglas se ejecutan por `(prioridad, codigo)` en orden ascendente:

- Período base: prioridad `-100`.
- Adaptadores I/H/R: prioridad `0`.
- Extensiones: prioridad `100` por defecto.

Los límites de vigencia son inclusivos. Una regla que requiere ejercicio o fecha
de presentación no se aplica si ese dato falta. El informe conserva las
incidencias de los campos obligatorios y la advertencia de formato sin fecha.

Una extensión que reemplace un período antes del cálculo de plazos puede usar
prioridad `-50` y `reemplazar_periodo=True`. Si reemplaza el período después del
cálculo base y ello cambia el plazo, también debe devolver el plazo actualizado
con `reemplazar_plazo=True`. Las sustituciones quedan en la trazabilidad; las
reglas previas siguen figurando como ejecutadas.

Los identificadores duplicados y las vigencias invertidas se rechazan al cargar.
Los resultados se verifican antes de aplicarlos: estructura de incidencias,
período reconocido y fechas del plazo coherentes. Un conflicto sin reemplazo
explícito se trata como fallo y no sustituye los valores base.

Los fallos de ejecución producen `REGLA_NO_EJECUTADA` y estado QA Bloqueado.
No se acepta una declaración omitiendo silenciosamente una regla fallida.
Los cambios de una regla se aplican de forma atómica y se preserva la entrada
original. Los autores no deben modificar el contexto ni sus valores anidados.

## Informes y CLI

`--directorio-informes` escribe JSON, HTML y CSV. Se conservan `--salida` y
`--informe`; este último selecciona HTML o CSV por extensión y texto para las
otras extensiones. Las opciones `--informe-html` y `--informe-csv` permiten rutas
separadas. Las carpetas de salida se crean y no se sobrescribe el fichero de
entrada ni el layout. Repetir una ejecución sobre la misma carpeta reemplaza
sus informes anteriores.

HTML autónomo sin dependencias de red: datos escapados y fuentes enlazadas solo
con esquemas HTTP/HTTPS. CSV: una fila por caso, separador `;`, comillas según
`csv.writer`, UTF-8 con BOM y neutralización de celdas que parezcan fórmulas.

Código de salida 0 sin errores, 1 con errores, 2 ante entrada/configuración no
procesable. `--estricto-qa` también devuelve 1 si hay advertencias. La advertencia
de calendario nominal provoca revisión en modo estricto aunque no haya errores.

## Verificación y límites

78 pruebas de modalidades, transiciones, formatos de entrada, extensiones,
vigencias, conflictos, errores de plugins, mensajes, informes y CLI. CI ejecuta
la suite en Linux/Windows y Python 3.11/3.12/3.13.

Las reglas fiscales están revisadas a 08/10/2026. El formato ASCII necesita un
layout oficial verificado; el ejemplo del contrato no es un diseño AEAT. Los
plazos son nominales, sin ajuste automático por días inhábiles. No se calcula el
impuesto, ni se prueba el diseño visual del impreso, ni se garantiza aceptación
AEAT. El mapeo territorial Sage de clave catastral conserva su identificación
como requisito funcional, separado de las fuentes normativas.
