# downloader.py
import time
import logging
from pathlib import Path
import yt_dlp

from config import Config
from utils import clean_filename

class SafeProgressHook:
    def __init__(self, callback=None, cancel_event=None):
        self.callback, self.cancel_event, self.last_update = callback, cancel_event, 0

    def __call__(self, data):
        if self.cancel_event and self.cancel_event.is_set(): raise yt_dlp.utils.DownloadError("Descarga cancelada.")
        if not self.callback: return
        try:
            current_time = time.time()
            if current_time - self.last_update < 1.0: return # Actualizar una vez por segundo
            self.last_update = current_time
            if data['status'] == 'downloading':
                self.callback({
                    'status': 'downloading',
                    'percentage': (data.get('downloaded_bytes', 0) / data.get('total_bytes_estimate', 1)) * 100,
                    'speed': int(data.get('speed', 0)),
                    'eta': data.get('eta', 0), # <-- NUEVO: Capturar tiempo estimado
                    'video_id': data.get('info_dict', {}).get('id'),
                })
        except Exception: pass

class DownloaderEngine:
    def __init__(self, output_path=None, max_retries=3):
        self.output_path = Path(output_path or Config.DOWNLOAD_PATH).expanduser().resolve()
        self.max_retries = max_retries; self.logger = logging.getLogger(__name__)
        self.output_path.mkdir(parents=True, exist_ok=True)

    def get_video_info(self, url):
        self.logger.info(f"Obteniendo información de: {url}")
        try:
            opts = {'quiet': True, 'no_warnings': True, 'extract_flat': 'in_playlist', 'skip_download': True}
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if 'entries' in info and info.get('entries'):
                    return {'type': 'playlist', 'title': info.get('title', 'Playlist'), 'entries': [self._parse_entry(e) for e in info['entries'] if e]}
                else:
                    return {'type': 'video', 'entries': [self._parse_entry(info)]}
        except Exception as e:
            self.logger.error(f"Error obteniendo información: {e}"); return {'type': 'error', 'message': str(e)}

    def _parse_entry(self, entry):
        video_id, webpage_url = entry.get('id'), entry.get('url') or entry.get('webpage_url')
        if not webpage_url and video_id: webpage_url = f"https://www.youtube.com/watch?v={video_id}"
        thumbnails, thumbnail_url = entry.get('thumbnails'), None
        if thumbnails and isinstance(thumbnails, list) and len(thumbnails) > 0:
            thumbnail_url = thumbnails[-1].get('url')
        if not thumbnail_url: thumbnail_url = entry.get('thumbnail')
        return {'id': video_id, 'url': webpage_url, 'title': clean_filename(entry.get('title', 'Video sin título')), 'duration': entry.get('duration', 0), 'thumbnail': thumbnail_url}

    def download_task(self, task, progress_callback, cancel_event):
        try:
            ydl_opts = {'outtmpl': str(self.output_path / f"%(title)s [%(id)s].%(ext)s"), 'quiet': True, 'noprogress': True, 'no_warnings': True, 'ignoreerrors': True, 'retries': self.max_retries, 'socket_timeout': 30, 'progress_hooks': [SafeProgressHook(progress_callback, cancel_event)]}
            fmt, quality = task['format'], task.get('quality', '720p')
            
            if fmt == 'mp3':
                ydl_opts['format'] = 'bestaudio/best'
                ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': task.get('audio_bitrate', '192')}]
            elif fmt == 'wav':
                ydl_opts['format'] = 'bestaudio/best'
                ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'wav'}]
            elif fmt == 'mkv': # Si es MKV, siempre la mejor calidad.
                ydl_opts['format'] = 'bestvideo*+bestaudio/best'
                ydl_opts['merge_output_format'] = 'mkv'
            else: # MP4 u Original
                ydl_opts['format'] = 'bestvideo*+bestaudio/best' if quality == 'best' else f'bestvideo*[height<={quality[:-1]}]+bestaudio/best'
                if fmt in ['mp4']: ydl_opts['merge_output_format'] = fmt
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(task['url'], download=True)
                final_filepath = ydl.prepare_filename(info)
                if fmt in ['mp3', 'wav']:
                    final_filepath = Path(final_filepath).with_suffix(f'.{fmt}')
            progress_callback({'status': 'finished', 'video_id': task['id'], 'filename': str(final_filepath)})
        except Exception as e:
            status = 'cancelled' if "cancelada" in str(e) else 'error'
            progress_callback({'status': status, 'error_message': str(e), 'video_id': task['id']})
    
    def set_output_path(self, path):
        self.output_path = Path(path).expanduser().resolve(); self.output_path.mkdir(parents=True, exist_ok=True)
