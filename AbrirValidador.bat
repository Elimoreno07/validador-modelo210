@echo off
setlocal
cd /d "%~dp0"
if exist "ValidadorModelo210.exe" (
  "ValidadorModelo210.exe"
  exit /b
)
if exist "ValidadorModelo210\ValidadorModelo210.exe" (
  "ValidadorModelo210\ValidadorModelo210.exe"
  exit /b
)
if exist "dist\ValidadorModelo210\ValidadorModelo210.exe" (
  "dist\ValidadorModelo210\ValidadorModelo210.exe"
  exit /b
)
echo Descarga y descomprime la version Windows desde:
echo https://github.com/Elimoreno07/validador-modelo210/releases/latest
echo Abre AbrirValidador.bat dentro de la carpeta descomprimida.
pause
