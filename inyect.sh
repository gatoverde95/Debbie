#!/bin/bash

# Detectar idioma del sistema
LANGUAGE=$(echo $LANG | cut -d'_' -f1)

# Decidir qué script ejecutar para el idioma
if [ "$LANGUAGE" == "es" ]; then
    echo "Idioma detectado: Español"
    LANG_SCRIPT="/usr/share/debbie/debbie.py"
elif [ "$LANGUAGE" == "en" ]; then
    echo "Detected language: English"
    LANG_SCRIPT="/usr/share/debbie/pylang/debbie_en.py"
else
    echo "Idioma no soportado: $LANGUAGE"
    # Establecer un script por defecto (español)
    LANG_SCRIPT="/usr/share/debbie/debbie.py"
fi

# Verificar si se proporcionó un archivo .deb
if [ -z "$1" ]; then
    echo "No se proporcionó un archivo .deb. Ejecutando solo el script de idioma..."
    python3 "$LANG_SCRIPT"
else
    DEB_FILE="$1"
    if [[ "$DEB_FILE" =~ \.deb$ ]]; then
        echo "Pasando el archivo .deb a Python para instalación: $DEB_FILE"
        # Ejecutar el script Python y pasar el archivo .deb como argumento
        python3 "$LANG_SCRIPT" "$DEB_FILE"
    else
        echo "El archivo proporcionado no es un paquete .deb válido."
        python3 "$LANG_SCRIPT"
    fi
fi

