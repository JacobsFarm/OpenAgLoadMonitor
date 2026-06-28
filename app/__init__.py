import os
import json
from flask import Flask

DEFAULT_CONFIG = {
    "SECRET_KEY": "change-me",
    "CAMERAS": [
        {"name": "Camera 1", "url": ""}
    ],
    "RTSP_URL_OCR": "",
    "OCR_ENABLED": True,
    "SHOW_OCR_IN_CAMERAS": False,
    "VIDEO_SOURCE_TYPE": "file",
    "VIDEO_SOURCE_FILE": "test/test_video.mp4",
    "YOLO_MODEL_PATH": "weights/agloadmonitor5m.pt",
    "MODEL_DOWNLOAD_URL": "https://github.com/JacobsFarm/OpenAgLoadMonitor/releases/download/0.1.2/agloadmonitor5m.pt",
    "CONFIDENCE_THRESHOLD": 0.5,
    "STREAM_LAYOUT": "vertical",
    "AUTO_OPEN_BROWSER": True,
    "KIOSK_MODE": False,
    "USE_HTTPS": False
}

def ensure_config(config_path):
    """Maakt een standaard config.json aan als die nog niet bestaat (bv. eerste start van de exe)."""
    if not os.path.exists(config_path):
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        print(f"ℹ️ Standaard config.json aangemaakt op {config_path}")

def create_app():
    app = Flask(__name__)

    # 1. Config Laden (default aanmaken indien nodig)
    base_dir = os.getcwd()
    config_path = os.path.join(base_dir, 'data', 'config.json')
    ensure_config(config_path)
    try:
        with open(config_path, 'r') as f:
            app.config.update(json.load(f))
    except FileNotFoundError:
        print("Config niet gevonden!")

    # 2. Blueprints
    from app.web.routes import main
    app.register_blueprint(main)

    from app.api.endpoints import api
    app.register_blueprint(api, url_prefix='/api')

    # 3. Start de achtergrond-threads (OCR + camera passthrough)
    from app.vision.streamer import start_ocr_thread, start_camera_threads
    # Alleen starten in het hoofdproces (niet in de debug-reloader child)
    if os.environ.get('WERKZEUG_RUN_MAIN') or __name__ == 'app':
        if app.config.get('OCR_ENABLED', True):
            print("Starten van OCR- en camera-services...")
            start_ocr_thread(app.config)
        else:
            print("OCR uitgeschakeld (OCR_ENABLED=false) — alleen camera-services starten.")
        start_camera_threads(app.config)

    return app
