# Arquitectura de la aplicación local

`app.py` solo presenta datos y llama a `servicio_gui.py`. El servicio adapta el
archivo con `entrada_gui.py`, ejecuta `validar_conjunto` y genera los informes.
No cambia detectores, validaciones, reglas fiscales ni el contrato de la CLI.
Los plugins instalados del motor siguen disponibles al ejecutar desde Python.
Para distribuir nuevos plugins en el EXE deben incorporarse y recompilarse.

## Lectura de archivos

JSON contiene un objeto o lista de objetos. TXT admite los mismos JSON, objetos
JSON por línea o XML; los registros de longitud fija necesitan un layout.
ASCII/.210/.dat utiliza el descriptor versionado del motor: longitud exacta,
posiciones desde 1, campos sin solapamientos y valores vacíos explícitos.
El layout se carga por separado en Opciones de lectura. No se suministran
posiciones oficiales inventadas. UTF-8 es el valor predeterminado; se puede
seleccionar Windows-1252. Tamaño máximo: 10 MB por archivo.

XML utiliza los nombres de campo del contrato del motor. No es un importador
universal de esquemas XML AEAT o de cualquier exportación Sage.

```xml
<declaraciones>
  <declaracion>
    <tipoRenta>28</tipoRenta>
    <ejercicio>2026</ejercicio>
    <periodo>0A</periodo>
    <fechaDevengo>2026-11-15</fechaDevengo>
    <modalidadPresentacion>individual</modalidadPresentacion>
  </declaracion>
</declaraciones>
```

También se admite una raíz `declaracion` y namespaces. Para listas:
`<fechasDevengo><fecha>2026-11-15</fecha></fechasDevengo>` y
`<clavesRenta><clave>04</clave></clavesRenta>`.
Los objetos anidados, como `plazoInformado`, se representan con hijos.
Se rechazan campos duplicados, atributos, contenido mixto, DTD y entidades.
Un archivo ilegible produce un mensaje de lectura, sin una validación ficticia.

## Persistencia e informes

Cada ejecución válida a nivel de lectura crea una subcarpeta UTC+UUID en
`informes/`, incluso cuando hay errores funcionales. Guarda resultados.json,
informe.html, informe.csv, informe.pdf y validacion.json (metadatos del historial).
Se genera todo antes del guardado y se publica con un renombrado de carpeta;
un fallo no deja una entrada de historial completa parcialmente escrita.
El archivo original no se conserva. Los informes sí contienen los datos del
resultado; se guardan localmente y están excluidos del repositorio.

El historial lee las carpetas guardadas y permite recuperar resultados y
descargas después de reiniciar. Las carpetas incompletas se omiten.
Se puede configurar `MODELO210_INFORMES` para utilizar otra carpeta escribible.
En Python, la ubicación predeterminada es la raíz del proyecto; en el EXE,
la carpeta contigua al ejecutable, nunca el directorio temporal de PyInstaller.
El historial crece hasta que el usuario borra sus subcarpetas.

HTML y CSV reutilizan los generadores existentes. PDF usa ReportLab, texto
escapado, salto entre declaraciones y paginación automática. La interfaz
muestra Código, Tipo, Campo, Descripción y Solución; añade Caso en lotes.

## Lanzamiento y distribución

`lanzador.py` arranca Streamlit solo en 127.0.0.1, elige un puerto disponible,
desactiva la telemetría y el observador de archivos, espera la salud del servidor
y abre el navegador. La consola permite detenerlo con Ctrl+C; cerrar únicamente
la pestaña no detiene el servidor. `--sin-navegador` permite pruebas de arranque.

PyInstaller genera una distribución en carpeta. Hay que distribuir la carpeta
entera `dist/ValidadorModelo210`, incluyendo `_internal`. El EXE no necesita Python.
El spec incorpora app.py, ejemplos, módulos, recursos y metadatos de Streamlit.
La compilación debe realizarse en Windows con la arquitectura de destino.
El comando `ValidadorModelo210.exe --autoprueba` ejecuta los cuatro ejemplos y
genera sus informes con las dependencias empaquetadas; crea entradas de historial.

## Verificación

Las pruebas nuevas cubren equivalencia con el motor, todas las modalidades,
JSON/TXT/XML/ASCII, rechazo de entradas inválidas, persistencia, nombres únicos,
protección de rutas, fallo de exportación, PDF paginado y pantalla Streamlit.
Se mantienen todas las pruebas previas. AppTest comprueba estado, tablas y
descargas; la carga mediante selector/arrastre requiere además una prueba manual:

1. Abrir ejecutar.bat y arrastrar ejemplos/210I_correcto.json.
2. Pulsar Validar y comprobar modelo, ejercicio, período y avisos.
3. Descargar HTML, CSV y PDF y comprobar sus contenidos.
4. Validar 210I_error.json y revisar sus tres errores.
5. Reiniciar, abrir el resultado desde Historial y descargar los informes.
6. Repetir con TXT, XML y ASCII con un layout verificado.
