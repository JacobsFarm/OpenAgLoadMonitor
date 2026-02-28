import cv2
import threading
import time
import os
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
    "lock": threading.Lock()
}

latest_weight_data = global_state["latest_weight_data"]

zoom_state = {
    "locked": False,
    "coords": None,
    "candidates": [],
    "attempts": 0
}

# ================= UTILS =================

def get_absolute_path(relative_path):
    if os.path.isabs(relative_path):
        return relative_path
    base_path = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(base_path, "../../"))
    return os.path.join(project_root, relative_path)

# ================= WORKERS =================

def ocr_background_worker(app_config):
    print(f"--- OCR Service Started (Go2rtc RTSP) | Interval: {FRAME_SKIP_INTERVAL} ---")
    
    snapshot_dir = get_absolute_path(os.path.join('data', 'snapshots'))
    os.makedirs(snapshot_dir, exist_ok=True)
    last_snapshot_time = 0

    if ocr_logic.reader is None:
        model_p = get_absolute_path(app_config.get('YOLO_MODEL_PATH'))
        app_config['YOLO_MODEL_PATH'] = model_p
        ocr_logic.init_model(app_config)
    
    # We luisteren nu naar de interne, supersnelle Go2rtc RTSP stream!
    go2rtc_rtsp_url = "rtsp://127.0.0.1:8554/cam_ocr"
    
    # Forceer de FFMPEG backend en zet de buffer op 1 voor zo min mogelijk vertraging
    print(f"Verbinden met OCR videostream: {go2rtc_rtsp_url}")
    cap = cv2.VideoCapture(go2rtc_rtsp_url, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    frame_count = 0

    while True:
        success, full_frame = cap.read()
        
        if not success:
            print("⚠️ Fout bij lezen van Go2rtc RTSP stream, wacht even en probeer opnieuw...")
            time.sleep(2)
            cap.open(go2rtc_rtsp_url, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            continue

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

def generate_ocr_frames(app_config):
    """Blijft behouden voor als je de OCR bounding boxes in je browser wilt debuggen via /video_feed_ocr"""
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
