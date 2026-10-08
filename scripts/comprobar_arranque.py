"""Prueba de salud del servidor local; no abre navegador y lo detiene al acabar."""
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path


def main():
    comando = [sys.argv[1], '--sin-navegador'] if len(sys.argv) > 1 else [sys.executable, '-u', 'lanzador.py', '--sin-navegador']
    with tempfile.TemporaryFile(mode='w+b') as log:
        proceso = subprocess.Popen(comando, stdout=log, stderr=subprocess.STDOUT)
        try:
            for _ in range(100):
                time.sleep(.4)
                log.seek(0)
                texto = log.read().decode('utf-8', errors='replace')
                puertos = re.findall(r'http://127\.0\.0\.1:(\d+)', texto)
                if puertos:
                    try:
                        with urllib.request.urlopen(f'http://127.0.0.1:{puertos[0]}/_stcore/health', timeout=1) as respuesta:
                            if respuesta.status == 200:
                                print('OK: servidor local, salud HTTP 200.')
                                return
                    except OSError:
                        pass
                if proceso.poll() is not None:
                    raise RuntimeError('El lanzador terminó antes de arrancar:\n' + texto)
            raise RuntimeError('El servidor no respondió:\n' + texto)
        finally:
            proceso.terminate()
            proceso.wait(timeout=15)


if __name__ == '__main__':
    main()
