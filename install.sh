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

# Usamos 'cat' con un 'heredoc' para escribir el contenido en el archivo.
# Este es el bloque modificado que combina la lógica de ambos scripts.
cat << EOF > $RUN_SCRIPT
#!/bin/bash

# Directorio del script para asegurar que las rutas relativas funcionen correctamente.
SCRIPT_DIR="\$(dirname "\$0")"

# Activa el entorno virtual.
source "\${SCRIPT_DIR}/${VENV_DIR}/bin/activate"

echo "Lanzando la aplicación en segundo plano..."
echo "Los registros se guardarán en: \${SCRIPT_DIR}/downloader.log"

# --- EJECUCIÓN EN SEGUNDO PLANO ---
# 'nohup' hace que el proceso ignore la señal de cierre de la terminal.
# 'python -u' deshabilita el búfer de salida, lo que es bueno para los logs.
# '> downloader.log 2>&1' redirige stdout y stderr al archivo de log.
# '&' ejecuta el comando en segundo plano.
nohup python -u "\${SCRIPT_DIR}/main.py" --gui > "\${SCRIPT_DIR}/downloader.log" 2>&1 &

# Captura el Process ID (PID) del último comando ejecutado en segundo plano.
PID=\$!

echo "La aplicación se está ejecutando con PID: \$PID"
echo "Puedes cerrar esta terminal. Para detener la aplicación, usa: kill \$PID"

EOF

# Hacer el script ejecutable
chmod +x $RUN_SCRIPT
echo -e "${GREEN}Script de ejecución '${RUN_SCRIPT}' creado con éxito.${NC}"


# --- Mensaje final ---
echo -e "\n${GREEN}¡Instalación completada!${NC}"
echo -e "Para ejecutar el programa en segundo plano, usa el siguiente comando:"
echo -e "${YELLOW}./${RUN_SCRIPT}${NC}\n"
