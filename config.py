import json
import os

CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as file:
            return json.load(file)
    return {"language": "es"}  # Idioma por defecto: español

def save_config(config):
    with open(CONFIG_FILE, "w") as file:
        json.dump(config, file)

# Cargar configuración inicial
config = load_config()