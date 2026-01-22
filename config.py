import os
import json

class Config:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    
    # Path to the JSON file in F:\messpy\data\config.json
    # Navigates up from app/ folder to root, then into data/
    JSON_PATH = os.path.join(os.path.dirname(BASE_DIR), 'data', 'config.json')

    try:
        with open(JSON_PATH, 'r') as f:
            _data = json.load(f)
    except Exception:
        _data = {}

    # Settings from JSON
    SECRET_KEY = _data.get('SECRET_KEY', 'default-secret-key')
    RTSP_URL_BAK = _data.get('RTSP_URL_BAK', '')
    RTSP_URL_OCR = _data.get('RTSP_URL_OCR', '')
    AUTO_NEXT_STEP_DELAY = _data.get('AUTO_NEXT_STEP_DELAY', 5)

    # Paths
    PLANS_FOLDER = os.path.join(os.path.dirname(BASE_DIR), 'data', 'plans')
    LOGS_FOLDER = os.path.join(os.path.dirname(BASE_DIR), 'data', 'logs')
    MODEL_PATH = os.path.join(BASE_DIR, 'models', 'yolo_digits_v1.pt')
