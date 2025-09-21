# config.py
import os
import logging
from pathlib import Path

class Config:
    # --- Configuración para Downloader ---
    DOWNLOAD_PATH = str(Path.home() / "descargas") # Ruta por defecto
    DEFAULT_QUALITY = '720p'                        # Calidad por defecto para descargas
    MAX_RETRIES = 5                                 # Número máximo de reintentos
    USE_RATE_LIMITING = True                        # Usar limitación de tasa (útil para JKAnime)

    # --- Configuración para Logging ---
    LOG_LEVEL = logging.INFO                        # Nivel de logging (INFO, DEBUG, WARNING, ERROR)
    LOG_FILE = "downloader.log"                     # Archivo de log
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
