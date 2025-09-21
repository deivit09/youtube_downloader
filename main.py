#!/usr/bin/env python3
"""
Anime Downloader - Aplicación principal extendida (Fixed)
Permite descargar episodios de anime desde múltiples sitios incluyendo JKAnime
"""

import argparse
import sys
import os
from pathlib import Path

try:
    from downloader_extended import ExtendedAnimeDownloader as AnimeDownloader
    EXTENDED_MODE = True
except ImportError:
    from downloader import AnimeDownloader
    EXTENDED_MODE = False

from config import Config
from utils import setup_logging, validate_url, clean_filename

def main():
    """Función principal del programa"""
    parser = argparse.ArgumentParser(
        description='Descarga episodios de anime desde diferentes sitios web incluyendo JKAnime',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  # YouTube
  python main.py -u "https://www.youtube.com/watch?v=VIDEO_ID" -q 720p
  
  # JKAnime
  python main.py -u "https://jkanime.net/dandadan-2nd-season/12/" -q 720p
  
  # Interfaz gráfica
  python main.py --gui
  
  # Listar sitios soportados
  python main.py --list-sites
        """
    )
    
    parser.add_argument(
        '-u', '--url',
        type=str,
        help='URL del episodio de anime a descargar'
    )
    
    parser.add_argument(
        '-q', '--quality',
        type=str,
        default=Config.DEFAULT_QUALITY,
        choices=['480p', '720p', '1080p', 'best'],
        help=f'Calidad de descarga (default: {Config.DEFAULT_QUALITY})'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=str,
        default=Config.DOWNLOAD_PATH,
        help=f'Directorio de descarga (default: {Config.DOWNLOAD_PATH})'
    )
    
    parser.add_argument(
        '--gui',
        action='store_true',
        help='Abrir interfaz gráfica'
    )
    
    parser.add_argument(
        '--list-sites',
        action='store_true',
        help='Listar sitios web soportados'
    )
    
    parser.add_argument(
        '--info',
        action='store_true',
        help='Solo obtener información del video, no descargar'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Mostrar información detallada'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version=f'Anime Downloader v1.0.0 {"(Extended)" if EXTENDED_MODE else "(Standard)"}'
    )
    
    args = parser.parse_args()
    
    # Configurar logging
    setup_logging(verbose=args.verbose)
    
    # Mostrar modo
    mode_text = "🚀 MODO EXTENDIDO" if EXTENDED_MODE else "📺 MODO ESTÁNDAR"
    print(f"🎌 Anime Downloader v1.0.0 - {mode_text}")
    
    # Listar sitios soportados
    if args.list_sites:
        list_supported_sites()
        return
    
    # Si se especifica GUI, lanzar interfaz gráfica
    if args.gui:
        try:
            from gui import AnimeDownloaderGUI
            app = AnimeDownloaderGUI()
            app.run()
        except ImportError as e:
            print(f"Error: No se pudo cargar la interfaz gráfica: {e}")
            print("Instala las dependencias necesarias: pip install tkinter")
            sys.exit(1)
        return
    
    # Validar argumentos requeridos para CLI
    if not args.url:
        print("Error: Se requiere una URL para descargar.")
        print("Usa --help para ver las opciones disponibles o --list-sites para ver sitios soportados.")
        sys.exit(1)
    
    # Validar URL
    if not validate_url(args.url):
        print(f"Error: URL inválida: {args.url}")
        sys.exit(1)
    
    # Crear directorio de descarga si no existe
    output_path = Path(args.output).expanduser().resolve()
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"📥 URL: {args.url}")
    print(f"🎥 Calidad: {args.quality}")
    print(f"📂 Destino: {output_path}")
    print("-" * 50)
    
    # Inicializar downloader con parámetros correctos según el tipo
    if EXTENDED_MODE:
        # ExtendedAnimeDownloader solo acepta estos parámetros
        downloader = AnimeDownloader(
            output_path=str(output_path),
            quality=args.quality,
            max_retries=Config.MAX_RETRIES
        )
    else:
        # AnimeDownloader estándar acepta concurrent_downloads
        downloader = AnimeDownloader(
            output_path=str(output_path),
            quality=args.quality,
            max_retries=Config.MAX_RETRIES,
            concurrent_downloads=1
        )
    
    # Verificar qué tipo de sitio es (solo en modo extendido)
    if EXTENDED_MODE and hasattr(downloader, 'can_handle_url'):
        extractor_name = downloader.can_handle_url(args.url)
        if extractor_name:
            print(f"🎌 Sitio detectado: {extractor_name.upper()}")
        else:
            print("📺 Sitio estándar detectado")
    
    try:
        # Solo obtener información si se solicita
        if args.info:
            print("ℹ️  Obteniendo información del video...")
            info = downloader.get_video_info(args.url)
            
            if info:
                print("\n📋 INFORMACIÓN DEL VIDEO:")
                print(f"  Título: {info.get('title', 'N/A')}")
                print(f"  Uploader: {info.get('uploader', 'N/A')}")
                print(f"  Duración: {info.get('duration', 0)} segundos")
                print(f"  Fuente: {info.get('source', 'N/A')}")
                
                if EXTENDED_MODE and 'video_urls_count' in info:
                    print(f"  URLs encontradas: {info['video_urls_count']}")
                
                if info.get('description'):
                    desc = info['description'][:200]
                    print(f"  Descripción: {desc}{'...' if len(info['description']) > 200 else ''}")
            else:
                print("❌ No se pudo obtener información del video")
                sys.exit(1)
            return
        
        # Realizar descarga
        print("🚀 Iniciando descarga...")
        success = downloader.download_episode(args.url)
        
        if success:
            print("✅ Descarga completada exitosamente!")
            print(f"📁 Archivo guardado en: {output_path}")
        else:
            print("❌ Error en la descarga. Revisa los logs para más detalles.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Descarga cancelada por el usuario.")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

def list_supported_sites():
    """Lista todos los sitios web soportados"""
    print("🌐 SITIOS WEB SOPORTADOS:\n")
    
    if EXTENDED_MODE:
        try:
            # Crear downloader con parámetros correctos
            downloader = AnimeDownloader()
            supported = downloader.list_supported_sites()
            
            print("🎌 SITIOS DE ANIME ESPECÍFICOS:")
            if supported['custom_extractors']:
                for site in supported['custom_extractors']:
                    if site == 'jkanime':
                        print("  ✅ JKAnime (jkanime.net)")
                        print("      - Ejemplo: https://jkanime.net/dandadan-2nd-season/12/")
                    else:
                        print(f"  ✅ {site}")
            else:
                print("  ❌ Ningún extractor personalizado disponible")
            
            print("\n📺 SITIOS ESTÁNDAR (via yt-dlp):")
            for site in supported['standard']:
                print(f"  ✅ {site}")
                
        except Exception as e:
            print(f"❌ Error listando sitios: {e}")
    else:
        print("📺 SITIOS ESTÁNDAR (via yt-dlp):")
        standard_sites = [
            'youtube.com', 'youtu.be', 'vimeo.com',
            'dailymotion.com', 'twitch.tv', 'facebook.com',
            'twitter.com', 'instagram.com', 'tiktok.com'
        ]
        
        for site in standard_sites:
            print(f"  ✅ {site}")
        
        print("\n⚠️  Para soporte de sitios de anime específicos:")
        print("   Instala los extractores personalizados creando:")
        print("   - extractors/jkanime.py")
        print("   - downloader_extended.py")
    
    # Mostrar número de extractores de manera segura
    if EXTENDED_MODE:
        try:
            downloader = AnimeDownloader()
            num_extractors = len(getattr(downloader, 'custom_extractors', {}))
            print(f"\n💡 Total de extractores personalizados: {num_extractors}")
        except:
            print(f"\n💡 Total de extractores personalizados: 0")
    else:
        print(f"\n💡 Total de extractores personalizados: 0")
    
    print("💡 Para más sitios, revisa: https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md")

if __name__ == "__main__":
    main()
