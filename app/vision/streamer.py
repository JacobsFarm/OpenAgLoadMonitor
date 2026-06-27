import cv2
import threading
import time
import os
import sys
import numpy as np
from datetime import datetime
import app.vision.ocr as ocr_logic
from app.services.weight_logic import stabilizer

# ================= CONFIGURATION =================
FRAME_SKIP_INTERVAL = 2       
AUTO_ZOOM_ENABLED = True      
AUTO_ZOOM_TARGETS = ['monitor']
AUTO_ZOOM_SAMPLES = 20        
AUTO_ZOOM_PADDING = 15        

ENABLE_SNAPSHOTS = False     
SNAPSHOT_INTERVAL = 20        

# ================= GLOBAL STATE =================
global_state = {
    "latest_weight_data": {"gewicht": 0},
    "current_frame": None,
    "lock": threading.Lock(),
    "last_ts": 0.0,        # tijdstip van het laatste OCR-frame
    "reconnect": False     # forceer herverbinden van de OCR-bron
}

# Een frame jonger dan dit aantal seconden = "verbonden"
STREAM_FRESH_SECONDS = 5.0

latest_weight_data = global_state["latest_weight_data"]

zoom_state = {
    "locked": False,
    "coords": None,
    "candidates": [],
    "attempts": 0
}

# ================= UTILS =================

def get_bundled_path(relative_path):
    if os.path.isabs(relative_path): return relative_path
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, relative_path)
    base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(base_path, "../../", relative_path))

def get_persistent_path(relative_path):
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), relative_path)
    base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(base_path, "../../", relative_path))

def resolve_source(app_config, cam_key):
    """Bepaalt de videobron voor een camera.
    cam_key: 'cam1' | 'cam2' | 'cam_ocr'
    In 'file'-modus gebruiken alle camera's het lokale testbestand.
    """
    if app_config.get("VIDEO_SOURCE_TYPE") == "file":
        return get_bundled_path(app_config.get("VIDEO_SOURCE_FILE", "test/test_video.mp4"))
    mapping = {
        "cam1": "RTSP_URL_1",
        "cam2": "RTSP_URL_2",
        "cam_ocr": "RTSP_URL_OCR",
    }
    return app_config.get(mapping[cam_key], "")

# ================= CAMERA PASSTHROUGH STATE =================
# Laatste frame per passthrough-camera (cam1/cam2). De OCR-camera heeft zijn
# eigen geannoteerde frame in global_state["current_frame"].
camera_streams = {
    "cam1": {"frame": None, "lock": threading.Lock(), "last_ts": 0.0, "reconnect": False},
    "cam2": {"frame": None, "lock": threading.Lock(), "last_ts": 0.0, "reconnect": False},
}

# ================= WORKERS =================

