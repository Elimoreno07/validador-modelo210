"""Pantalla local de QA. Lanzar con ejecutar.bat o streamlit run app.py."""
import csv
import hashlib
from pathlib import Path
import streamlit as st
from validador_modelo210.entrada import leer_json
from validador_modelo210.servicio_gui import (ejecutar_validacion, directorio_informes,
                                             incidencias, leer_historial, cargar_validacion)

st.set_page_config(page_title='QA Sage 200 · Modelo 210', page_icon='✅', layout='wide')
st.title('QA Impresos Sage 200')
st.caption('Validación previa del Modelo 210 · 210I / 210H / 210R')
destino = st.session_state.get('_directorio_web')
if destino:
    st.caption('Versión web: los ficheros se procesan en el servidor. El historial pertenece a esta sesión; descarga los informes que quieras conservar.')
st.write('Selecciona un fichero o arrástralo al área de carga y pulsa Validar.')
st.markdown('**Seleccionar fichero**')
fichero = st.file_uploader('Seleccionar fichero', type=['json', 'txt', 'xml', '210', 'ascii', 'dat', 'csv', 'jsonl', 'ndjson'])
with st.expander('Opciones de lectura (ASCII y codificación)'):
    codificacion = st.selectbox('Codificación', ['utf-8-sig', 'cp1252'])
    layout_subido = st.file_uploader('Layout JSON versionado (obligatorio para registros de longitud fija)', type=['json'], key='layout')
    st.caption('TXT admite JSON, JSON por línea, XML o registros fijos con layout. XML: raíz declaracion o declaraciones.')

firma = hashlib.sha256(fichero.getvalue() + codificacion.encode() + (layout_subido.getvalue() if layout_subido else b'')).hexdigest() if fichero else None
if st.session_state.get('firma') != firma:
    st.session_state.pop('actual', None)
    st.session_state['firma'] = firma
if st.button('Validar', type='primary', disabled=fichero is None):
    st.session_state.pop('actual', None)
    try:
        with st.spinner('Validando y guardando informes…'):
            layout = leer_json(layout_subido.getvalue().decode('utf-8-sig')) if layout_subido else None
            st.session_state['actual'] = ejecutar_validacion(fichero.getvalue(), fichero.name, destino=destino, layout=layout, encoding=codificacion)
    except (ValueError, UnicodeError, csv.Error) as exc:
        st.error('No se ha podido leer el fichero: ' + str(exc))
    except OSError:
        st.error('No se pueden guardar los informes. Comprueba los permisos de la carpeta informes.')

actual = st.session_state.get('actual')
if actual:
    resultados = actual['resultados']
    errores = sum(len(r['errores']) for r in resultados)
    avisos = sum(len(r['advertencias']) for r in resultados)
    (st.error if errores else st.success)('❌ Validación incorrecta' if errores else '✅ Validación correcta')
    if avisos:
        st.warning(f'{avisos} avisos pendientes de revisión para QA.')
    columnas = st.columns(3)
    for columna, titulo, valor in zip(columnas, ['Declaraciones', 'Errores', 'Avisos'], [len(resultados), errores, avisos]):
        columna.metric(titulo, valor)
    st.dataframe([{'Caso': i, 'Modelo': r['tipoModelo'] or 'Indeterminado', 'Ejercicio': r['ejercicio'],
                   'Período': r['periodo'], 'Estado QA': r.get('estadoQA'), 'Plazo': r.get('estadoPlazo'),
                   'Errores': len(r['errores']), 'Avisos': len(r['advertencias'])}
                  for i, r in enumerate(resultados, 1)], hide_index=True, width='stretch')
    tabla = incidencias(resultados)
    if tabla:
        st.dataframe(tabla, hide_index=True, width='stretch')
    else:
        st.info('Sin incidencias en los controles aplicados.')
    with st.expander('Plazos y reglas aplicadas'):
        st.json([{'caso': i, 'plazo': r['plazoPresentacion'], 'reglas': r['reglasAplicadas'],
                  'trazabilidad': r.get('reglasEjecutadas')} for i, r in enumerate(resultados, 1)])
    for columna, extension, mime in zip(st.columns(3), ['html', 'csv', 'pdf'], ['text/html', 'text/csv', 'application/pdf']):
        columna.download_button('Exportar ' + extension.upper(), actual['archivos']['informe.' + extension],
                                file_name='informe_210.' + extension, mime=mime)
    st.caption('Informes guardados en esta sesión.' if destino else 'Informes guardados en: ' + actual['carpeta'])

st.subheader('Historial de validaciones')
try:
    historial = leer_historial(destino)
    if historial:
        st.dataframe([{'Fecha (UTC)': m['fecha'], 'Fichero': m['fichero'], 'Errores': m['errores'],
                       'Avisos': m['avisos']} for m in historial], hide_index=True, width='stretch')
        seleccionado = st.selectbox('Validación guardada', [m['id'] for m in historial],
            format_func=lambda i: next(m['fecha'] + ' · ' + m['fichero'] for m in historial if m['id'] == i))
        if st.button('Abrir resultado del historial'):
            st.session_state['actual'] = cargar_validacion(seleccionado, destino)
            st.rerun()
    else:
        st.caption('Todavía no hay validaciones guardadas.')
except (OSError, ValueError, KeyError):
    st.warning('No se ha podido cargar el historial. Comprueba la carpeta de informes.')
if not destino:
    st.caption('Carpeta de informes: ' + str(directorio_informes()))
st.caption('El resultado corresponde a los controles del motor. Los plazos son nominales y requieren revisión de los avisos.')
