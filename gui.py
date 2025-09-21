# gui.py
import customtkinter as ctk
import threading
from tkinter import StringVar, filedialog
from pathlib import Path

from downloader import AnimeDownloader
from utils import format_bytes, setup_logging
import config_manager

class AnimeDownloaderGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Descargador de Videos")
        self.geometry("700x520")
        ctk.set_appearance_mode(config_manager.get_theme_mode())
        
        self.font_main = (config_manager.get_font_family(), 14)
        self.font_bold = (config_manager.get_font_family(), 16, "bold")
        self.grid_columnconfigure(0, weight=1)

        self.downloader = AnimeDownloader()
        self.download_path_var = StringVar(value=self.downloader.output_path)
        self.cancel_event = threading.Event()

        # --- Widgets ---
        self.title_label = ctk.CTkLabel(self, text="Descargador y Convertidor de Videos", font=self.font_bold)
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        self.url_var = StringVar()
        self.url_entry = ctk.CTkEntry(self, textvariable=self.url_var, placeholder_text="Pega aquí la URL del video...", font=self.font_main)
        self.url_entry.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        # Ruta de descarga...
        self.path_frame = ctk.CTkFrame(self)
        self.path_frame.grid(row=2, column=0, padx=20, pady=5, sticky="ew")
        self.path_frame.grid_columnconfigure(1, weight=1)
        self.path_label = ctk.CTkLabel(self.path_frame, text="Guardar en:", font=self.font_main)
        self.path_label.grid(row=0, column=0, padx=(10, 5), pady=5, sticky="w")
        self.path_entry = ctk.CTkEntry(self.path_frame, textvariable=self.download_path_var, font=self.font_main)
        self.path_entry.grid(row=0, column=1, padx=(0, 10), pady=5, sticky="ew")
        self.browse_button = ctk.CTkButton(self.path_frame, text="Examinar", command=self.browse_path, font=("Arial", 12), width=100)
        self.browse_button.grid(row=0, column=2, padx=(0, 10), pady=5)


        # Opciones de conversión...
        self.conversion_frame = ctk.CTkFrame(self)
        self.conversion_frame.grid(row=3, column=0, padx=20, pady=10)
        self.conversion_label = ctk.CTkLabel(self.conversion_frame, text="Formato de Salida:", font=self.font_main)
        self.conversion_label.pack(side="left", padx=(10, 5), pady=5)
        self.conversion_var = StringVar(value="none")
        self.radio_none = ctk.CTkRadioButton(self.conversion_frame, text="Original", variable=self.conversion_var, value="none")
        self.radio_none.pack(side="left", padx=5, pady=5)
        self.radio_mp4 = ctk.CTkRadioButton(self.conversion_frame, text="MP4", variable=self.conversion_var, value="mp4")
        self.radio_mp4.pack(side="left", padx=5, pady=5)
        self.radio_mp3 = ctk.CTkRadioButton(self.conversion_frame, text="MP3 (Solo Audio)", variable=self.conversion_var, value="mp3")
        self.radio_mp3.pack(side="left", padx=5, pady=5)

        # Frame para los botones de acción
        self.action_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.action_frame.grid(row=4, column=0, padx=20, pady=10)
        self.action_frame.grid_columnconfigure((0, 1), weight=1)

        self.download_button = ctk.CTkButton(self.action_frame, text="Descargar", command=self.start_download, font=self.font_bold)
        self.download_button.grid(row=0, column=0, padx=5)

        self.cancel_button = ctk.CTkButton(self.action_frame, text="Cancelar y Salir", command=self.cancel_and_exit, font=self.font_bold, fg_color="#D32F2F", hover_color="#B71C1C")
        self.cancel_button.grid(row=0, column=1, padx=5)
        self.cancel_button.configure(state="disabled")

        # Widgets de Progreso...
        self.progress_bar = ctk.CTkProgressBar(self, orientation="horizontal", mode="determinate")
        self.progress_bar.grid(row=5, column=0, padx=20, pady=10, sticky="ew")
        self.status_label = ctk.CTkLabel(self, text="Bienvenido. Elige una opción y pega una URL.", font=self.font_main, wraplength=650)
        self.status_label.grid(row=6, column=0, padx=20, pady=(0, 20))

    def start_download(self):
        url = self.url_var.get()
        if not url:
            self.status_label.configure(text="Error: Por favor, ingresa una URL.")
            return

        self.cancel_event.clear()
        self.download_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.progress_bar.set(0)
        self.status_label.configure(text="Iniciando descarga...")
        
        convert_to = self.conversion_var.get()
        
        download_thread = threading.Thread(
            target=self.downloader.download_episode_safe,
            args=(url, self.update_progress, convert_to, self.cancel_event),
            daemon=True  # <-- CAMBIO 1: Hacemos el hilo un "daemon"
        )
        download_thread.start()

    def cancel_and_exit(self):
        """Activa el evento de cancelación y cierra la aplicación."""
        # <-- CAMBIO 2: La función ahora simplemente destruye la ventana
        self.cancel_event.set() # Avisa al hilo (buena práctica)
        self.destroy()        # Cierra la ventana y, como el hilo es daemon, todo termina.

    def _update_gui_callback(self, data):
        status = data.get('status')
        
        if status == 'downloading':
            percentage = data.get('percentage', 0)
            self.progress_bar.set(percentage / 100)
            downloaded_str = format_bytes(data.get('downloaded_bytes', 0))
            total_str = format_bytes(data.get('total_bytes', 0))
            speed_str = f"{format_bytes(data.get('speed', 0))}/s"
            self.status_label.configure(text=f"{percentage:.1f}% de {total_str}  •  {speed_str}")

        elif status == 'converting':
            self.status_label.configure(text=f"Convirtiendo...")
            self.progress_bar.configure(mode='indeterminate')
            self.progress_bar.start()

        elif status == 'finished' or status == 'error' or status == 'cancelled':
            self.progress_bar.stop()
            self.progress_bar.configure(mode='determinate')
            self.download_button.configure(state="normal")
            self.cancel_button.configure(state="disabled")

            if status == 'finished':
                self.progress_bar.set(1)
                filename_clean = Path(data.get('filename', 'video.mp4')).name
                self.status_label.configure(text=f"¡Éxito! Guardado como: {filename_clean}")
            elif status == 'error':
                self.progress_bar.set(0)
                self.status_label.configure(text=f"Error: {data.get('error_message', 'Desconocido')}")
            elif status == 'cancelled':
                self.progress_bar.set(0)
                self.status_label.configure(text="Descarga cancelada por el usuario.")

    def browse_path(self):
        selected_path = filedialog.askdirectory(initialdir=self.download_path_var.get())
        if selected_path:
            self.download_path_var.set(selected_path)
            self.downloader.set_output_path(selected_path)

    def update_progress(self, data):
        self.after(0, self._update_gui_callback, data)

    def run(self):
        setup_logging()
        self.mainloop()
