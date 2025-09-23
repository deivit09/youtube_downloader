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

from downloader import DownloaderEngine
from utils import format_bytes, setup_logging
import config_manager

# --- La clase SettingsWindow se mantiene sin cambios ---
class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent); self.parent = parent; self.title("Configuración"); self.geometry("400x300"); self.transient(parent); self.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self, text="Ruta de Descarga:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.path_var = StringVar(value=config_manager.get_default_download_path()); ctk.CTkEntry(self, textvariable=self.path_var).grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        ctk.CTkLabel(self, text="Calidad de Video:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.quality_var = StringVar(value=config_manager.get_default_quality()); ctk.CTkOptionMenu(self, variable=self.quality_var, values=['best', '1080p', '720p', '480p']).grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        ctk.CTkLabel(self, text="Bitrate MP3:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.bitrate_var = StringVar(value=config_manager.get_default_mp3_bitrate()); ctk.CTkOptionMenu(self, variable=self.bitrate_var, values=['320k', '192k', '128k']).grid(row=2, column=1, padx=10, pady=5, sticky="ew")
        ctk.CTkButton(self, text="Guardar y Cerrar", command=self.save_and_close).grid(row=3, column=0, columnspan=2, pady=20)
    def save_and_close(self):
        config_manager.save_setting('Downloader', 'default_download_path', self.path_var.get()); config_manager.save_setting('Downloader', 'default_quality', self.quality_var.get()); config_manager.save_setting('Audio', 'default_mp3_bitrate', self.bitrate_var.get())
        self.parent.update_defaults_from_config(); self.destroy()

class AppGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(config_manager.get_window_title()); self.geometry(config_manager.get_window_size()); ctk.set_appearance_mode(config_manager.get_theme_mode())
        self.downloader = DownloaderEngine(); self.download_queue = deque(); self.cancel_event = threading.Event(); self.is_downloading = False; self.video_widgets = {}; self.tab_data = {}
        self.total_queue_size = 0; self.completed_in_queue = 0; self.total_queue_duration = 0
        self.grid_columnconfigure(0, weight=3); self.grid_columnconfigure(1, weight=2); self.grid_rowconfigure(0, weight=1)
        self.left_frame = ctk.CTkFrame(self); self.left_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew"); self.left_frame.grid_rowconfigure(1, weight=1); self.left_frame.grid_columnconfigure(0, weight=1)
        self.url_frame = ctk.CTkFrame(self.left_frame); self.url_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew"); self.url_frame.grid_columnconfigure(0, weight=1)
        self.url_var = StringVar(); self.url_entry = ctk.CTkEntry(self.url_frame, textvariable=self.url_var, placeholder_text="Pega una URL de video o playlist..."); self.url_entry.grid(row=0, column=0, padx=(0,5), sticky="ew")
        self.fetch_button = ctk.CTkButton(self.url_frame, text="Buscar", width=80, command=self.fetch_url_info); self.fetch_button.grid(row=0, column=1, padx=(0,5))
        self.fetch_progress = ctk.CTkProgressBar(self.url_frame, mode="indeterminate")
        self.tab_view_container = ctk.CTkFrame(self.left_frame, fg_color="transparent"); self.tab_view_container.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.no_tabs_label = ctk.CTkLabel(self.tab_view_container, text="Realiza una búsqueda para ver los resultados.", font=("Arial", 16), text_color="gray"); self.no_tabs_label.pack(expand=True, padx=20, pady=20)
        self.tab_view = ctk.CTkTabview(self.tab_view_container)
        self.right_frame = ctk.CTkFrame(self); self.right_frame.grid(row=0, column=1, padx=(0,10), pady=10, sticky="nsew"); self.right_frame.grid_rowconfigure(1, weight=1); self.right_frame.grid_columnconfigure(0, weight=1)
        self.preview_frame = ctk.CTkFrame(self.right_frame); self.preview_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew"); self.preview_frame.grid_columnconfigure(0, weight=1)
        self.thumbnail_label = ctk.CTkLabel(self.preview_frame, text="", height=180); self.thumbnail_label.grid(pady=5)
        self.preview_title_label = ctk.CTkLabel(self.preview_frame, text="Pasa el ratón sobre un video para previsualizar", wraplength=300); self.preview_title_label.grid(pady=5)
        self.options_frame = ctk.CTkFrame(self.right_frame); self.options_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew"); self.options_frame.grid_columnconfigure(1, weight=1)
        self.format_var = StringVar(value="mp4"); self.format_var.trace_add("write", self._on_format_change)
        ctk.CTkLabel(self.options_frame, text="Formato Salida:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        ctk.CTkOptionMenu(self.options_frame, variable=self.format_var, values=['mp4', 'mkv', 'mp3', 'wav', 'original']).grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        self.quality_label = ctk.CTkLabel(self.options_frame, text="Calidad Video:")
        self.quality_var = StringVar(value=config_manager.get_default_quality()); self.quality_menu = ctk.CTkOptionMenu(self.options_frame, variable=self.quality_var, values=['best', '1080p', '720p', '480p'])
        self.bitrate_label = ctk.CTkLabel(self.options_frame, text="Bitrate Audio:")
        self.mp3_bitrate_var = StringVar(value=config_manager.get_default_mp3_bitrate()); self.bitrate_menu = ctk.CTkOptionMenu(self.options_frame, variable=self.mp3_bitrate_var, values=['320k', '192k', '128k'])
        self.global_status_frame = ctk.CTkFrame(self.right_frame); self.global_status_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        self.global_status_label = ctk.CTkLabel(self.global_status_frame, text="Progreso de la cola: 0 de 0", anchor="w"); self.global_status_label.pack(pady=5, padx=10, fill="x")
        self.action_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent"); self.action_frame.grid(row=3, column=0, padx=10, pady=10, sticky="ew")
        btn_inner_frame = ctk.CTkFrame(self.action_frame, fg_color="transparent"); btn_inner_frame.pack()
        self.start_button = ctk.CTkButton(btn_inner_frame, text="Iniciar Descargas", command=self.start_download_queue, state="disabled"); self.start_button.pack(side="left", padx=5)
        self.cancel_button = ctk.CTkButton(btn_inner_frame, text="Cancelar", command=self.cancel_download, state="disabled", fg_color="#D32F2F", hover_color="#B71C1C"); self.cancel_button.pack(side="left", padx=5)
        self.settings_button = ctk.CTkButton(btn_inner_frame, text="⚙️", width=40, command=self.open_settings); self.settings_button.pack(side="left", padx=5)
        self.quit_button = ctk.CTkButton(btn_inner_frame, text="Salir", width=60, command=self.destroy, fg_color="gray"); self.quit_button.pack(side="left", padx=5)
        self.bind_all("<MouseWheel>", self._on_mouse_wheel, add="+"); self.bind_all("<Button-4>", self._on_mouse_wheel, add="+"); self.bind_all("<Button-5>", self._on_mouse_wheel, add="+")
        self._on_format_change()

    def _on_format_change(self, *args):
        fmt = self.format_var.get(); self.quality_label.grid_forget(); self.quality_menu.grid_forget(); self.bitrate_label.grid_forget(); self.bitrate_menu.grid_forget()
        if fmt == 'mp4': self.quality_label.grid(row=1, column=0, padx=10, pady=5, sticky="w"); self.quality_menu.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        elif fmt in ['mp3', 'wav']: self.bitrate_label.grid(row=1, column=0, padx=10, pady=5, sticky="w"); self.bitrate_menu.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

    def fetch_url_info(self):
        url = self.url_var.get()
        if not url: return
        self.fetch_button.configure(state="disabled"); self.fetch_progress.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(5,0)); self.fetch_progress.start()
        threading.Thread(target=self._fetch_info_thread, args=(url,), daemon=True).start()

    def _fetch_info_thread(self, url):
        info = self.downloader.get_video_info(url)
        self.after(0, self._populate_new_tab, info)

    def _populate_new_tab(self, info):
        self.fetch_progress.stop(); self.fetch_progress.grid_forget(); self.fetch_button.configure(state="normal")
        if info['type'] == 'error': self.preview_title_label.configure(text=f"Error: {info['message']}"); return
        if self.no_tabs_label.winfo_exists(): self.no_tabs_label.pack_forget()
        self.tab_view.pack(expand=True, fill="both")
        first_entry_id = info['entries'][0].get('id', str(time.time())[-5:])
        tab_name = f"{info.get('title', 'Resultados')[:25]}... [{first_entry_id}]"
        self.tab_view.add(tab_name); self.tab_view.set(tab_name)
        current_tab = self.tab_view.tab(tab_name)
        current_tab.grid_rowconfigure(1, weight=1); current_tab.grid_columnconfigure(0, weight=1)
        self.tab_data[tab_name] = info['entries']
        actions_frame = ctk.CTkFrame(current_tab); actions_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        ctk.CTkButton(actions_frame, text="Seleccionar Todos", command=lambda tn=tab_name: self.toggle_all_checkboxes(tn, True)).pack(side="left", padx=5)
        ctk.CTkButton(actions_frame, text="Deseleccionar Todos", command=lambda tn=tab_name: self.toggle_all_checkboxes(tn, False)).pack(side="left", padx=5)
        ctk.CTkButton(actions_frame, text="Cerrar Pestaña [X]", command=lambda tn=tab_name: self.close_current_tab(tn), fg_color="gray").pack(side="right", padx=5)
        scroll_frame = ctk.CTkScrollableFrame(current_tab); scroll_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        for i, entry in enumerate(self.tab_data[tab_name]):
            video_frame = ctk.CTkFrame(scroll_frame); video_frame.pack(fill="x", pady=5, padx=5); video_frame.grid_columnconfigure(1, weight=1)
            entry['selected'] = ctk.BooleanVar(value=False)
            ctk.CTkCheckBox(video_frame, text="", variable=entry['selected']).grid(row=0, column=0, rowspan=2, padx=5)
            title_label = ctk.CTkLabel(video_frame, text=entry['title'], anchor="w"); title_label.grid(row=0, column=1, sticky="ew", padx=5)
            status_label = ctk.CTkLabel(video_frame, text=f"Duración: {self.format_duration(entry['duration'])}", anchor="w", text_color="gray"); status_label.grid(row=1, column=1, sticky="ew", padx=5)
            progress_bar = ctk.CTkProgressBar(video_frame); progress_bar.set(0); progress_bar.grid(row=0, column=2, rowspan=2, padx=5)
            self.video_widgets[entry['id']] = {'frame': video_frame, 'status_label': status_label, 'progress_bar': progress_bar}
            video_frame.bind("<Enter>", lambda e, en=entry: self.update_preview(en)); [w.bind("<Enter>", lambda e, en=entry: self.update_preview(en)) for w in video_frame.winfo_children()]
            if i == 0: self.update_preview(entry)
        self.start_button.configure(state="normal")

    def start_download_queue(self):
        if self.is_downloading: return
        self.download_queue.clear()
        self.total_queue_duration = 0 # <-- Resetear duración total
        for tab_name, entries in self.tab_data.items():
            for entry in entries:
                if entry.get('selected') and entry['selected'].get():
                    task = {'url': entry['url'], 'id': entry['id'], 'format': self.format_var.get(), 'quality': self.quality_var.get(), 'audio_bitrate': self.mp3_bitrate_var.get()}
                    self.download_queue.append(task)
                    self.total_queue_duration += entry.get('duration', 0) # <-- Sumar duración
                    # --- CORRECCIÓN: Marcar como "En cola" inmediatamente ---
                    self._update_video_status(entry['id'], "En cola...")
        
        if not self.download_queue: return
        self.total_queue_size = len(self.download_queue); self.completed_in_queue = 0
        self.update_global_status() # <-- Actualizar estado global inicial
        self.is_downloading = True; self.start_button.configure(state="disabled"); self.cancel_button.configure(state="normal"); self.cancel_event.clear()
        self._process_next_in_queue()

    def _process_next_in_queue(self):
        if self.cancel_event.is_set() or not self.download_queue:
            self.after(0, self.finish_downloading); return
        task = self.download_queue[0]
        threading.Thread(target=self.downloader.download_task, args=(task, self.update_progress, self.cancel_event), daemon=True).start()

    def update_progress(self, data):
        status = data.get('status')
        if status in ['finished', 'error', 'cancelled']:
            task = self.download_queue.popleft() # Quitar el que acaba de terminar
            entry = self.find_entry_by_id(task['id'])
            if entry: self.total_queue_duration -= entry.get('duration', 0) # Restar duración
            if status == 'finished': self.completed_in_queue += 1
            self.after(0, self.update_global_status)
            self.after(100, self._process_next_in_queue)
        self.after(0, self._update_gui_callback, data)

    def _update_gui_callback(self, data):
        video_id = data.get('video_id')
        if not video_id or video_id not in self.video_widgets: return
        widgets, status = self.video_widgets[video_id], data.get('status')
        if status == 'downloading':
            widgets['progress_bar'].set(data.get('percentage', 0) / 100)
            eta = data.get('eta', 0)
            eta_str = f"({self.format_duration(eta)} restante)" if eta and eta > 0 else ""
            widgets['status_label'].configure(text=f"Descargando... {eta_str}")
        elif status == 'finished':
            widgets['progress_bar'].set(1); widgets['status_label'].configure(text="Completado", text_color="green")
        elif status in ['error', 'cancelled']:
            widgets['progress_bar'].set(0); color = "yellow" if status == 'cancelled' else "red"
            widgets['status_label'].configure(text="Cancelado" if status == 'cancelled' else "Error", text_color=color)

    def finish_downloading(self):
        self.is_downloading = False; self.start_button.configure(state="normal"); self.cancel_button.configure(state="disabled")
        self.global_status_label.configure(text=f"Cola finalizada. {self.completed_in_queue} de {self.total_queue_size} completados.")
    
    # --- FUNCIONES DE UTILIDAD Y OTROS MÉTODOS ---
    def update_global_status(self):
        """Actualiza la etiqueta de estado global con el progreso y tiempo restante."""
        duration_str = self.format_duration(self.total_queue_duration, long=True)
        self.global_status_label.configure(text=f"Progreso: {self.completed_in_queue} de {self.total_queue_size} | Tiempo restante: ~{duration_str}")
        
    def find_entry_by_id(self, video_id):
        """Busca un video en todas las pestañas por su ID."""
        for tab_name, entries in self.tab_data.items():
            for entry in entries:
                if entry.get('id') == video_id:
                    return entry
        return None

    def format_duration(self, seconds, long=False):
        if not isinstance(seconds, (int, float)) or seconds < 0: return "00:00"
        seconds = int(seconds)
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if long and hours > 0: return f"{hours}h {minutes:02d}m {seconds:02d}s"
        elif long: return f"{minutes:02d}m {seconds:02d}s"
        else: return f"{minutes:02d}:{seconds:02d}"

    def _on_mouse_wheel(self, event):
        widget_under_mouse = self.winfo_containing(event.x_root, event.y_root)
        scrollable_frame = widget_under_mouse
        while scrollable_frame is not None and not isinstance(scrollable_frame, ctk.CTkScrollableFrame):
            scrollable_frame = scrollable_frame.master
        if scrollable_frame:
            delta = -1 if (hasattr(event, 'delta') and event.delta > 0) or (hasattr(event, 'num') and event.num == 4) else 1
            scrollable_frame._parent_canvas.yview_scroll(delta, "units")
    
    def update_preview(self, entry):
        self.preview_title_label.configure(text=entry['title'])
        threading.Thread(target=self._load_thumbnail, args=(entry.get('thumbnail'),), daemon=True).start()

    def _load_thumbnail(self, url):
        if not url: self.after(0, lambda: self.thumbnail_label.configure(image=None, text="Miniatura no disponible")); return
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}; response = requests.get(url, stream=True, timeout=5, headers=headers); response.raise_for_status()
            with Image.open(BytesIO(response.content)) as img:
                img.thumbnail((320, 180))
                ctk_image = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
                self.after(0, self._update_thumbnail_widget, ctk_image)
        except Exception: self.after(0, lambda: self.thumbnail_label.configure(image=None, text="Miniatura no disponible"))
    def _update_thumbnail_widget(self, ctk_image):
        self.thumbnail_label.configure(image=ctk_image, text=""); self.thumbnail_label.image = ctk_image
    
    def toggle_all_checkboxes(self, tab_name, select):
        if tab_name in self.tab_data:
            for entry in self.tab_data[tab_name]:
                if 'selected' in entry: entry['selected'].set(select)
    def close_current_tab(self, tab_name):
        if tab_name in self.tab_data: del self.tab_data[tab_name]
        try: self.tab_view.delete(tab_name)
        except Exception: pass
        if not self.tab_view.winfo_children():
            self.tab_view.pack_forget(); self.no_tabs_label.pack(expand=True, padx=20, pady=20)
            self.start_button.configure(state="disabled")
    def open_settings(self): SettingsWindow(self)
    def update_defaults_from_config(self): self.quality_var.set(config_manager.get_default_quality()); self.mp3_bitrate_var.set(config_manager.get_default_mp3_bitrate())
    def cancel_download(self): self.cancel_event.set()
    def _update_video_status(self, video_id, message):
        if video_id in self.video_widgets: self.video_widgets[video_id]['status_label'].configure(text=message, text_color="cyan")
    def run(self):
        setup_logging(); self.update_defaults_from_config(); self.mainloop()
