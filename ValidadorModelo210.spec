# Compilar en Windows: pyinstaller --clean --noconfirm ValidadorModelo210.spec
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules, copy_metadata

base = Path(SPECPATH)
datas, binaries, hiddenimports = [], [], []
for paquete in ('streamlit', 'reportlab'):
    d, b, h = collect_all(paquete)
    datas += d
    binaries += b
    hiddenimports += h
datas += copy_metadata('streamlit', recursive=True)
datas += [(str(base / 'app.py'), '.'), (str(base / 'ejemplos'), 'ejemplos')]
hiddenimports += collect_submodules('validador_modelo210', filter=lambda nombre: '.tests' not in nombre)
a = Analysis([str(base / 'lanzador.py')], pathex=[str(base)], binaries=binaries,
             datas=datas, hiddenimports=hiddenimports, excludes=['pytest', 'IPython', 'matplotlib', 'scipy'])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='ValidadorModelo210', console=True)
coll = COLLECT(exe, a.binaries, a.datas, name='ValidadorModelo210')
