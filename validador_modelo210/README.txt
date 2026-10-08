VALIDADOR MODELO 210 EN PYTHON
Versión de reglas: 08/10/2026. Python 3.11 o superior, sin dependencias externas.

Ejecutar desde el directorio que contiene la carpeta validador_modelo210:

  python -m validador_modelo210 validador_modelo210/ejemplos/declaraciones.json --salida resultado.json --informe informe.txt
  python -m unittest discover -s validador_modelo210/tests -v

El ejemplo contiene tres declaraciones correctas y una incompatible.
Código de salida: 0 sin errores; 1 errores de validación; 2 error de lectura/formato.

API:
  from validador_modelo210 import validar, validar_conjunto, validar_fichero
  resultado = validar({"tipoRenta": "04", "ejercicio": 2026,
                       "fechaDevengo": "2026-11-15", "periodo": "4T",
                       "modalidadPresentacion": "agrupada", "resultado": "ingresar"})
  # También admite un registro JSON como cadena.
  resultados = validar_conjunto([registro1, registro2])
  resultados = validar_fichero("declaraciones.json")

CONTRATO DE ENTRADA
  tipoRenta: clave AEAT de dos dígitos; admite también entero o claveRenta.
  ejercicio: entero entre 2011 y 9998; año de devengo, no de presentación.
  periodo: período fiscal informado, 0A o 1T/2T/3T/4T. Es obligatorio para contrastarlo.
  modalidadPresentacion: individual o agrupada. Alternativa: agrupacion booleano.
  fechaDevengo: obligatoria en individual. ISO, DD/MM/YYYY o DDMMAAAA.
  devengos: lista de fechas opcional para agrupación; para agrupación trimestral se
            necesitan fechas. En agrupación anual sin detalle se advierte que no
            se han contrastado todos los devengos con el ejercicio.
  resultado: obligatorio para 210R. ingresar, devolver, cuota_cero o importe con signo.
  tipoModelo: opcional; se contrasta contra el modelo calculado por tipoRenta.
  clavesRenta: opcional; lista de claves de la misma declaración, que deben coincidir.
  canalPresentacion: opcional, telematica o papel; no determina la agrupación.
  fechaPresentacion: opcional, permite comprobar ventana y activar casillas 2027.
  domiciliacion: opcional, booleano JSON true/false.
  fechaFinPeriodoRetencion: para calcular fin de devolución; no es fecha de devengo.
  numeroDias / cuotaParticipacion / claveReferenciaCatastral: casillas de 210I.
  situacionInmueble: opcional para contrastar mapeo territorial Sage solicitado.

Se aceptan alias Sage documentados en comun.py. Valores contradictorios de alias
generan error. No se infiere periodo desde IOFPeriodoPres: ese campo de Sage es
un mes de presentación, no el período fiscal AEAT.

FORMATO DE SALIDA
  tipoModelo, ejercicio, periodo (calculado), periodoInformado, fechaDevengo,
  estado, errores, advertencias, reglasAplicadas, plazoPresentacion, versionNormativa.
  Los errores y advertencias tienen codigo/campo/mensaje; cada regla incorpora fuente.
  Correcto significa que pasan los controles implementados, incluso si hay advertencias.

ENTRADAS EN FICHERO
  JSON: objeto o lista. JSONL/NDJSON: un objeto JSON por línea. CSV: cabecera con
  los nombres anteriores; separador coma, punto y coma o tabulación.
  Para domiciliacion en CSV usar true/false; el adaptador convierte a booleano.
  Los importes no admiten separador de miles. La salida JSON de consola es UTF-8.
  Un fichero ASCII/.210 necesita --layout con un descriptor JSON versionado:

  {"version":"IDENTIFICADOR_DEL_DISENO_VERIFICADO", "longitudRegistro":14,
   "campos":{"tipoRenta":{"inicio":1,"longitud":2},
             "ejercicio":{"inicio":3,"longitud":4},
             "fechaDevengo":{"inicio":7,"longitud":8,"valoresVacios":["00000000"]}}}

  Este descriptor de 14 caracteres es solo ilustrativo; no es el diseño AEAT.
  Posiciones desde 1; longitud exacta; sin solapamientos. Cada línea es un registro.
  El descriptor debe incluir los campos necesarios para validar, como período,
  agrupación y resultado. El fichero no lleva tratamiento implícito de envoltorios.
  Usar --encoding cp1252 para ficheros Windows-1252, cuando corresponda.
  No se incluye un layout oficial 2027 sin sus posiciones verificadas.

ARQUITECTURA
  detector_modelo.py: catálogo explícito I/H/R, incompatibilidades y detección de G.
  detector_periodo.py: 0A frente a trimestre según agrupación, renta y resultado.
  reglas_210I.py: devengo anual, transición del plazo y casillas desde 2027.
  reglas_210H.py: plazo de transmisión y exclusión de domiciliación del tipo 28.
  reglas_210R.py: resultado, agrupación, alquileres 2024 y transición de plazo 2026.
  validador.py: normalización, obligatorios, coherencia y aplicación de reglas.
  entrada.py: lectura de formatos; informe.py: informe final legible; __main__.py: CLI.
  tests/: pruebas unitarias por modalidad, entradas y CLI.

DECISIONES Y LÍMITES
  El período de una renta individual es 0A. Una fecha de noviembre no implica 4T.
  El resultado solicitado 210R/4T es válido para una agrupación trimestral a ingresar
  de una renta que lo permita. En agrupación no se informa la casilla de devengo:
  fechaDevengo, si se recibe, se trata como evidencia auxiliar con advertencia.
  Las rentas 24/25/26/31/36/38 se detectan como 210G y se rechazan por fuera de alcance.
  No se calcula impuesto, ni se valida NIF, base, cuota o requisitos completos de
  agrupación. Los nuevos campos inmobiliarios se comprueban en 210I; la revisión
  completa de contenido del nuevo formulario 210R queda fuera de este validador
  de modalidad/período. El mapeo catastral Sage se distingue de las reglas legales.
  Plazos nominales, sin calendario de días inhábiles ni prórrogas especiales.
  Presentación tardía produce advertencia para permitir extemporáneas.
  Para limitar fechas futuras usar --fecha-referencia YYYY-MM-DD o fecha_referencia
  en la API. No se usa el reloj del equipo de forma implícita.
  Ejercicios posteriores a 2026 usan reglas conocidas y generan advertencia para
  revisar cambios posteriores. No se garantiza normativa histórica especial ajena
  al alcance de las reglas indicadas ni aceptación por los servicios AEAT.

FUENTES
  Instrucciones AEAT, catálogo y período fiscal:
  https://sede.agenciatributaria.gob.es/Sede/todas-gestiones/impuestos-tasas/impuesto-sobre-renta-no-residentes/modelo-210-irnr______a-no-residentes-permanente_/instrucciones.html
  Orden HAC/623/2026 y entrada en vigor:
  https://www.boe.es/eli/es/o/2026/06/12/hac623
  Transición de plazos, nota AEAT:
  https://www3.agenciatributaria.gob.es/Sede/todas-gestiones/impuestos-tasas/impuesto-sobre-renta-no-residentes/modelo-210-irnr______a-no-residentes-permanente_/nota-modificaciones-plazos-presentacion-modelo-210.html
