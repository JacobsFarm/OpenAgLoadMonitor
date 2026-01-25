from flask import Blueprint, render_template, Response, current_app
# Importeer nu beide functies
from app.vision.streamer import generate_bak_frames, generate_ocr_frames

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('index.html', gewicht=0, stap="Wachten", doel=0)

# --- Route 1: Voor de Bak (Lading) ---
# Gebruik deze in je <img> tag als je de bak wilt zien
@main.route('/video_feed_bak')
def video_feed_bak():
    return Response(generate_bak_frames(current_app.config),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# --- Route 2: Voor de OCR (Monitor) ---
# Gebruik deze om te debuggen of de getallen goed gelezen worden
@main.route('/video_feed_ocr')
def video_feed_ocr():
    return Response(generate_ocr_frames(current_app.config),
                    mimetype='multipart/x-mixed-replace; boundary=frame')