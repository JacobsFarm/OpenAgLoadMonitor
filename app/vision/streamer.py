import cv2
import threading
import time
import app.vision.ocr as ocr_logic 
import os                   
from datetime import datetime
from app.services.weight_logic import stabilizer 

# --- Parameters ---
OCR_PROCESS_INTERVAL = 4 

global_state = {
    "latest_weight_data": {"gewicht": 0},
    "current_frame": None,
    "lock": threading.Lock()
}
latest_weight_data = global_state["latest_weight_data"]

def get_video_source(config, type_key):
    if config.get('VIDEO_SOURCE_TYPE') == 'file':
        return config.get('VIDEO_SOURCE_FILE')
    return config.get('RTSP_URL_OCR') if type_key == 'OCR' else config.get('RTSP_URL_BAK')

# --- ACHTERGROND PROCES ---
def ocr_background_worker(app_config):
    print(f"--- Starten van OCR Achtergrond Thread (Interval: elke {OCR_PROCESS_INTERVAL}e frame) ---")
    
    snapshot_dir = os.path.join(os.getcwd(), 'data', 'snapshots')
    if not os.path.exists(snapshot_dir):
        try:
            os.makedirs(snapshot_dir)
        except Exception as e:
            print(f"FOUT: Kan snapshot map niet maken: {e}")

    last_snapshot_time = 0

    if ocr_logic.reader is None:
        ocr_logic.init_model(app_config)
    
    src = get_video_source(app_config, 'OCR')
    cap = cv2.VideoCapture(src)
    
    # Forceer een kleine buffer als de backend het ondersteunt (helpt tegen latency)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    frame_count = 0

    while True:
        # 1. Lees ALTIJD het frame om de buffer leeg te maken
        success, frame = cap.read()
        
        if not success:
            if app_config.get('VIDEO_SOURCE_TYPE') == 'file':
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            else:
                print("Geen beeld, opnieuw verbinden...")
                time.sleep(2)
                cap.open(src)
                continue

        frame_count += 1

        # 2. Check: Is het tijd om de AI te draaien?
        # Als de restwaarde van de deling NIET 0 is, slaan we over.
        if frame_count % OCR_PROCESS_INTERVAL != 0:
            # We doen hier niets, zodat de loop direct weer naar cap.read() gaat.
            # Dit is essentieel om de "oude" beelden uit de buffer te spoelen.
            continue

        # 3. ZWARE OPERATIES (Alleen als we door de check komen)
        if ocr_logic.reader is not None:
            # A. Detectie (Ogen)
            raw_weight, annotated_frame = ocr_logic.reader.detect_numbers(frame)
            
            # B. Logica (Brein)
            clean_weight = stabilizer.process_new_reading(raw_weight)
            
            # C. Update Globale Status
            with global_state["lock"]:
                latest_weight_data["gewicht"] = clean_weight
                # We updaten het plaatje alleen als we een nieuwe detectie hebben gedaan
                global_state["current_frame"] = annotated_frame.copy()

            # D. SNAPSHOTS OPSLAAN
            should_save = app_config.get('SAVE_SNAPSHOTS', False)
            interval = app_config.get('SNAPSHOT_INTERVAL', 20)

            if should_save:
                current_time = time.time()
                if current_time - last_snapshot_time > interval:
                    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    filename = f"snapshot_{timestamp}.jpg"
                    filepath = os.path.join(snapshot_dir, filename)
                    cv2.imwrite(filepath, frame)
                    print(f"📸 Screenshot opgeslagen: {filename}")
                    last_snapshot_time = current_time
        
        # OPMERKING: De time.sleep(0.02) is hier WEGGEHAALD.
        # cap.read() blokkeert namelijk vanzelf totdat de camera een nieuw frame heeft.
        # Extra slapen zorgt alleen maar voor meer vertraging (lag).

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
        # Voor de kijker thuis is 10 FPS (0.1s) prima voor de update van het plaatje
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
