from flask import Blueprint, Response, current_app, send_from_directory
import os
import sys
from app.vision.streamer import generate_ocr_frames, generate_camera_frames

main = Blueprint('main', __name__)

def get_frontend_dir():
    """Bepaalt de juiste map voor de frontend, of het nu dev of de gecompileerde .exe is."""
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, 'frontend', 'dist')
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '../../frontend/dist'))

FRONTEND_DIST_DIR = get_frontend_dir()

@main.route('/')
@main.route('/config')
def index():
    return send_from_directory(FRONTEND_DIST_DIR, 'index.html')

@main.route('/assets/<path:path>')
def serve_assets(path):
    return send_from_directory(os.path.join(FRONTEND_DIST_DIR, 'assets'), path)

@main.route('/rootCA.pem')
def root_ca():
    """Download de lokale root-CA om op de telefoon te installeren (voor de PWA).
    Wordt als .crt aangeboden zodat Android het herkent als te installeren CA."""
    cert_dir = os.path.join(os.getcwd(), 'data', 'certs')
    if os.path.isfile(os.path.join(cert_dir, 'rootCA.pem')):
        return send_from_directory(
            cert_dir, 'rootCA.pem',
            mimetype='application/x-x509-ca-cert',
            as_attachment=True,
            download_name='AgLoadMonitor-CA.crt',
        )
    return "Certificaat nog niet aangemaakt — zet HTTPS aan en herstart de app.", 404

@main.route('/<path:path>')
def serve_root_files(path):
    dist_path = os.path.join(FRONTEND_DIST_DIR, path)
    if os.path.isfile(dist_path):
        return send_from_directory(FRONTEND_DIST_DIR, path)
    # SPA-fallback: onbekende routes (bv. /settings) horen bij de Svelte-app.
    # Geef index.html terug i.p.v. 404, anders krijg je een wit scherm.
    return send_from_directory(FRONTEND_DIST_DIR, 'index.html')

@main.route('/video_feed_ocr')
def video_feed_ocr():
    return Response(generate_ocr_frames(current_app.config),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@main.route('/video_feed_cam/<cam_key>')
def video_feed_cam(cam_key):
    """MJPEG-stream voor een willekeurige kijk-camera (cam1, cam2, cam3, ...)."""
    return Response(generate_camera_frames(cam_key),
                    mimetype='multipart/x-mixed-replace; boundary=frame')
