# Uso desde el navegador sin instalar ni descargar la aplicación

Aplicación activada por la propietaria:
https://validador-modelo210-fkeuevczxibs8rrtwubw5q.streamlit.app/

Para crear otro despliegue en Streamlit Community Cloud:

1. Accede a https://share.streamlit.io/ con tu cuenta y conecta GitHub.
2. Pulsa Create app y selecciona la opción de utilizar un repositorio existente.
3. Configura:
   - Repositorio: Elimoreno07/validador-modelo210
   - Rama: main
   - Archivo de entrada: app_web.py
   - Python: 3.12 en Advanced settings
4. Pulsa Deploy. La plataforma asignará la URL de la aplicación.
5. Comparte la URL que aparezca cuando termine el despliegue.

Fuente: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy

`requirements.txt` instala Streamlit y ReportLab. `.streamlit/config.toml`
configura cargas de hasta 10 MB y desactiva estadísticas de uso.
No se necesita el EXE, PyInstaller, una clave API ni instalar Python en el equipo
del usuario de la web.

`app_web.py` reutiliza la pantalla y el motor existentes. Cada sesión obtiene
una carpeta temporal propia para informes e historial. No se lee ni comparte
la carpeta de informes de otro usuario o la carpeta persistente del escritorio.
El historial web no es permanente: una nueva sesión o reinicio del servidor
puede perderlo. El usuario debe descargar los informes que quiera conservar.
Los datos se procesan en el servidor de alojamiento.

La aplicación local mantiene su historial persistente. El motor normativo no
se ha modificado. Para alojamiento privado, el mismo punto de entrada puede
utilizarse en un servidor con autenticación y almacenamiento adecuado.
