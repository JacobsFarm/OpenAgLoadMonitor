import cv2
import numpy as np
from ultralytics import YOLO
import os

class DigitalReadout:
    def __init__(self, model_path):
        print(f"Laden van YOLO model: {model_path}")
        self.model = YOLO(model_path)
        # LET OP: Alle stabilisatie variabelen zijn hier nu weggehaald!

    def detect_numbers(self, frame):
        """
        Voert puur de detectie uit.
        Geeft terug: (ruw_getal, plaatje)
        """
        results = self.model.predict(frame, conf=0.5, verbose=False)
        
        detections = []

        # 1. Haal resultaten op
        for r in results:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                label = self.model.names[cls_id]
                
                if label.isdigit():
                    x1 = box.xyxy[0][0].item() 
                    detections.append((x1, label))

        # 2. Sorteer van Links naar Rechts
        detections.sort(key=lambda x: x[0])

        # 3. Plak cijfers aan elkaar
        number_str = "".join([d[1] for d in detections])
        
        raw_number = None # Standaard None als we niks zien
        if number_str:
            try:
                raw_number = int(number_str)
            except ValueError:
                pass

        # We returnen nu direct de RUWE waarde, zonder smoothing
        return raw_number, results[0].plot()

# Global setup blijft hetzelfde
reader = None

def init_model(app_config):
    global reader
    path = os.path.join(os.getcwd(), app_config['YOLO_MODEL_PATH'])
    reader = DigitalReadout(path)