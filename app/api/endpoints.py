from flask import Blueprint, jsonify
from app.vision.streamer import latest_weight_data

api = Blueprint('api', __name__)

@api.route('/status')
def get_status():
    # Geeft het huidige gewicht terug dat door de OCR is gelezen
    return jsonify(latest_weight_data)