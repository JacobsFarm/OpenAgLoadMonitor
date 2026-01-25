import cv2
import threading
import time
import app.vision.ocr as ocr_logic 
# NIEUW: Importeer je brein
from app.services.weight_logic import stabilizer 

# ... (De global_state en get_video_source functies blijven hetzelfde als in) ...
global_state = {
    "latest_weight_data": {"gewicht": 0},
    "current_frame": None,
    "lock": threading.Lock()
}
latest_weight_data = global_state["latest_weight_data"]

def get_video_source(config, type_key):
    # ... (Zelfde als voorheen) ...
    if config.get('VIDEO_SOURCE_TYPE') == 'file':
        return config.get('VIDEO_SOURCE_FILE')
    return config.get('RTSP_URL_OCR') if type_key == 'OCR' else config.get('RTSP_URL_BAK')

# --- ACHTERGROND PROCES ---
def ocr_background_worker(app_config):
    print("--- Starten van OCR Achtergrond Thread ---")
    
    if ocr_logic.reader is None:
        ocr_logic.init_model(app_config)
    
    src = get_video_source(app_config, 'OCR')
    cap = cv2.VideoCapture(src)
    
    while True:
        success, frame = cap.read()
        if not success:
            if app_config.get('VIDEO_SOURCE_TYPE') == 'file':
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            else:
                time.sleep(2)
                cap.open(src)
                continue

        if ocr_logic.reader is not None:
            # 1. HAAL RUWE DATA OP (OGEN)
            raw_weight, annotated_frame = ocr_logic.reader.detect_numbers(frame)
            
            # 2. VERWERK MET LOGICA (BREIN)
            # Hier wordt het getal "schoongemaakt" en gestabiliseerd
            clean_weight = stabilizer.process_new_reading(raw_weight)
            
            # 3. OPSLAAN (GEHEUGEN)
            with global_state["lock"]:
                latest_weight_data["gewicht"] = clean_weight
                global_state["current_frame"] = annotated_frame.copy()
        
        # Korte pauze voor 'realtime' gevoel (50fps check)
        time.sleep(0.02)

# ... (De rest van het bestand: start_ocr_thread en generate functies blijven gelijk) ...
def start_ocr_thread(app_config):
    t = threading.Thread(target=ocr_background_worker, args=(app_config,))
    t.daemon = True
    t.start()

def generate_ocr_frames(app_config):
    while True:
        frame = None
        with global_state["lock"]:
            if global_state["current_frame"] is not None:
                frame = global_state["current_frame"]
        if frame is not None:
            try:
                ret, buffer = cv2.imencode('.jpg', frame)
                if ret: yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            except: pass
        time.sleep(0.1)

def generate_bak_frames(app_config):
    src = get_video_source(app_config, 'BAK')
    cap = cv2.VideoCapture(src)
    while True:
        success, frame = cap.read()
        if not success:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue
        try:
            ret, buffer = cv2.imencode('.jpg', frame)
            if ret: yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        except: pass