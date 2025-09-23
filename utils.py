# utils.py
import sys
import re
import os
import shutil
import logging
from urllib.parse import urlparse

from config import Config # Importamos la configuración para logging

def clean_filename(filename):
    """Elimina caracteres no válidos de un nombre de archivo."""
    # Elimina caracteres que son problemáticos en la mayoría de los sistemas operativos
    cleaned = re.sub(r'[\\/*?:"<>|]', "", filename)
    # Reemplaza espacios múltiples con uno solo
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def check_disk_space(path):
    """Verifica el espacio libre en disco en la ruta dada (en bytes)."""
    # shutil.disk_usage devuelve (total, usado, libre)
    total, used, free = shutil.disk_usage(os.path.realpath(path))
    return free

def format_bytes(byte_count):
    """Formatea un número de bytes a un formato legible (KB, MB, GB)."""
    if byte_count is None or byte_count == 0:
        return "0 B"
    power = 1024
    n = 0
    power_labels = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while byte_count >= power and n < len(power_labels) -1 :
        byte_count /= power
        n += 1
    return f"{byte_count:.2f} {power_labels[n]}B"

def setup_logging(verbose=False):
    """Configura el sistema de logging para la aplicación."""
    log_level = logging.DEBUG if verbose else Config.LOG_LEVEL
    
    # Configurar el logger raíz
    logging.basicConfig(
        level=log_level,
        format=Config.LOG_FORMAT,
        handlers=[
            logging.FileHandler(Config.LOG_FILE),
            logging.StreamHandler(sys.stdout) # También imprime en consola
        ]
    )
    # Deshabilitar loggers de librerías externas para evitar spam
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('yt_dlp').setLevel(logging.WARNING) # yt-dlp tiene su propio logging interno
    logging.getLogger('requests').setLevel(logging.WARNING)
    
    logging.info("Logging configurado.")


def validate_url(url):
    """Valida si una cadena es una URL bien formada."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False

def extract_video_info(url):
    """
    Función para extraer información de un video.
    Actualmente, esta lógica está dentro de la clase AnimeDownloader,
    así que esta función es un placeholder por si se necesita en el futuro.
    """
    print(f"Llamada a extract_video_info con la URL: {url}")
    # En el futuro, aquí podrías poner lógica para llamar a yt-dlp
    # y obtener información si lo necesitaras fuera de la clase principal.
    return None
