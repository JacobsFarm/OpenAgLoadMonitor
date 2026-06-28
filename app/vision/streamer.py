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

def get_cameras(app_config):
    """Geeft de lijst met kijk-camera's terug als [{"name", "url"}, ...].

    Ondersteunt zowel het nieuwe CAMERAS-array als de oude
    RTSP_URL_1/RTSP_URL_2/ADD_SECOND_CAMERA-config (backward compatible),
    zodat bestaande config.json-bestanden blijven werken.
    """
    cams = app_config.get("CAMERAS")
    if isinstance(cams, list) and cams:
        return [
            {"name": c.get("name") or f"Cam {i + 1}", "url": c.get("url", "")}
            for i, c in enumerate(cams)
        ]

    # --- Fallback: oude config migreren ---
    legacy = [{"name": "Bak", "url": app_config.get("RTSP_URL_1", "")}]
    if app_config.get("ADD_SECOND_CAMERA"):
        legacy.append({"name": "Overzicht", "url": app_config.get("RTSP_URL_2", "")})
    return legacy

def cam_key_for_index(index):
    """Stabiele sleutel per camera: cam1, cam2, cam3, ..."""
    return f"cam{index + 1}"

def resolve_camera_source(app_config, cam):
    """Bepaalt de videobron voor één kijk-camera.
    In 'file'-modus gebruiken alle camera's het lokale testbestand.
    """
    if app_config.get("VIDEO_SOURCE_TYPE") == "file":
        return get_bundled_path(app_config.get("VIDEO_SOURCE_FILE", "test/test_video.mp4"))
    return cam.get("url", "")

def resolve_ocr_source(app_config):
    """Bepaalt de videobron voor de OCR-camera (display-uitlezing)."""
    if app_config.get("VIDEO_SOURCE_TYPE") == "file":
        return get_bundled_path(app_config.get("VIDEO_SOURCE_FILE", "test/test_video.mp4"))
    return app_config.get("RTSP_URL_OCR", "")

# ================= CAMERA PASSTHROUGH STATE =================
# Laatste frame per passthrough-camera. Wordt dynamisch opgebouwd in
# start_camera_threads() op basis van de CAMERAS-array uit de config.
# De OCR-camera heeft zijn eigen geannoteerde frame in
# global_state["current_frame"] en staat dus niet in deze dict.
camera_streams = {}

def _make_stream_state():
    return {"frame": None, "lock": threading.Lock(), "last_ts": 0.0, "reconnect": False}

# ================= WORKERS =================

def camera_passthrough_worker(app_config, cam_key, source):
    """Leest een camerastream (RTSP of testbestand) en bewaart steeds het nieuwste frame.
    Pure passthrough zonder YOLO, voor het live meekijken in de browser.
    """
    is_file = app_config.get("VIDEO_SOURCE_TYPE") == "file"
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
        # Het model wordt NIET in de exe gebundeld maar bij de eerste start
        # gedownload naast de exe (zie config.py / MODEL_DOWNLOAD_URL). Gebruik
        # daarom het persistente pad, niet het tijdelijke bundle-pad.
        model_p = get_persistent_path(app_config.get('YOLO_MODEL_PATH', 'weights/agloadmonitor5m.pt'))
        app_config['YOLO_MODEL_PATH'] = model_p
        ocr_logic.init_model(app_config)

    is_file = app_config.get("VIDEO_SOURCE_TYPE") == "file"
    ocr_source = resolve_ocr_source(app_config)

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
    """Start één passthrough-worker per kijk-camera uit de CAMERAS-array."""
    cams = get_cameras(app_config)

    # camera_streams in-place opbouwen (zelfde object blijft gedeeld met routes/api)
    camera_streams.clear()
    for i, cam in enumerate(cams):
        cam_key = cam_key_for_index(i)
        camera_streams[cam_key] = _make_stream_state()

        source = resolve_camera_source(app_config, cam)
        t = threading.Thread(
            target=camera_passthrough_worker,
            args=(app_config, cam_key, source),
        )
        t.daemon = True
        t.start()

    # OCR-camera ook als kijk-tegel tonen terwijl de OCR-detectie UIT staat?
    # (Met OCR aan komt het geannoteerde beeld al via /video_feed_ocr.)
    if app_config.get("SHOW_OCR_IN_CAMERAS") and not app_config.get("OCR_ENABLED", True):
        camera_streams["cam_ocr"] = _make_stream_state()
        ocr_source = resolve_ocr_source(app_config)
        t = threading.Thread(
            target=camera_passthrough_worker,
            args=(app_config, "cam_ocr", ocr_source),
        )
        t.daemon = True
        t.start()

def get_stream_status():
    """Geeft per camera terug of er recent een frame binnenkwam (= verbonden)."""
    now = time.time()
    status = {}
    for key, stream in camera_streams.items():
        ts = stream["last_ts"]
        status[key] = {"connected": bool(ts) and (now - ts) < STREAM_FRESH_SECONDS}
    # OCR-detectiecamera: alleen apart rapporteren als hij niet al als
    # passthrough-tegel draait (anders dubbel/overschreven).
    if "cam_ocr" not in status:
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