def camera_passthrough_worker(app_config, cam_key):
    """Leest een camerastream (RTSP of testbestand) en bewaart steeds het nieuwste frame.
    Pure passthrough zonder YOLO, voor het live meekijken in de browser.
    """
    is_file = app_config.get("VIDEO_SOURCE_TYPE") == "file"
    source = resolve_source(app_config, cam_key)
    print(f"--- Camera passthrough '{cam_key}' verbindt met: {source} ---")

    cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # minimale buffer = zo live mogelijk

    while True:
        # Forceer-herverbinden aangevraagd (bijv. via tik op een dode tegel)?
        if camera_streams[cam_key]["reconnect"]:
            camera_streams[cam_key]["reconnect"] = False
            print(f"🔄 '{cam_key}' herverbinden op verzoek...")
            cap.release()
            cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        success, frame = cap.read()

        if not success:
            if is_file:
                # Testbestand opnieuw afspelen (loop)
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            print(f"⚠️ '{cam_key}' verloor de stream, opnieuw verbinden...")
            time.sleep(2)
            cap.open(source, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            continue

        with camera_streams[cam_key]["lock"]:
            camera_streams[cam_key]["frame"] = frame
            camera_streams[cam_key]["last_ts"] = time.time()

        # Bij een bestand op ~realtime tempo afspelen; bij RTSP zo snel mogelijk
        # de buffer leeghouden voor lage latency.
        if is_file:
            time.sleep(0.03)


def ocr_background_worker(app_config):
    print(f"--- OCR Service Started (directe bron) | Interval: {FRAME_SKIP_INTERVAL} ---")

    # Gebruik persistent path zodat de snapshots naast de .exe komen te staan
    snapshot_dir = get_persistent_path(os.path.join('data', 'snapshots'))
    os.makedirs(snapshot_dir, exist_ok=True)
    last_snapshot_time = 0

    if ocr_logic.reader is None:
        # Gebruik bundled path zodat hij het model in de exe vindt (of lokaal)
        model_p = get_bundled_path(app_config.get('YOLO_MODEL_PATH', 'weights/yolo11n.pt'))
        app_config['YOLO_MODEL_PATH'] = model_p
        ocr_logic.init_model(app_config)

    is_file = app_config.get("VIDEO_SOURCE_TYPE") == "file"
    ocr_source = resolve_source(app_config, "cam_ocr")

    print(f"Verbinden met OCR videobron: {ocr_source}")
    cap = cv2.VideoCapture(ocr_source, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    frame_count = 0

    while True:
        # Forceer-herverbinden aangevraagd?
        if global_state["reconnect"]:
            global_state["reconnect"] = False
            print("🔄 OCR-bron herverbinden op verzoek...")
            cap.release()
            cap = cv2.VideoCapture(ocr_source, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        success, full_frame = cap.read()

        if not success:
            if is_file:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # testbestand loopen
                continue
            print("⚠️ Fout bij lezen van OCR-stream, wacht even en probeer opnieuw...")
            time.sleep(2)
            cap.open(ocr_source, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            continue

        global_state["last_ts"] = time.time()

        frame_count += 1
        current_interval = 2 if (AUTO_ZOOM_ENABLED and not zoom_state["locked"]) else FRAME_SKIP_INTERVAL
        
        if frame_count % current_interval != 0:
            continue

        if ocr_logic.reader is not None:
            processing_frame = full_frame.copy()
            
            # --- Auto-Zoom Logic ---
            if AUTO_ZOOM_ENABLED:
                if not zoom_state["locked"]:
                    try:
                        box = ocr_logic.reader.find_screen_box(full_frame, AUTO_ZOOM_TARGETS)
                        if box:
                            zoom_state["candidates"].append(box)
                            
                            if len(zoom_state["candidates"]) >= AUTO_ZOOM_SAMPLES:
                                median_box = np.median(zoom_state["candidates"], axis=0).astype(int)
                                h, w, _ = full_frame.shape
                                
                                x1 = max(0, median_box[0] - AUTO_ZOOM_PADDING)
                                y1 = max(0, median_box[1] - AUTO_ZOOM_PADDING)
                                x2 = min(w, median_box[2] + AUTO_ZOOM_PADDING)
                                y2 = min(h, median_box[3] + AUTO_ZOOM_PADDING)
                                
                                if (x2 - x1) > 50 and (y2 - y1) > 50:
                                    zoom_state["coords"] = (x1, y1, x2, y2)
                                    zoom_state["locked"] = True
                                else:
                                    zoom_state["candidates"] = []
                    except Exception as e:
                        print(f"⚠️ Zoom Error: {e}")

                elif zoom_state["locked"] and zoom_state["coords"]:
                    x1, y1, x2, y2 = zoom_state["coords"]
                    processing_frame = full_frame[y1:y2, x1:x2]

            # --- Detection ---
            try:
                raw_weight, annotated_img = ocr_logic.reader.detect_numbers(processing_frame)
                clean_weight = stabilizer.process_new_reading(raw_weight)
                
                with global_state["lock"]:
                    latest_weight_data["gewicht"] = clean_weight
                    global_state["current_frame"] = annotated_img.copy()
            except Exception as e:
                pass

            # --- Snapshots ---
            if ENABLE_SNAPSHOTS:
                current_time = time.time()
                if current_time - last_snapshot_time > SNAPSHOT_INTERVAL:
                    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    cv2.imwrite(os.path.join(snapshot_dir, f"snap_{timestamp}.jpg"), full_frame)
                    last_snapshot_time = current_time

# ================= INTERFACE =================

def start_ocr_thread(app_config):
    t = threading.Thread(target=ocr_background_worker, args=(app_config,))
    t.daemon = True
    t.start()

def start_camera_threads(app_config):
    """Start de passthrough-workers voor cam1 (en cam2 indien geactiveerd)."""
    keys = ["cam1"]
    if app_config.get("ADD_SECOND_CAMERA") or app_config.get("VIDEO_SOURCE_TYPE") == "file":
        keys.append("cam2")

    for cam_key in keys:
        t = threading.Thread(target=camera_passthrough_worker, args=(app_config, cam_key))
        t.daemon = True
        t.start()

def get_stream_status():
    """Geeft per camera terug of er recent een frame binnenkwam (= verbonden)."""
    now = time.time()
    status = {}
    for key in ("cam1", "cam2"):
        ts = camera_streams[key]["last_ts"]
        status[key] = {"connected": bool(ts) and (now - ts) < STREAM_FRESH_SECONDS}
    ocr_ts = global_state.get("last_ts", 0.0)
    status["cam_ocr"] = {"connected": bool(ocr_ts) and (now - ocr_ts) < STREAM_FRESH_SECONDS}
    return status

def request_reconnect(cam_key):
    """Vraagt de betreffende worker om zijn bron (RTSP) opnieuw te openen."""
    if cam_key in camera_streams:
        camera_streams[cam_key]["reconnect"] = True
        return True
    if cam_key in ("cam_ocr", "ocr"):
        global_state["reconnect"] = True
        return True
    return False

def generate_camera_frames(cam_key):
    """MJPEG-generator voor een passthrough-camera (cam1/cam2)."""
    stream = camera_streams.get(cam_key)
    while True:
        frame = None
        if stream is not None:
            with stream["lock"]:
                if stream["frame"] is not None:
                    frame = stream["frame"]

        if frame is not None:
            try:
                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                if ret:
                    yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            except Exception:
                pass
        time.sleep(0.05)  # ~20 fps cap

def generate_ocr_frames(app_config):
    while True:
        frame = None
        with global_state["lock"]:
            if global_state["current_frame"] is not None:
                frame = global_state["current_frame"]
        
        if frame is not None:
            try:
                ret, buffer = cv2.imencode('.jpg', frame)
                if ret:
                    yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            except:
                pass
        time.sleep(0.1)
