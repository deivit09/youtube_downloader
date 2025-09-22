# gui.py
import customtkinter as ctk
import threading
from tkinter import StringVar, filedialog
from pathlib import Path
import requests
from PIL import Image
from io import BytesIO
from collections import deque
import time

from downloader import AnimeDownloader
from utils import format_bytes, setup_logging
import config_manager

# --- La clase SettingsWindow se mantiene igual ---
class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Configuración")
        self.geometry("400x300")
        self.transient(parent)
        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text="Ruta de Descarga:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.path_var = StringVar(value=config_manager.get_default_download_path())
        ctk.CTkEntry(self, textvariable=self.path_var).grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(self, text="Calidad de Video:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.quality_var = StringVar(value=config_manager.get_default_quality())
        ctk.CTkOptionMenu(self, variable=self.quality_var, values=['1080p', '720p', '480p', 'best']).grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(self, text="Bitrate MP3:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.bitrate_var = StringVar(value=config_manager.get_default_mp3_bitrate())
        ctk.CTkOptionMenu(self, variable=self.bitrate_var, values=['320k', '192k', '128k']).grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkButton(self, text="Guardar y Cerrar", command=self.save_and_close).grid(row=3, column=0, columnspan=2, pady=20)

    def save_and_close(self):
        config_manager.save_setting('Downloader', 'default_download_path', self.path_var.get())
        config_manager.save_setting('Downloader', 'default_quality', self.quality_var.get())
        config_manager.save_setting('Audio', 'default_mp3_bitrate', self.bitrate_var.get())
        self.parent.update_defaults_from_config()
        self.destroy()

class AnimeDownloaderGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title(config_manager.get_window_title())
        self.geometry(config_manager.get_window_size())
        ctk.set_appearance_mode(config_manager.get_theme_mode())
        
        self.downloader = AnimeDownloader()
        self.download_queue = deque()
        self.cancel_event = threading.Event()
        self.is_downloading = False
        self.video_widgets = {}
        self.current_entries = [] # Para guardar la información de los videos encontrados

        # --- Layout Principal ---
        self.grid_columnconfigure(0, weight=3) # Dar más peso a la cola
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)

        # --- Frame Izquierdo (Entrada y Cola) ---
        self.left_frame = ctk.CTkFrame(self)
        self.left_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.left_frame.grid_rowconfigure(1, weight=1)
        self.left_frame.grid_columnconfigure(0, weight=1)

        self.url_frame = ctk.CTkFrame(self.left_frame)
        self.url_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.url_frame.grid_columnconfigure(0, weight=1)
        self.url_var = StringVar()
        self.url_entry = ctk.CTkEntry(self.url_frame, textvariable=self.url_var, placeholder_text="Pega una URL de video o playlist...")
        self.url_entry.grid(row=0, column=0, padx=(0,5), sticky="ew")
        self.fetch_button = ctk.CTkButton(self.url_frame, text="Buscar", width=80, command=self.fetch_url_info)
        self.fetch_button.grid(row=0, column=1)

        self.queue_frame = ctk.CTkScrollableFrame(self.left_frame, label_text="Cola de Descarga")
        self.queue_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        # --- Frame Derecho (Opciones y Previsualización) ---
        self.right_frame = ctk.CTkFrame(self)
        self.right_frame.grid(row=0, column=1, padx=(0,10), pady=10, sticky="nsew")
        self.right_frame.grid_rowconfigure(1, weight=1)
        self.right_frame.grid_columnconfigure(0, weight=1)

        self.preview_frame = ctk.CTkFrame(self.right_frame)
        self.preview_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.preview_frame.grid_columnconfigure(0, weight=1)
        self.thumbnail_label = ctk.CTkLabel(self.preview_frame, text="")
        self.thumbnail_label.grid(pady=5)
        self.preview_title_label = ctk.CTkLabel(self.preview_frame, text="Título del Video", wraplength=300)
        self.preview_title_label.grid(pady=5)
        
        self.options_frame = ctk.CTkFrame(self.right_frame)
        self.options_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.options_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self.options_frame, text="Formato:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.format_var = StringVar(value="mp4")
        ctk.CTkOptionMenu(self.options_frame, variable=self.format_var, values=['mp4', 'mkv', 'mp3', 'original']).grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        ctk.CTkLabel(self.options_frame, text="Bitrate MP3:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.mp3_bitrate_var = StringVar(value=config_manager.get_default_mp3_bitrate())
        ctk.CTkOptionMenu(self.options_frame, variable=self.mp3_bitrate_var, values=['320k', '192k', '128k']).grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        
        self.action_frame = ctk.CTkFrame(self.right_frame)
        self.action_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        self.action_frame.grid_columnconfigure((0, 1, 2), weight=1)
        self.start_button = ctk.CTkButton(self.action_frame, text="Iniciar Descargas", command=self.start_download_queue, state="disabled")
        self.start_button.grid(row=0, column=0, padx=5)
        self.cancel_button = ctk.CTkButton(self.action_frame, text="Cancelar", command=self.cancel_download, state="disabled", fg_color="#D32F2F", hover_color="#B71C1C")
        self.cancel_button.grid(row=0, column=1, padx=5)
        self.settings_button = ctk.CTkButton(self.action_frame, text="⚙️", width=40, command=self.open_settings)
        self.settings_button.grid(row=0, column=2, padx=5)
    
    def fetch_url_info(self):
        url = self.url_var.get()
        if not url: return
        self.fetch_button.configure(text="Buscando...", state="disabled")
        self.start_button.configure(state="disabled")
        for widget in self.queue_frame.winfo_children(): widget.destroy()
        self.video_widgets.clear()
        self.current_entries.clear()
        threading.Thread(target=self._fetch_info_thread, args=(url,), daemon=True).start()

    def _fetch_info_thread(self, url):
        info = self.downloader.get_video_info(url)
        self.after(0, self._populate_queue_frame, info)

    def _populate_queue_frame(self, info):
        self.fetch_button.configure(text="Buscar", state="normal")
        if info['type'] == 'error':
            self.preview_title_label.configure(text=f"Error: {info['message']}")
            return

        self.queue_frame.configure(label_text=info.get('title', 'Videos Encontrados'))
        self.current_entries = info['entries']
        
        for i, entry in enumerate(self.current_entries):
            video_frame = ctk.CTkFrame(self.queue_frame)
            video_frame.pack(fill="x", pady=5, padx=5)
            video_frame.grid_columnconfigure(1, weight=1)
            
            entry['selected'] = ctk.BooleanVar(value=True)
            ctk.CTkCheckBox(video_frame, text="", variable=entry['selected']).grid(row=0, column=0, rowspan=2, padx=5)
            
            title_label = ctk.CTkLabel(video_frame, text=entry['title'], anchor="w")
            title_label.grid(row=0, column=1, sticky="ew", padx=5)

            status_label = ctk.CTkLabel(video_frame, text=f"Duración: {time.strftime('%H:%M:%S', time.gmtime(entry['duration']))}", anchor="w", text_color="gray")
            status_label.grid(row=1, column=1, sticky="ew", padx=5)

            progress_bar = ctk.CTkProgressBar(video_frame)
            progress_bar.grid(row=0, column=2, rowspan=2, padx=5)
            progress_bar.set(0)
            
            self.video_widgets[entry['id']] = {'frame': video_frame, 'status_label': status_label, 'progress_bar': progress_bar}
            
            if i == 0: self.update_preview(entry)

        self.start_button.configure(state="normal")

    def start_download_queue(self):
        if self.is_downloading: return

        # --- LÓGICA DE COLA FUNCIONAL ---
        self.download_queue.clear()
        for entry in self.current_entries:
            if entry['selected'].get():
                task = {
                    'type': 'video', # Cada item es un video
                    'url': entry['url'],
                    'id': entry['id'],
                    'format': self.format_var.get(),
                    'audio_bitrate': self.mp3_bitrate_var.get(),
                }
                self.download_queue.append(task)
        
        if not self.download_queue:
            print("No hay videos seleccionados para descargar.")
            return

        self.is_downloading = True
        self.start_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.cancel_event.clear()
        
        # Iniciar el worker que procesará la cola
        threading.Thread(target=self._queue_worker, daemon=True).start()

    def _queue_worker(self):
        """Procesa la cola de descarga un video a la vez."""
        while self.download_queue:
            if self.cancel_event.is_set():
                print("Worker de cola cancelado.")
                break
            
            task = self.download_queue.popleft()
            self.after(0, self._update_video_status, task['id'], "Descargando...")
            self.downloader.download_task(task, self.update_progress, self.cancel_event)
            # La llamada a download_task es bloqueante, por lo que espera a que termine
            # antes de pasar al siguiente video en la cola.

        # Cuando la cola termina
        self.after(0, self.finish_downloading)

    def finish_downloading(self):
        """Se llama cuando la cola está vacía para resetear la GUI."""
        self.is_downloading = False
        self.start_button.configure(state="normal")
        self.cancel_button.configure(state="disabled")
        # Podrías añadir un mensaje de "Cola completada"
        print("Todas las descargas han finalizado.")

    def update_progress(self, data):
        self.after(0, self._update_gui_callback, data)

    def _update_gui_callback(self, data):
        video_id = data.get('video_id')
        if not video_id or video_id not in self.video_widgets: return
        
        widgets = self.video_widgets[video_id]
        status = data.get('status')
        
        if status == 'downloading':
            widgets['progress_bar'].set(data.get('percentage', 0) / 100)
            speed_str = f"{format_bytes(data.get('speed', 0))}/s"
            widgets['status_label'].configure(text=f"Descargando... {speed_str}")
        
        elif status == 'finished':
            widgets['progress_bar'].set(1)
            filename = Path(data.get('filename', '')).name
            widgets['status_label'].configure(text=f"Completado: {filename}", text_color="green")
        
        elif status == 'error':
            widgets['progress_bar'].set(0)
            widgets['status_label'].configure(text=f"Error: {data.get('error_message', 'Desconocido')}", text_color="red")

        elif status == 'cancelled':
            widgets['progress_bar'].set(0)
            widgets['status_label'].configure(text="Cancelado", text_color="yellow")

    def _update_video_status(self, video_id, message):
        """Actualiza el texto de estado para un video específico en la cola."""
        if video_id in self.video_widgets:
            self.video_widgets[video_id]['status_label'].configure(text=message, text_color="cyan")
    
    # ... (El resto de métodos se mantienen igual) ...
    def update_preview(self, entry):
        self.preview_title_label.configure(text=entry['title'])
        threading.Thread(target=self._load_thumbnail, args=(entry['thumbnail'],), daemon=True).start()

    def _load_thumbnail(self, url):
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            image_data = BytesIO(response.content)
            
            # Usar 'thumbnail' de Pillow para crear una versión más pequeña y evitar errores
            with Image.open(image_data) as img:
                img.thumbnail((320, 180)) # Reducir a un tamaño máximo de 320x180
                ctk_image = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
                self.after(0, self.thumbnail_label.configure, {"image": ctk_image})
        except Exception as e:
            print(f"No se pudo cargar la miniatura: {e}")
    
    def cancel_download(self):
        self.cancel_event.set()
        # El worker y el downloader se encargarán de parar
    
    def open_settings(self):
        SettingsWindow(self)

    def update_defaults_from_config(self):
        self.mp3_bitrate_var.set(config_manager.get_default_mp3_bitrate())
        self.downloader.quality = config_manager.get_default_quality()
        self.downloader.set_output_path(config_manager.get_default_download_path())
        print("Configuración de la GUI actualizada.")

    def run(self):
        setup_logging()
        self.update_defaults_from_config()
        self.mainloop()
