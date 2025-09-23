# config_manager.py
import configparser
from pathlib import Path

config = configparser.ConfigParser()
config.read('config.ini')

# --- Theme ---
def get_theme_mode(): return config.get('Theme', 'mode', fallback='Dark')
def get_color_theme(): return config.get('Theme', 'color_theme', fallback='blue')
def get_font_family(): return config.get('Theme', 'font_family', fallback='Arial')

# --- Window ---
def get_window_title(): return config.get('Window', 'title', fallback='Video Downloader Pro')

def get_window_size():
    width = config.getint('Window', 'default_width', fallback=800)
    height = config.getint('Window', 'default_height', fallback=600)
    return f"{width}x{height}"

# --- Downloader ---
def get_default_quality(): return config.get('Downloader', 'default_quality', fallback='720p')
def get_default_download_path():
    path_str = config.get('Downloader', 'default_download_path', fallback='~/descargas')
    return str(Path(path_str).expanduser())

# --- Audio ---
def get_default_mp3_bitrate(): return config.get('Audio', 'default_mp3_bitrate', fallback='192k')

# --- Guardar ---
def save_setting(section, key, value):
    if not config.has_section(section): config.add_section(section)
    config.set(section, key, str(value))
    with open('config.ini', 'w') as configfile:
        config.write(configfile)
