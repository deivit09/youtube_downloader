#!/bin/bash

# --- Colores para los mensajes ---
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # Sin color

echo -e "${GREEN}Iniciando el instalador del Video Downloader...${NC}"

# --- 1. Verificar si Python 3 está instalado ---
echo -e "\n${YELLOW}Paso 1: Verificando la instalación de Python 3...${NC}"
if ! command -v python3 &> /dev/null
then
    echo -e "${RED}ERROR: Python 3 no está instalado. Por favor, instálalo para continuar.${NC}"
    exit 1
fi
if ! python3 -m pip --version &> /dev/null
then
    echo -e "${RED}ERROR: pip para Python 3 no está instalado. Por favor, instálalo (ej. 'sudo apt install python3-pip').${NC}"
    exit 1
fi
echo -e "${GREEN}Python 3 y pip encontrados.${NC}"


# --- 2. Crear un entorno virtual ---
VENV_DIR="venv"
echo -e "\n${YELLOW}Paso 2: Creando entorno virtual en la carpeta '${VENV_DIR}'...${NC}"

if [ -d "$VENV_DIR" ]; then
    echo -e "El directorio del entorno virtual '${VENV_DIR}' ya existe. Saltando creación."
else
    python3 -m venv $VENV_DIR
    if [ $? -ne 0 ]; then
        echo -e "${RED}ERROR: No se pudo crear el entorno virtual.${NC}"
        exit 1
    fi
fi
echo -e "${GREEN}Entorno virtual creado/verificado con éxito.${NC}"


# --- 3. Instalar dependencias ---
echo -e "\n${YELLOW}Paso 3: Instalando dependencias desde requirements.txt...${NC}"

if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}ERROR: No se encuentra el archivo 'requirements.txt'. Asegúrate de que esté en el mismo directorio.${NC}"
    exit 1
fi

# Usar el pip del entorno virtual para instalar los paquetes
$VENV_DIR/bin/pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo -e "${RED}ERROR: Falló la instalación de dependencias.${NC}"
    exit 1
fi
echo -e "${GREEN}Dependencias instaladas correctamente.${NC}"


# --- 4. Crear el script de ejecución ---
RUN_SCRIPT="run.sh"
echo -e "\n${YELLOW}Paso 4: Creando el script de ejecución '${RUN_SCRIPT}'...${NC}"

# Usamos 'cat' con un 'heredoc' para escribir el contenido en el archivo
cat << EOF > $RUN_SCRIPT
#!/bin/bash

# Activa el entorno virtual
source "$(dirname "\$0")/${VENV_DIR}/bin/activate"

# Ejecuta la aplicación de Python
python "$(dirname "\$0")/app.py"

# Desactiva el entorno virtual al cerrar (opcional, buena práctica)
deactivate
EOF

# Hacer el script ejecutable
chmod +x $RUN_SCRIPT
echo -e "${GREEN}Script de ejecución '${RUN_SCRIPT}' creado.${NC}"


# --- Mensaje final ---
echo -e "\n${GREEN}¡Instalación completada!${NC}"
echo -e "Para ejecutar el programa, simplemente usa el siguiente comando:"
echo -e "${YELLOW}./${RUN_SCRIPT}${NC}\n"
