@echo off
setlocal
cd /d "%~dp0"
if exist "dist\ValidadorModelo210\ValidadorModelo210.exe" (
  "dist\ValidadorModelo210\ValidadorModelo210.exe"
  exit /b
)
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" lanzador.py
) else (
  py -3 lanzador.py
)
if errorlevel 1 (
  echo No se ha podido arrancar. Consulta la instalacion en README.md.
  pause
)
