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

@main.route('/<path:path>')
def serve_root_files(path):
    dist_path = os.path.join(FRONTEND_DIST_DIR, path)
    if os.path.exists(dist_path):
        return send_from_directory(FRONTEND_DIST_DIR, path)
    return "Bestand niet gevonden", 404

@main.route('/video_feed_ocr')
def video_feed_ocr():
    return Response(generate_ocr_frames(current_app.config),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@main.route('/video_feed_cam/<cam_key>')
def video_feed_cam(cam_key):
    """MJPEG-stream voor een willekeurige kijk-camera (cam1, cam2, cam3, ...)."""
    return Response(generate_camera_frames(cam_key),
                    mimetype='multipart/x-mixed-replace; boundary=frame')
