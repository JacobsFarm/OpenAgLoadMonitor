import os
import sys
import json
import urllib.request

def get_root_dir():
    """
    Bepaalt de hoofdmap van de applicatie. 
    Werkt correct in zowel de Python dev-omgeving als de gebouwde .exe.
    """
    if getattr(sys, 'frozen', False):
        # We draaien als .exe. Pak de map waar de .exe staat.
        return os.path.dirname(sys.executable)
    else:
        # We draaien als script (app/config.py). Ga één map omhoog naar de hoofdmap.
        return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

class Config:
    ROOT_DIR = get_root_dir()
    
    # Path to the JSON file
    JSON_PATH = os.path.join(ROOT_DIR, 'data', 'config.json')

    try:
        with open(JSON_PATH, 'r') as f:
            _data = json.load(f)
    except Exception:
        print(f"Let op: kon config niet laden vanaf {JSON_PATH}")
        _data = {}

    # Settings from JSON
    SECRET_KEY = _data.get('SECRET_KEY', 'default-secret-key')
    RTSP_URL_BAK = _data.get('RTSP_URL_BAK', '')
    RTSP_URL_OCR = _data.get('RTSP_URL_OCR', '')
    AUTO_NEXT_STEP_DELAY = _data.get('AUTO_NEXT_STEP_DELAY', 5)
    
    # Haal de download URL op (met jouw GitHub link als fallback)
    MODEL_DOWNLOAD_URL = _data.get('MODEL_DOWNLOAD_URL', 'https://github.com/JacobsFarm/OpenAgLoadMonitor/releases/download/0.1.2/agloadmonitor5m.pt')

    # Paths
    PLANS_FOLDER = os.path.join(ROOT_DIR, 'data', 'plans')
    LOGS_FOLDER = os.path.join(ROOT_DIR, 'data', 'logs')
    
    # Map voor de weights en het pad naar het model
    WEIGHTS_FOLDER = os.path.join(ROOT_DIR, 'weights')
    
    # Gebruik de naam uit je JSON of val terug op de standaard naam
    model_filename = os.path.basename(_data.get('YOLO_MODEL_PATH', 'agloadmonitor5m.pt'))
    MODEL_PATH = os.path.join(WEIGHTS_FOLDER, model_filename)

# ---> Automatische Download Logica <---
# Zodra dit bestand wordt geïmporteerd (bijv. bij het opstarten van de app),
# voeren we deze check uit.

os.makedirs(Config.WEIGHTS_FOLDER, exist_ok=True)

if not os.path.exists(Config.MODEL_PATH):
    print(f"YOLO model niet gevonden lokaal. Start download naar: {Config.MODEL_PATH} ...")
    if Config.MODEL_DOWNLOAD_URL:
        try:
            print(f"Downloaden vanaf: {Config.MODEL_DOWNLOAD_URL}")
            urllib.request.urlretrieve(Config.MODEL_DOWNLOAD_URL, Config.MODEL_PATH)
            print("✅ Model succesvol gedownload!")
        except Exception as e:
            print(f"❌ Fout tijdens het downloaden van model: {e}")
    else:
        print("❌ Fout: Geen MODEL_DOWNLOAD_URL geconfigureerd in config.json of default.")
else:
    print(f"✅ YOLO model lokaal gevonden op: {Config.MODEL_PATH}")
