import configparser

# Inicializa el parser de configuración
config = configparser.ConfigParser()
config.read('config.ini')

# --- Funciones para obtener los valores de configuración ---

def get_theme_mode():
    """Obtiene el modo del tema (Dark/Light)."""
    return config.get('Theme', 'mode', fallback='Dark')

def get_color_theme():
    """Obtiene el color del tema (blue/dark-blue/green)."""
    return config.get('Theme', 'color_theme', fallback='blue')

def get_font_family():
    """Obtiene la fuente de la aplicación."""
    return config.get('Theme', 'font_family', fallback='Arial')

def get_window_title():
    """Obtiene el título de la ventana."""
    return config.get('Window', 'title', fallback='Video Downloader')

def get_window_size():
    """Obtiene las dimensiones de la ventana."""
    width = config.getint('Window', 'default_width', fallback=700)
    height = config.getint('Window', 'default_height', fallback=350)
    return f"{width}x{height}"
