# downloader.py
import time
import logging
from pathlib import Path
import yt_dlp
import ffmpeg
import os
from threading import Event

from config import Config
from utils import clean_filename, check_disk_space, format_bytes

class SafeProgressHook:
    def __init__(self, callback=None, cancel_event=None):
        self.callback = callback
        self.cancel_event = cancel_event
        self.last_update = 0

    def __call__(self, data):
        if self.cancel_event and self.cancel_event.is_set():
            raise Exception("Descarga cancelada por el usuario.")
        
        if not self.callback: return

        try:
            current_time = time.time()
            if current_time - self.last_update < 1.0: return
            self.last_update = current_time
            
            status = data.get('status')
            
            if status == 'downloading':
                info_dict = data.get('info_dict', {})
                progress_data = {
                    'status': 'downloading',
                    'percentage': (data.get('downloaded_bytes', 0) / (data.get('total_bytes') or data.get('total_bytes_estimate', 1))) * 100,
                    'downloaded_bytes': int(data.get('downloaded_bytes', 0)),
                    'total_bytes': int(data.get('total_bytes') or data.get('total_bytes_estimate', 0)),
                    'speed': int(data.get('speed', 0)),
                    'filename': info_dict.get('filename', ''),
                    'video_id': info_dict.get('id'),
                }
            elif status == 'finished':
                progress_data = {
                    'status': 'finished',
                    'filename': data.get('info_dict', {}).get('filename', ''),
                    'video_id': data.get('info_dict', {}).get('id'),
                }
            else:
                return
            
            self.callback(progress_data)
        except Exception as e:
            if "cancelada por el usuario" in str(e): raise e
            logging.debug(f"Error en callback (ignorado): {e}")

class AnimeDownloader:
    def __init__(self, output_path=None, quality='720p', max_retries=3):
        self.output_path = Path(output_path or Config.DOWNLOAD_PATH).expanduser().resolve()
        self.quality = quality
        self.max_retries = max_retries
        self.logger = logging.getLogger(__name__)
        self.output_path.mkdir(parents=True, exist_ok=True)

    def _get_ydl_config(self, progress_callback, cancel_event, task):
        config = {
            'outtmpl': str(self.output_path / '%(title)s [%(id)s].%(ext)s'),
            'quiet': True, 'noprogress': True, 'no_warnings': True,
            'ignoreerrors': True, 'retries': self.max_retries, 'socket_timeout': 30,
            'progress_hooks': [SafeProgressHook(progress_callback, cancel_event)],
            'noplaylist': task['type'] != 'playlist',
        }

        fmt = task['format']
        if fmt == 'mp3':
            config['format'] = 'bestaudio/best'
            config['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': task.get('audio_bitrate', '192'),
            }]
        elif fmt == 'mkv':
             config['format'] = f'bestvideo[height<={self.quality[:-1]}]+bestaudio/best[height<={self.quality[:-1]}]'
             config['merge_output_format'] = 'mkv'
        else: # MP4 o Original
            config['format'] = f'bestvideo[ext=mp4][height<={self.quality[:-1]}]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            if fmt == 'mp4':
                config['merge_output_format'] = 'mp4'

        return config

    def get_video_info(self, url):
        """Obtiene información de una URL (video o playlist)."""
        self.logger.info(f"Obteniendo información de: {url}")
        try:
            opts = {'quiet': True, 'no_warnings': True, 'extract_flat': True, 'skip_download': True}
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if 'entries' in info: # Es una playlist o canal
                    return {
                        'type': 'playlist',
                        'title': info.get('title', 'Playlist sin título'),
                        'uploader': info.get('uploader', 'Desconocido'),
                        'entries': [self._parse_entry(entry) for entry in info['entries']]
                    }
                else: # Es un video individual
                    return {
                        'type': 'video',
                        'entries': [self._parse_entry(info)]
                    }
        except Exception as e:
            self.logger.error(f"Error obteniendo información del video: {e}")
            return {'type': 'error', 'message': str(e)}

    def _parse_entry(self, entry):
        return {
            'id': entry.get('id'),
            'url': entry.get('webpage_url') or f"https://www.youtube.com/watch?v={entry.get('id')}",
            'title': clean_filename(entry.get('title', 'Video sin título')),
            'duration': entry.get('duration', 0),
            'thumbnail': entry.get('thumbnail'),
        }

    def download_task(self, task, progress_callback, cancel_event):
        """Descarga una tarea individual (que puede ser un video de una playlist)."""
        self.logger.info(f"Iniciando descarga de: {task['url']} | Formato: {task['format'].upper()}")
        
        if not self._check_available_space():
            if progress_callback: progress_callback({'status': 'error', 'error_message': 'Espacio insuficiente.'})
            return
        
        ydl_opts = self._get_ydl_config(progress_callback, cancel_event, task)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(task['url'], download=True)
            
            if not info: raise Exception("yt-dlp no devolvió información.")
            
            filename = ydl.prepare_filename(info)
            if task['format'] == 'mp3':
                filename = Path(filename).with_suffix('.mp3')
            
            self.logger.info(f"Descarga y procesamiento completado. Archivo: {filename}")

        except Exception as e:
            if "cancelada por el usuario" in str(e):
                self.logger.info(f"Descarga de {task['id']} cancelada.")
                progress_callback({'status': 'cancelled', 'video_id': task['id']})
            else:
                self.logger.error(f"Fallo la descarga de {task['url']} con error: {e}")
                progress_callback({'status': 'error', 'error_message': str(e), 'video_id': task['id']})

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
