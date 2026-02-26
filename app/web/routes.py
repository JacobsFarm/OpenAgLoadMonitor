from flask import Blueprint, render_template, Response, current_app
# Importeer nu alle drie de frame-generators uit je streamer
from app.vision.streamer import generate_bak_frames, generate_ocr_frames, generate_cam2_frames

main = Blueprint('main', __name__)

@main.route('/')
def index():
    # Laadt de hoofd HTML pagina
    return render_template('index.html', gewicht=0, stap="Wachten", doel=0)

# --- Route 1: Camera 1 (Gekoppeld aan RTSP_URL_1) ---
# De naam video_feed_bak wordt behouden omdat je HTML deze aanroept
@main.route('/video_feed_cam1')
def video_feed_bak():
    return Response(generate_bak_frames(current_app.config),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# --- Route 2: Camera 2 (Gekoppeld aan RTSP_URL_2) ---
# Dit is de nieuwe route voor de optionele tweede camera
@main.route('/video_feed_cam2')
def video_feed_cam2():
    return Response(generate_cam2_frames(current_app.config),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# --- Route 3: OCR Camera ---
# Gebruik deze om te debuggen of de getallen goed gelezen worden
@main.route('/video_feed_ocr')
def video_feed_ocr():
    return Response(generate_ocr_frames(current_app.config),
                    mimetype='multipart/x-mixed-replace; boundary=frame')
