"""Servicio de escritorio independiente de Streamlit; historial persistente."""
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from .entrada_gui import cargar_subida
from .informe import generar_html, generar_csv
from .informe_pdf import generar_pdf
from .validador import validar_conjunto


def directorio_informes():
    if os.environ.get('MODELO210_INFORMES'):
        return Path(os.environ['MODELO210_INFORMES']).expanduser().resolve()
    base = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent.parent
    return base / 'informes'


def incidencias(resultados):
    return [{'Caso': i, 'Código': aviso['codigo'], 'Tipo': tipo, 'Campo': aviso.get('campo', ''),
             'Descripción': aviso['mensaje'], 'Solución': aviso.get('accionQA', 'Revisar el campo indicado.')}
            for i, r in enumerate(resultados, 1) for tipo, clave in (('Error', 'errores'), ('Aviso', 'advertencias'))
            for aviso in r[clave]]


def ejecutar_validacion(contenido, nombre, *, destino=None, layout=None, encoding='utf-8-sig', registro_reglas=None):
    filas = cargar_subida(contenido, nombre, layout=layout, encoding=encoding)
    resultados = validar_conjunto(filas, registro_reglas=registro_reglas)
    archivos = {'resultados.json': json.dumps(resultados, ensure_ascii=False, indent=2).encode('utf-8'),
                'informe.html': generar_html(resultados).encode('utf-8'),
                'informe.csv': generar_csv(resultados).encode('utf-8'),
                'informe.pdf': generar_pdf(resultados)}
    momento = datetime.now(timezone.utc)
    identificador = momento.strftime('%Y%m%dT%H%M%S') + '_' + uuid4().hex
    base = (Path(destino) if destino is not None else directorio_informes()).resolve()
    base.mkdir(parents=True, exist_ok=True)
    temporal = base / ('.pendiente_' + identificador)
    final = base / identificador
    meta = {'id': identificador, 'fecha': momento.isoformat(), 'fichero': nombre.replace('\\', '/').rsplit('/', 1)[-1],
            'declaraciones': len(resultados), 'errores': sum(len(r['errores']) for r in resultados),
            'avisos': sum(len(r['advertencias']) for r in resultados)}
    try:
        temporal.mkdir()
        for archivo, contenido_archivo in archivos.items():
            (temporal / archivo).write_bytes(contenido_archivo)
        (temporal / 'validacion.json').write_text(json.dumps(meta, ensure_ascii=False), encoding='utf-8')
        temporal.rename(final)
    except OSError:
        shutil.rmtree(temporal, ignore_errors=True)
        raise
    return {'meta': meta, 'resultados': resultados, 'archivos': archivos, 'carpeta': str(final)}


def leer_historial(destino=None):
    base = Path(destino) if destino is not None else directorio_informes()
    historial = []
    for ruta in base.glob('*/validacion.json'):
        if ruta.parent.name.startswith('.'):
            continue
        try:
            meta = json.loads(ruta.read_text(encoding='utf-8'))
            if meta['id'] == ruta.parent.name and all(k in meta for k in ('fecha', 'fichero', 'errores', 'avisos')):
                historial.append(meta)
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return sorted(historial, key=lambda m: m['fecha'], reverse=True)


def cargar_validacion(identificador, destino=None):
    base = (Path(destino) if destino is not None else directorio_informes()).resolve()
    carpeta = (base / identificador).resolve()
    if carpeta.parent != base or identificador.startswith('.'):
        raise ValueError('Identificador de historial no válido.')
    return {'meta': json.loads((carpeta / 'validacion.json').read_text(encoding='utf-8')),
            'resultados': json.loads((carpeta / 'resultados.json').read_text(encoding='utf-8')),
            'archivos': {n: (carpeta / n).read_bytes() for n in ('resultados.json', 'informe.html', 'informe.csv', 'informe.pdf')},
            'carpeta': str(carpeta)}
