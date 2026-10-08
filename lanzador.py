"""Lanzador común para Python y PyInstaller; servidor solo en loopback."""
import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path


def puerto_libre():
    with socket.socket() as servidor:
        servidor.bind(('127.0.0.1', 0))
        return servidor.getsockname()[1]


def abrir_cuando_listo(puerto):
    for _ in range(120):
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{puerto}/_stcore/health', timeout=1) as respuesta:
                if respuesta.status == 200:
                    webbrowser.open(f'http://127.0.0.1:{puerto}')
                    return
        except OSError:
            time.sleep(.5)


def main():
    base = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
    destino = Path(sys.executable).parent if getattr(sys, 'frozen', False) else base
    os.environ.setdefault('MODELO210_INFORMES', str(destino / 'informes'))
    if '--autoprueba' in sys.argv:
        from validador_modelo210.servicio_gui import ejecutar_validacion
        for nombre, modelo, correcto in [('210I_correcto', '210I', True), ('210I_error', '210I', False),
                                         ('210H_correcto', '210H', True), ('210R_correcto', '210R', True)]:
            entrega = ejecutar_validacion((base / 'ejemplos' / (nombre + '.json')).read_bytes(), nombre + '.json')
            resultado = entrega['resultados'][0]
            if resultado['tipoModelo'] != modelo or (not resultado['errores']) != correcto:
                raise RuntimeError('Autoprueba fallida: ' + nombre)
            print('OK: ' + nombre + ' - HTML, CSV, PDF y JSON generados.')
        return
    from streamlit.web import bootstrap
    puerto = puerto_libre()
    opciones = {'global.developmentMode': False, 'server.address': '127.0.0.1', 'server.port': puerto,
        'server.headless': True, 'server.maxUploadSize': 10,
        'server.fileWatcherType': 'none', 'browser.gatherUsageStats': False}
    bootstrap.load_config_options(opciones)
    if '--sin-navegador' not in sys.argv:
        threading.Thread(target=abrir_cuando_listo, args=(puerto,), daemon=True).start()
    print(f'QA Sage 200: http://127.0.0.1:{puerto}\nCierra esta ventana o pulsa Ctrl+C para detener la aplicación.', flush=True)
    bootstrap.run(str(base / 'app.py'), False, [], opciones)


if __name__ == '__main__':
    main()
