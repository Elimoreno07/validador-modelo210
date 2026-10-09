"""Entrada cloud: almacenamiento temporal independiente por sesión de usuario."""
import runpy
import tempfile
from pathlib import Path
import streamlit as st

if '_almacen_web' not in st.session_state:
    st.session_state['_almacen_web'] = tempfile.TemporaryDirectory(prefix='modelo210_')
st.session_state['_directorio_web'] = str(Path(st.session_state['_almacen_web'].name) / 'informes')
runpy.run_path(str(Path(__file__).resolve().with_name('app.py')), run_name='__main__')
