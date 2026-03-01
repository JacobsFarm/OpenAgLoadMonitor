import json
import os
from flask import Blueprint, request, jsonify
from app.config import Config

# Maak een blueprint aan voor al je API routes
# LET OP: Dit heet nu 'api' in plaats van 'api_bp', zodat __init__.py het kan vinden!
api = Blueprint('api', __name__)

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
