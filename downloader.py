# downloader.py
import time
import logging
from pathlib import Path
import yt_dlp
import ffmpeg
import os

from config import Config
from utils import clean_filename, check_disk_space, format_bytes

class SafeProgressHook:
    """Hook de progreso que ahora también maneja la cancelación."""
    def __init__(self, callback=None, cancel_event=None):
        self.callback = callback
        self.cancel_event = cancel_event # <-- Evento para saber si cancelar
        self.last_update = 0

    def __call__(self, data):
        # --- LÓGICA DE CANCELACIÓN ---
        # En cada actualización de progreso, revisamos si se pidió cancelar.
        if self.cancel_event and self.cancel_event.is_set():
            # Si es así, lanzamos una excepción para detener a yt-dlp.
            raise Exception("Descarga cancelada por el usuario.")
        # -----------------------------
            
        if not self.callback:
            return
        
        # El resto del método se mantiene igual...
        try:
            # ... (código del callback sin cambios) ...
            current_time = time.time()
            if current_time - self.last_update < 1.0:
                return
            self.last_update = current_time
            
            status = data.get('status')
            
            if status == 'downloading':
                info_dict = data.get('info_dict', {})
                downloaded = data.get('downloaded_bytes', 0)
                total = data.get('total_bytes') or data.get('total_bytes_estimate', 0)
                speed = data.get('speed', 0)
                percentage = (downloaded / total) * 100 if total > 0 else 0
                
                progress_data = {
                    'status': 'downloading', 'percentage': percentage,
                    'downloaded_bytes': int(downloaded), 'total_bytes': int(total),
                    'speed': int(speed), 'filename': info_dict.get('filename', ''),
                }
            elif status == 'finished':
                progress_data = {
                    'status': 'finished', 'percentage': 100,
                    'filename': data.get('info_dict', {}).get('filename', ''),
                }
            else:
                return
            
            self.callback(progress_data)
        except Exception as e:
            # No registrar el error si es nuestra propia excepción de cancelación
            if "cancelada por el usuario" not in str(e):
                logging.debug(f"Error en callback de progreso (ignorado): {e}")
            else:
                # Re-lanzar la excepción de cancelación para que el downloader la atrape
                raise e


class AnimeDownloader:
    # ... (el __init__ y otros métodos se mantienen igual) ...
    def __init__(self, output_path=None, quality='720p', max_retries=3):
        self.output_path = Path(output_path or Config.DOWNLOAD_PATH).expanduser().resolve()
        self.quality = quality
        self.max_retries = max_retries
        self.logger = logging.getLogger(__name__)
        self.output_path.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Downloader inicializado - Calidad: {quality}")

    # Este método ahora acepta el 'cancel_event'
    def _get_ydl_config(self, progress_callback=None, convert_format='none', cancel_event=None):
        config = {
            'outtmpl': str(self.output_path / '%(title)s.%(ext)s'),
            'quiet': True, 'noprogress': True, 'no_warnings': True,
            'ignoreerrors': True, 'retries': self.max_retries, 'socket_timeout': 30,
            # Pasamos el evento de cancelación a nuestro hook
            'progress_hooks': [SafeProgressHook(progress_callback, cancel_event)] if progress_callback else [],
        }
        if convert_format == 'mp3':
            config['format'] = 'bestaudio/best'
            config['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]
        else:
            config['format'] = f'bestvideo[ext=mp4][height<={self.quality[:-1]}]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            config['merge_output_format'] = 'mp4'
        return config

    # Este método ahora acepta y pasa el 'cancel_event'
    def download_episode_safe(self, url, progress_callback=None, convert_format='none', cancel_event=None):
        self.logger.info(f"Iniciando descarga de: {url} | Formato: {convert_format.upper()}")
        
        if not self._check_available_space():
            if progress_callback: progress_callback({'status': 'error', 'error_message': 'Espacio en disco insuficiente.'})
            return False

        # Pasamos el evento de cancelación a la configuración de yt-dlp
        ydl_opts = self._get_ydl_config(progress_callback, convert_format, cancel_event)
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

            if not info: raise Exception("yt-dlp no devolvió información.")
            
            filename = ydl.prepare_filename(info)
            if convert_format == 'mp3': filename = Path(filename).with_suffix('.mp3')
            
            final_filepath = str(filename)
            if convert_format == 'mp4':
                final_filepath = self._ensure_mp4_container(final_filepath, progress_callback, cancel_event)
                if not final_filepath: return False

            if progress_callback: progress_callback({'status': 'finished', 'filename': final_filepath})
            return True

        except Exception as e:
            if "cancelada por el usuario" in str(e):
                self.logger.info("La descarga fue cancelada por el usuario.")
                if progress_callback: progress_callback({'status': 'cancelled'})
            else:
                self.logger.error(f"Fallo la descarga de {url} con error: {e}")
                if progress_callback: progress_callback({'status': 'error', 'error_message': str(e)})
            return False

    # Modificamos el método de conversión para que también sea cancelable
    def _ensure_mp4_container(self, input_path, progress_callback, cancel_event):
        input_path = Path(input_path)
        if input_path.suffix == '.mp4': return str(input_path)

        output_path = input_path.with_suffix('.mp4')
        if progress_callback: progress_callback({'status': 'converting', 'filename': str(output_path)})
        
        try:
            # Aquí no podemos cancelar FFmpeg fácilmente, pero revisamos antes de empezar
            if cancel_event and cancel_event.is_set(): raise Exception("Conversión cancelada por el usuario.")
            
            ffmpeg.input(str(input_path)).output(str(output_path), vcodec='copy', acodec='copy').run(overwrite_output=True, quiet=True)
            os.remove(input_path)
            return str(output_path)
        except Exception as e:
            if "cancelada por el usuario" not in str(e):
                self.logger.error(f"Error de FFmpeg: {e}")
                if progress_callback: progress_callback({'status': 'error', 'error_message': 'Fallo al re-empaquetar a MP4'})
            # No necesitamos hacer nada más si se canceló
            return None
    
    # ... (El resto de métodos: get_video_info, set_output_path, etc., se mantienen igual) ...
    def get_video_info(self, url):
        try:
            opts = {'quiet': True, 'no_warnings': True, 'extract_flat': False}
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info:
                    return {'title': clean_filename(info.get('title', 'Unknown')), 'duration': info.get('duration', 0), 'uploader': info.get('uploader', 'Unknown'), 'thumbnail': info.get('thumbnail')}
        except Exception as e:
            self.logger.error(f"Error obteniendo información del video: {e}")
            return None

    def set_output_path(self, path):
        self.output_path = Path(path).expanduser().resolve()
        self.output_path.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Ruta de descarga actualizada a: {self.output_path}")

    def _check_available_space(self, min_space_gb=1):
        try:
            available = check_disk_space(self.output_path)
            if available < (min_space_gb * 1024**3):
                self.logger.error(f"Espacio insuficiente en disco. Disponible: {format_bytes(available)}")
                return False
            self.logger.info(f"Espacio disponible: {format_bytes(available)}")
            return True
        except Exception as e:
            self.logger.warning(f"No se pudo verificar el espacio en disco: {e}")
            return True
