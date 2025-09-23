#!/bin/bash

# Video Downloader - Instalación Completa
set -e

# --- Colores ---
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BLUE='\033[0;34m'; PURPLE='\033[0;35m'; CYAN='\033[0;36m'; NC='\033[0m'
log_step() { echo -e "\n${PURPLE}==> $1${NC}"; }
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }

clear
echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                🚀 Video Downloader v2.2.0 Installer          ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║ Este script configurará todo lo necesario para la aplicación.║"
echo "╚══════════════════════════════════════════════════════════════╝${NC}"

log_step "Verificando Python 3..."
if ! command -v python3 &> /dev/null; then echo -e "${RED}Python 3 no está instalado.${NC}"; exit 1; fi
if ! python3 -m pip --version &> /dev/null; then echo -e "${RED}pip para Python 3 no está instalado.${NC}"; exit 1; fi
log_success "Python 3 y pip encontrados."

VENV_DIR="venv"
log_step "Configurando entorno virtual en '$VENV_DIR'..."
if [ -d "$VENV_DIR" ]; then rm -rf "$VENV_DIR"; fi
python3 -m venv $VENV_DIR
log_success "Entorno virtual creado."

log_step "Instalando dependencias desde requirements.txt..."
if [ ! -f "requirements.txt" ]; then echo -e "${RED}No se encuentra 'requirements.txt'.${NC}"; exit 1; fi
source "$VENV_DIR/bin/activate"
pip install -r requirements.txt
deactivate
log_success "Dependencias instaladas."

RUN_SCRIPT="run.sh"
log_step "Creando script de ejecución '$RUN_SCRIPT'..."

# --- MODO NORMAL: EJECUCIÓN EN SEGUNDO PLANO ---
cat << EOF > $RUN_SCRIPT
#!/bin/bash
# Lanza la aplicación en segundo plano y libera la terminal.
echo "Lanzando la aplicación en segundo plano..."
source "\$(dirname "\$0")/$VENV_DIR/bin/activate"
nohup python -u "\$(dirname "\$0")/main.py" --gui > downloader.log 2>&1 &
echo "Aplicación lanzada. Revisa 'downloader.log' para ver los mensajes."
EOF

log_step "Finalizando instalación..."
chmod +x $RUN_SCRIPT
log_success "Permisos de ejecución asignados a '$RUN_SCRIPT'."

echo -e "\n${GREEN}╔══════════════════════════════════════════════════════════════╗"
echo -e "║                 ✅ ¡Instalación Completada!                  ║"
echo -e "╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
log_info "Para ejecutar el programa, usa el siguiente comando:"
echo -e "${YELLOW}./$RUN_SCRIPT${NC}\n"
