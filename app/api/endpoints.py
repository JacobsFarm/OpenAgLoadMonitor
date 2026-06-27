import json
import os
from flask import Blueprint, request, jsonify
from app.config import Config
from app.vision.streamer import get_stream_status, request_reconnect, latest_weight_data

# Maak een blueprint aan voor al je API routes
# LET OP: Dit heet nu 'api' in plaats van 'api_bp', zodat __init__.py het kan vinden!
api = Blueprint('api', __name__)

@api.route('/status', methods=['GET'])
def status():
    """Laatste (gestabiliseerde) gewichtswaarde voor het dashboard."""
    return jsonify(latest_weight_data)

@api.route('/stream_status', methods=['GET'])
def stream_status():
    """Per camera: verbonden of niet (gebruikt door de frontend voor de status-indicator)."""
    return jsonify(get_stream_status())

@api.route('/reconnect/<cam_key>', methods=['POST'])
def reconnect(cam_key):
    """Forceer de backend om de RTSP-bron van een camera opnieuw te openen."""
    ok = request_reconnect(cam_key)
    if ok:
        return jsonify({"message": f"Herverbinden aangevraagd voor {cam_key}"})
    return jsonify({"error": f"Onbekende camera: {cam_key}"}), 404

@api.route('/config', methods=['GET'])
def get_config():
    """Haal de actuele configuratie op uit config.json"""
    try:
        with open(Config.JSON_PATH, 'r') as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": f"Kan configuratie niet laden: {str(e)}"}), 500

@api.route('/config', methods=['POST'])
def save_config():
    """Sla de nieuwe of gewijzigde instellingen op"""
    try:
        new_config_data = request.json
        
        # Lees eerst de oude data, zodat we geen bestaande ongewijzigde keys weggooien
        if os.path.exists(Config.JSON_PATH):
            with open(Config.JSON_PATH, 'r') as f:
                data = json.load(f)
        else:
            data = {}
            
        # Werk de dictionary bij met de nieuwe waarden uit Svelte
        data.update(new_config_data)
        
        # Schrijf het netjes terug naar data/config.json
        with open(Config.JSON_PATH, 'w') as f:
            json.dump(data, f, indent=4)
            
        return jsonify({"message": "Configuratie succesvol opgeslagen", "config": data})
    except Exception as e:
        return jsonify({"error": f"Fout bij opslaan: {str(e)}"}), 500
