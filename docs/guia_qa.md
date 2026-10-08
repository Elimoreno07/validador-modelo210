# Guía de revisión para QA

La herramienta revisa declaraciones del Modelo 210 usadas en las pruebas de
Impresos Sage 200. El identificador `idCaso` permite relacionar cada resultado
con el caso del plan QA.

## Ejecutar una revisión

```shell
python -m validador_modelo210 declaraciones.json --directorio-informes output/qa
```

Abrir `output/qa/informe.html`. El resumen muestra bloqueados, pendientes de
revisión y preparados. Cada caso muestra modelo detectado, modalidad, período
informado y esperado, ejercicio, fechas y plazo. Los errores indican el campo,
qué sucede y qué revisar. Las reglas y sus versiones se despliegan al final.

Para relacionar un error con Sage, comparar la clave de renta, el apartado del
impreso y el período de la liquidación. El campo `IOFPeriodoPres` de Sage es un
mes de presentación; no sustituye al período fiscal `0A` o `1T`–`4T`.

## Interpretar el resultado

| Estado QA | Acción |
|---|---|
| Bloqueado | Corregir datos o comunicar la regla fallida antes de aceptar el caso. |
| Revisar | Contrastar y documentar las advertencias; no asumir aprobación automática. |
| Preparado | Los controles implementados no han encontrado incidencias. Continuar las pruebas del impreso. |

Los plazos nominales generan una advertencia para contrastar el calendario de
la campaña. Por eso, incluso una declaración con estado funcional `Correcto`
puede quedar en `Revisar`. Una presentación tardía se informa como advertencia
para permitir revisar los supuestos de presentación extemporánea.

Para un pipeline que bloquee también por advertencias:

```shell
python -m validador_modelo210 declaraciones.json --directorio-informes output/qa --estricto-qa
```

## Errores frecuentes

- Una renta individual informa `4T`: comprobar agrupación; el período esperado
  de una declaración individual es `0A`.
- La clave corresponde a transmisiones, pero se informa 210R: comprobar el
  apartado H y la clave seleccionada.
- La fecha de devengo pertenece a otro ejercicio: revisar el año de devengo,
  que puede diferir del de presentación.
- El plazo de Sage difiere del calculado: revisar ejercicio, resultado,
  agrupación y régimen aplicable. `plazoInformado` permite compararlo expresamente.
- La regla aparece como fallida: comunicar su identificador al responsable
  técnico; no aceptar el caso hasta recuperar la comprobación.

## Informe CSV

Abrir `informe.csv` en Excel usando UTF-8 y separador punto y coma si la apertura
automática no reconoce el formato. Una fila corresponde a una declaración.
Filtrar `estado_qa`, `modelo` o `errores` para preparar la revisión. Las columnas
de reglas permiten conservar la evidencia normativa de cada ejecución.

Los ejemplos en `docs/ejemplo` proceden de datos sintéticos. Los datos reales de
QA y sus informes deben mantenerse fuera de los archivos públicos del repositorio.

El contrato de entradas y alias se encuentra en
[README.txt](../validador_modelo210/README.txt); los detalles de extensión, en
[arquitectura.md](arquitectura.md).
