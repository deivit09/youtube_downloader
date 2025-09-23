# main.py
import argparse
import sys
from pathlib import Path
from downloader import DownloaderEngine # <-- NOMBRE CAMBIADO
from config import Config
from utils import setup_logging, validate_url

def main():
    parser = argparse.ArgumentParser(description='Descarga videos desde diferentes sitios web.')
    parser.add_argument('-u', '--url', type=str, help='URL del video o playlist a descargar')
    parser.add_argument('-q', '--quality', type=str, default=Config.DEFAULT_QUALITY, choices=['480p', '720p', '1080p', 'best'], help=f'Calidad (default: {Config.DEFAULT_QUALITY})')
    parser.add_argument('-o', '--output', type=str, default=Config.DOWNLOAD_PATH, help=f'Directorio de descarga (default: {Config.DOWNLOAD_PATH})')
    parser.add_argument('--gui', action='store_true', help='Abrir interfaz gráfica')
    parser.add_argument('--list-sites', action='store_true', help='Listar sitios soportados por yt-dlp')
    parser.add_argument('--version', action='version', version='Video Downloader v2.0.0')
    args = parser.parse_args()
    setup_logging()

    print("Video Downloader v2.0.0")

    if args.list_sites:
        print("Este programa usa yt-dlp, que soporta cientos de sitios.")
        print("Para una lista completa, visita: https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md")
        return

    if args.gui:
        try:
            from gui import AppGUI # <-- NOMBRE CAMBIADO
            app = AppGUI()
            app.run()
        except ImportError as e:
            print(f"Error al cargar la GUI: {e}")
            sys.exit(1)
        return

    if not args.url:
        parser.print_help()
        sys.exit(1)

    # Lógica de descarga CLI (simplificada)
    downloader = DownloaderEngine(output_path=str(args.output))
    task = {'url': args.url, 'quality': args.quality, 'format': 'mp4'}
    print(f"Iniciando descarga de {args.url} en calidad {args.quality}...")
    downloader.download_task(task, lambda d: print(d), __import__('threading').Event())

if __name__ == "__main__":
    main()
