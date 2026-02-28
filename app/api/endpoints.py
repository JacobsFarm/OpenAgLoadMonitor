from flask import Blueprint, jsonify
from app.vision.streamer import latest_weight_data

api = Blueprint('api', __name__)

@api.route('/status')
def get_status():
    # Zorg dat we altijd een dictionary hebben om mee te werken
    data = latest_weight_data if latest_weight_data else {}
    
    # We bouwen het JSON-antwoord op. Als 'gewicht', 'stap' of 'doel' niet 
    # in latest_weight_data staan, geven we veilige standaardwaarden mee.
    response_data = {
        "gewicht": data.get("gewicht", 0),
        "stap": data.get("stap", "Wachten"),
        "doel": data.get("doel", 0)
    }
    
    return jsonify(response_data)
