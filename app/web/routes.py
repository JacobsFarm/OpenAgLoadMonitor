from flask import Blueprint, Response, current_app, send_from_directory
import os
from app.vision.streamer import generate_ocr_frames

main = Blueprint('main', __name__)

# Bepaal het absolute pad naar de Svelte 'dist' map.
# Omdat dit bestand in 'app/web/' staat, gaan we twee mappen omhoog ('../../')
FRONTEND_DIST_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../frontend/dist'))

@main.route('/')
def index():
    # Serveer de hoofd HTML van de Svelte app
    return send_from_directory(FRONTEND_DIST_DIR, 'index.html')

@main.route('/assets/<path:path>')
def serve_assets(path):
    # Serveer de Javascript en CSS bestanden die Svelte heeft gegenereerd
    return send_from_directory(os.path.join(FRONTEND_DIST_DIR, 'assets'), path)

@main.route('/<path:path>')
def serve_root_files(path):
    # Serveer eventuele extra bestanden in de root (zoals een favicon of Vite manifest)
    dist_path = os.path.join(FRONTEND_DIST_DIR, path)
    if os.path.exists(dist_path):
        return send_from_directory(FRONTEND_DIST_DIR, path)
    return "Bestand niet gevonden", 404

# --- Route: OCR Camera (Optioneel) ---
# Blijft behouden om in een apart tabblad te debuggen of getallen goed gelezen worden
@main.route('/video_feed_ocr')
def video_feed_ocr():
    return Response(generate_ocr_frames(current_app.config),
                    mimetype='multipart/x-mixed-replace; boundary=frame')
