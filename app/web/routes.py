from flask import Blueprint, render_template, Response, current_app
# We importeren alleen nog de OCR frame-generator voor debug doeleinden
from app.vision.streamer import generate_ocr_frames

main = Blueprint('main', __name__)

@main.route('/')
def index():
    # Laadt de hoofd HTML pagina
    return render_template('index.html', gewicht=0, stap="Wachten", doel=0)

# --- Route: OCR Camera (Optioneel) ---
# Gebruik deze om in een apart tabblad te debuggen of de getallen goed gelezen worden
@main.route('/video_feed_ocr')
def video_feed_ocr():
    return Response(generate_ocr_frames(current_app.config),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

