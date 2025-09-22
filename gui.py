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

# La clase SettingsWindow se mantiene igual
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
        ctk.CTkOptionMenu(self, variable=self.quality_var, values=['best', '1080p', '720p', '480p']).grid(row=1, column=1, padx=10, pady=5, sticky="ew")

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
        self.tab_data = {} # Para guardar datos por pestaña

        # --- Layout Principal ---
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)

        # --- Frame Izquierdo (Pestañas de Historial) ---
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

        # --- NUEVO: SISTEMA DE PESTAÑAS PARA EL HISTORIAL ---
        self.tab_view = ctk.CTkTabview(self.left_frame)
        self.tab_view.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.tab_view.add("Bienvenido") # Pestaña inicial

        # --- Frame Derecho (Opciones y Previsualización) ---
        self.right_frame = ctk.CTkFrame(self)
        self.right_frame.grid(row=0, column=1, padx=(0,10), pady=10, sticky="nsew")
        self.right_frame.grid_rowconfigure(1, weight=1)
        self.right_frame.grid_columnconfigure(0, weight=1)
        # ... (resto de widgets sin cambios estructurales) ...
        self.preview_frame = ctk.CTkFrame(self.right_frame)
        self.preview_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.preview_frame.grid_columnconfigure(0, weight=1)
        self.thumbnail_label = ctk.CTkLabel(self.preview_frame, text="")
        self.thumbnail_label.grid(pady=5)
        self.preview_title_label = ctk.CTkLabel(self.preview_frame, text="Busca una URL para empezar", wraplength=300)
        self.preview_title_label.grid(pady=5)
        
        self.options_frame = ctk.CTkFrame(self.right_frame)
        self.options_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.options_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(self.options_frame, text="Calidad Video:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.quality_var = StringVar(value=config_manager.get_default_quality())
        ctk.CTkOptionMenu(self.options_frame, variable=self.quality_var, values=['best', '1080p', '720p', '480p']).grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(self.options_frame, text="Formato Salida:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.format_var = StringVar(value="mp4")
        ctk.CTkOptionMenu(self.options_frame, variable=self.format_var, values=['mp4', 'mkv', 'mp3', 'original']).grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(self.options_frame, text="Bitrate MP3:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.mp3_bitrate_var = StringVar(value=config_manager.get_default_mp3_bitrate())
        ctk.CTkOptionMenu(self.options_frame, variable=self.mp3_bitrate_var, values=['320k', '192k', '128k']).grid(row=2, column=1, padx=10, pady=5, sticky="ew")
        
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
        threading.Thread(target=self._fetch_info_thread, args=(url,), daemon=True).start()

    def _fetch_info_thread(self, url):
        info = self.downloader.get_video_info(url)
        self.after(0, self._populate_new_tab, info)

    def _populate_new_tab(self, info):
        self.fetch_button.configure(text="Buscar", state="normal")
        if info['type'] == 'error':
            self.preview_title_label.configure(text=f"Error: {info['message']}")
            return

        tab_name = info.get('title', 'Resultados')[:30] # Acortar nombre de la pestaña
        try:
            self.tab_view.add(tab_name)
            self.tab_view.set(tab_name)
        except Exception: # Si la pestaña ya existe, la seleccionamos
            self.tab_view.set(tab_name)
            for widget in self.tab_view.tab(tab_name).winfo_children(): widget.destroy()

        current_tab = self.tab_view.tab(tab_name)
        current_tab.grid_rowconfigure(1, weight=1)
        current_tab.grid_columnconfigure(0, weight=1)
        
        # Guardar los datos de esta pestaña
        tab_entries = info['entries']
        self.tab_data[tab_name] = tab_entries

        # Frame de acciones (Seleccionar/Deseleccionar)
        actions_frame = ctk.CTkFrame(current_tab)
        actions_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        ctk.CTkButton(actions_frame, text="Seleccionar Todos", command=lambda: self.toggle_all_checkboxes(tab_name, True)).pack(side="left", padx=5)
        ctk.CTkButton(actions_frame, text="Deseleccionar Todos", command=lambda: self.toggle_all_checkboxes(tab_name, False)).pack(side="left", padx=5)

        # ScrollFrame para la lista de videos
        scroll_frame = ctk.CTkScrollableFrame(current_tab)
        scroll_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        for i, entry in enumerate(tab_entries):
            video_frame = ctk.CTkFrame(scroll_frame)
            video_frame.pack(fill="x", pady=5, padx=5)
            video_frame.grid_columnconfigure(1, weight=1)
            
            entry['selected'] = ctk.BooleanVar(value=False) # <-- CORREGIDO: Desmarcado por defecto
            ctk.CTkCheckBox(video_frame, text="", variable=entry['selected']).grid(row=0, column=0, rowspan=2, padx=5)
            
            title_label = ctk.CTkLabel(video_frame, text=entry['title'], anchor="w")
            title_label.grid(row=0, column=1, sticky="ew", padx=5)
            status_label = ctk.CTkLabel(video_frame, text=f"Duración: {time.strftime('%M:%S', time.gmtime(entry['duration']))}", anchor="w", text_color="gray")
            status_label.grid(row=1, column=1, sticky="ew", padx=5)
            progress_bar = ctk.CTkProgressBar(video_frame)
            progress_bar.grid(row=0, column=2, rowspan=2, padx=5)
            progress_bar.set(0)
            
            self.video_widgets[entry['id']] = {'frame': video_frame, 'status_label': status_label, 'progress_bar': progress_bar}
            
            if i == 0: self.update_preview(entry)

        self.start_button.configure(state="normal")
        # --- ARREGLO SCROLL RUEDA RATÓN ---
        self.bind_all("<MouseWheel>", lambda event: self._on_mouse_wheel(event), add="+")

    def _on_mouse_wheel(self, event):
        # Redirige el evento de scroll a la lista si el cursor está sobre ella
        # Esta es una solución simple, puede necesitar ajustes
        pass # CustomTkinter a menudo maneja esto mejor que Tkinter estándar, verificar si es necesario

    def toggle_all_checkboxes(self, tab_name, select):
        if tab_name in self.tab_data:
            for entry in self.tab_data[tab_name]:
                entry['selected'].set(select)

    def start_download_queue(self):
        if self.is_downloading: return
        
        current_tab_name = self.tab_view.get()
        if not current_tab_name or current_tab_name not in self.tab_data:
            return

        self.download_queue.clear()
        for entry in self.tab_data[current_tab_name]:
            if entry['selected'].get():
                task = {
                    'url': entry['url'], 'id': entry['id'],
                    'format': self.format_var.get(),
                    'quality': self.quality_var.get(),
                    'audio_bitrate': self.mp3_bitrate_var.get(),
                }
                self.download_queue.append(task)
        
        if not self.download_queue: return

        self.is_downloading = True
        self.start_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.cancel_event.clear()
        threading.Thread(target=self._queue_worker, daemon=True).start()

    def _queue_worker(self):
        while self.download_queue:
            if self.cancel_event.is_set(): break
            task = self.download_queue.popleft()
            self.after(0, self._update_video_status, task['id'], "En cola...")
            self.downloader.download_task(task, self.update_progress, self.cancel_event)
        self.after(0, self.finish_downloading)

    def finish_downloading(self):
        self.is_downloading = False
        self.start_button.configure(state="normal")
        self.cancel_button.configure(state="disabled")

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
            widgets['status_label'].configure(text=f"Completado", text_color="green")
        elif status in ['error', 'cancelled']:
            widgets['progress_bar'].set(0)
            color = "yellow" if status == 'cancelled' else "red"
            msg = "Cancelado" if status == 'cancelled' else "Error"
            widgets['status_label'].configure(text=msg, text_color=color)

    # El resto de métodos se mantienen igual o con cambios menores...
    def update_defaults_from_config(self):
        self.quality_var.set(config_manager.get_default_quality())
        self.mp3_bitrate_var.set(config_manager.get_default_mp3_bitrate())

    def open_settings(self):
        SettingsWindow(self)

    def update_preview(self, entry):
        self.preview_title_label.configure(text=entry['title'])
        threading.Thread(target=self._load_thumbnail, args=(entry.get('thumbnail'),), daemon=True).start()

    def _load_thumbnail(self, url):
        if not url: return
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            with Image.open(BytesIO(response.content)) as img:
                img.thumbnail((320, 180))
                ctk_image = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
                self.after(0, self.thumbnail_label.configure, {"image": ctk_image, "text": ""})
        except Exception as e:
            self.after(0, self.thumbnail_label.configure, {"image": None, "text": "Miniatura no disponible"})
            print(f"No se pudo cargar la miniatura: {e}")
    
    def cancel_download(self): self.cancel_event.set()
    def _update_video_status(self, video_id, message):
        if video_id in self.video_widgets:
            self.video_widgets[video_id]['status_label'].configure(text=message, text_color="cyan")
    
    def run(self):
        setup_logging()
        self.update_defaults_from_config()
        self.mainloop()
