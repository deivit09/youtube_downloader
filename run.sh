#!/bin/bash

# Activa el entorno virtual
source "$(dirname "$0")/venv/bin/activate"

# --- EJECUCIÓN EN SEGUNDO PLANO ---
# 'nohup' hace que el proceso ignore la señal de cierre de la terminal.
# 'python -u' usa salida sin búfer, bueno para logs.
# '> downloader.log 2>&1' redirige toda la salida (normal y de error) al archivo de log.
# '&' ejecuta todo el comando en segundo plano.

echo "Lanzando la aplicación en segundo plano..."
nohup python -u "$(dirname "$0")/main.py" --gui > downloader.log 2>&1 &

echo "La aplicación se está ejecutando. Puedes cerrar esta terminal."
