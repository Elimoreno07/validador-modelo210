# Validador del Modelo 210

Herramienta local en Python para detectar la modalidad **210I**, **210H** o
**210R**, calcular el período fiscal y contrastarlo con los datos informados.
Devuelve JSON e informes con reglas aplicadas, errores y advertencias.

Python 3.11 o superior. Sin dependencias externas en tiempo de ejecución.

## Uso

Desde la raíz del repositorio:

```shell
python -m validador_modelo210 entrada.json --salida resultado.json --informe informe.txt
```

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
  tests/
```

## Pruebas

```shell
python -m unittest discover -s validador_modelo210/tests -v
```

Se incluyen 57 pruebas y un flujo de GitHub Actions para Linux y Windows.

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
