import os
import sys
import cv2
import numpy as np
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import shutil
from pathlib import Path

# Configuration - you can adjust these to your own paths
model_path = r"custom_model.pt" 
input_folder = r"C:\path\to\your\Datasets\to_annotate"
output_img_folder = r"C:\path\to\your\annotated_images"
output_label_folder = r"C:\path\to\your\annotated_labels"
delete_folder = r"C:\path\to\your\delete"
enable_delete_mode = True

# Nieuwe parameter: Zet op True om de confidence (bijv. 0.85) te tonen, of False om alleen de naam te tonen
show_confidence = False

# Classes from data.yaml
CLASS_NAMES = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'lcd-screen', 'monitor']

# Unieke kleuren per class (in RGB-formaat)
CLASS_COLORS = [
    (255, 50, 50),    # 0: Rood
    (50, 255, 50),    # 1: Groen
    (50, 100, 255),   # 2: Blauw
    (255, 255, 50),   # 3: Geel
    (255, 50, 255),   # 4: Magenta
    (50, 255, 255),   # 5: Cyaan
    (128, 0, 0),      # 6: Donkerrood
    (0, 128, 0),      # 7: Donkergroen
    (0, 0, 128),      # 8: Donkerblauw
    (128, 128, 0),    # 9: Olijf/Oker
    (128, 0, 128),    # lcd-screen: Paars
    (0, 128, 128)     # monitor: Teal
]

class YoloAnnotationApp:
    def __init__(self, root, model_path, input_folder, output_img_folder, output_label_folder, delete_folder, enable_delete_mode, show_confidence):
        self.root = root
        self.root.title("Annotation Helper - Multi-Class")
        self.root.geometry("1200x750")
        
        # Set up folders, model path, and classes
        self.model_path = model_path
        self.input_folder = input_folder
        self.output_img_folder = output_img_folder
        self.output_label_folder = output_label_folder
        self.delete_folder = delete_folder
        self.delete_mode_enabled = enable_delete_mode
        self.show_confidence = show_confidence
        self.class_names = CLASS_NAMES
        
        # Create output folders if they don't exist
        os.makedirs(self.output_img_folder, exist_ok=True)
        os.makedirs(self.output_label_folder, exist_ok=True)
        os.makedirs(self.delete_folder, exist_ok=True)
        
        # Get all images
        self.image_files = [f for f in os.listdir(self.input_folder) 
                            if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        self.current_index = 0
        
        # Variables for manual bounding box drawing
        self.drawing_mode = False
        self.start_x = None
        self.start_y = None
        self.current_rectangle = None
        self.manual_bbox = None
        self.current_img = None
        self.current_image_info = {}
        
        # Undo functionality
        self.last_action = None
        
        # Load the YOLO model
        self.load_model()
        
        # UI setup
        self.setup_ui()
        
        # Load the first image
        if self.image_files:
            self.root.update_idletasks()
            self.root.after(100, self.load_current_image)
    
    def load_model(self):
        try:
            from ultralytics import YOLO
            self.model = YOLO(self.model_path)
            self.model_type = "ultralytics"
            print("Model loaded with ultralytics YOLO")
        except Exception as e:
            print(f"Error loading model with ultralytics: {e}")
            try:
                import torch
                self.model = torch.hub.load('ultralytics/yolov5', 'custom', path=self.model_path, force_reload=True)
                self.model_type = "torch_hub"
                print("Model loaded with torch.hub")
            except Exception as e2:
                print(f"Both loading methods failed: {e2}")
                raise Exception("Could not load YOLO model. Install 'pip install ultralytics'")
    
    def setup_ui(self):
        # Create frame for images
        self.image_frame = ttk.Frame(self.root)
        self.image_frame.pack(pady=10, fill=tk.BOTH, expand=True)
        
        # Left: original image
        self.original_frame = ttk.LabelFrame(self.image_frame, text="Original Image")
        self.original_frame.pack(side=tk.LEFT, padx=10, fill=tk.BOTH, expand=True)
        self.original_canvas = tk.Canvas(self.original_frame, highlightthickness=0)
        self.original_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Right: image with predictions
        self.prediction_frame = ttk.LabelFrame(self.image_frame, text="Image with YOLO Predictions")
        self.prediction_frame.pack(side=tk.RIGHT, padx=10, fill=tk.BOTH, expand=True)
        self.prediction_canvas = tk.Canvas(self.prediction_frame, highlightthickness=0)
        self.prediction_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Event binding for mouse events
        self.original_canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.original_canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.original_canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        
        # Create footer with buttons
        self.button_frame = ttk.Frame(self.root)
        self.button_frame.pack(pady=10)
        
        # Status information
        self.status_label = ttk.Label(self.button_frame, text="")
        self.status_label.grid(row=0, column=0, columnspan=8, pady=5)
        
        # Row 1: Delete mode checkbox & Manual Class Selector
        self.delete_mode_var = tk.BooleanVar(value=self.delete_mode_enabled)
        self.delete_mode_checkbox = ttk.Checkbutton(
            self.button_frame, text="Enable Delete Mode", variable=self.delete_mode_var, command=self.toggle_delete_mode
        )
        self.delete_mode_checkbox.grid(row=1, column=0, columnspan=3, pady=5)
        
        ttk.Label(self.button_frame, text="Manual Class:").grid(row=1, column=3, columnspan=2, sticky='e', padx=5)
        self.selected_class = tk.StringVar(value=self.class_names[0])
        self.class_dropdown = ttk.Combobox(self.button_frame, textvariable=self.selected_class, values=self.class_names, state='readonly', width=15)
        self.class_dropdown.grid(row=1, column=5, columnspan=3, sticky='w', padx=5)
        
        # Navigation and action buttons
        ttk.Button(self.button_frame, text="Previous (A)", command=self.prev_image).grid(row=2, column=0, padx=5)
        ttk.Button(self.button_frame, text="Next (D)", command=self.next_image).grid(row=2, column=1, padx=5)
        ttk.Button(self.button_frame, text="Save (S)", command=self.save_current).grid(row=2, column=2, padx=5)
        ttk.Button(self.button_frame, text="Null (N)", command=self.save_as_null).grid(row=2, column=3, padx=5)
        ttk.Button(self.button_frame, text="Skip (O)", command=self.skip_current).grid(row=2, column=4, padx=5)
        ttk.Button(self.button_frame, text="Draw (T)", command=self.toggle_drawing_mode).grid(row=2, column=5, padx=5)
        
        self.undo_button = ttk.Button(self.button_frame, text="Undo (U)", command=self.undo_last_action)
        self.undo_button.grid(row=2, column=6, padx=5)
        self.undo_button.config(state='disabled')
        
        ttk.Button(self.button_frame, text="Exit (Q)", command=self.root.quit).grid(row=2, column=7, padx=5)
        
        # Keyboard shortcuts
        self.root.bind("<a>", lambda event: self.prev_image())
        self.root.bind("<A>", lambda event: self.prev_image())
        self.root.bind("<Left>", lambda event: self.prev_image())
        self.root.bind("<d>", lambda event: self.next_image())
        self.root.bind("<D>", lambda event: self.next_image())
        self.root.bind("<Right>", lambda event: self.next_image())
        self.root.bind("<s>", lambda event: self.save_current())
        self.root.bind("<S>", lambda event: self.save_current())
        self.root.bind("<n>", lambda event: self.save_as_null())
        self.root.bind("<N>", lambda event: self.save_as_null())
        self.root.bind("<o>", lambda event: self.skip_current())
        self.root.bind("<O>", lambda event: self.skip_current())
        self.root.bind("<space>", lambda event: self.skip_current())
        self.root.bind("<t>", lambda event: self.toggle_drawing_mode())
        self.root.bind("<T>", lambda event: self.toggle_drawing_mode())
        self.root.bind("<u>", lambda event: self.undo_last_action())
        self.root.bind("<U>", lambda event: self.undo_last_action())
        self.root.bind("<Return>", lambda event: self.confirm_manual_bbox() if self.drawing_mode and self.manual_bbox else None)
        self.root.bind("<Q>", lambda event: self.root.quit())
        self.root.bind("<q>", lambda event: self.root.quit())
        self.root.bind("<Escape>", lambda event: self.root.quit())
    
    def toggle_delete_mode(self):
        self.delete_mode_enabled = self.delete_mode_var.get()
        status_text = "Delete mode enabled - processed images will be moved to DELETE folder" if self.delete_mode_enabled else "Delete mode disabled"
        self.status_label.config(text=status_text)
    
    def store_action_for_undo(self, action_type, img_filename, was_moved_to_delete=False):
        self.last_action = {
            'type': action_type,
            'filename': img_filename,
            'was_moved_to_delete': was_moved_to_delete,
            'current_index': self.current_index
        }
        self.undo_button.config(state='normal')
    
    def undo_last_action(self):
        if not self.last_action:
            self.status_label.config(text="No action to undo!")
            return
        
        action = self.last_action
        img_filename = action['filename']
        base_name = os.path.splitext(img_filename)[0]
        
        try:
            if action['type'] in ['save', 'null', 'manual']:
                annotated_img_path = os.path.join(self.output_img_folder, img_filename)
                if os.path.exists(annotated_img_path):
                    os.remove(annotated_img_path)
                
                label_path = os.path.join(self.output_label_folder, f"{base_name}.txt")
                if os.path.exists(label_path):
                    os.remove(label_path)
            
            if action['was_moved_to_delete']:
                delete_path = os.path.join(self.delete_folder, img_filename)
                input_path = os.path.join(self.input_folder, img_filename)
                
                if os.path.exists(delete_path):
                    shutil.move(delete_path, input_path)
                    if img_filename not in self.image_files:
                        self.image_files.insert(action['current_index'], img_filename)
            
            self.status_label.config(text=f"Undid action for: {img_filename}")
            self.last_action = None
            self.undo_button.config(state='disabled')
            self.load_current_image()
            
        except Exception as e:
            self.status_label.config(text=f"Error during undo: {str(e)}")
    
    def move_to_delete_if_enabled(self, img_filename):
        if not self.delete_mode_enabled: return
        source_path = os.path.join(self.input_folder, img_filename)
        dest_path = os.path.join(self.delete_folder, img_filename)
        try:
            shutil.move(source_path, dest_path)
        except Exception as e:
            print(f"Error moving image to DELETE: {e}")
    
    def load_current_image(self):
        if not self.image_files:
            self.status_label.config(text="No images found!")
            return
        
        self.drawing_mode = False
        self.manual_bbox = None
        
        status_text = f"Image {self.current_index + 1} of {len(self.image_files)}: {self.image_files[self.current_index]}"
        if self.delete_mode_enabled:
            status_text += " | Delete mode: ON"
            
        self.status_label.config(text=status_text)
        
        img_path = os.path.join(self.input_folder, self.image_files[self.current_index])
        original_img = cv2.imread(img_path)
        original_img = cv2.cvtColor(original_img, cv2.COLOR_BGR2RGB)
        prediction_img = original_img.copy()
        
        try:
            if self.model_type == "ultralytics":
                results = self.model(img_path, conf=0.3)
            else:
                self.model.conf = 0.3
                results = self.model(img_path)
        except Exception as e:
            print(f"Error during prediction: {e}")
            results = None
        
        self.current_results = results
        self.current_img_path = img_path
        self.current_img = original_img
        
        self.draw_predictions(prediction_img, results)
        
        self.display_image(original_img, self.original_canvas)
        self.display_image(prediction_img, self.prediction_canvas)
    
    def draw_predictions(self, img, results):
        if results is None:
            cv2.putText(img, "Error processing predictions", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
            return
            
        try:
            if self.model_type == "ultralytics":
                if len(results) > 0:
                    for r in results:
                        for box in r.boxes:
                            xyxy = box.xyxy[0].cpu().numpy()
                            x1, y1, x2, y2 = map(int, xyxy)
                            conf = float(box.conf[0].cpu().numpy())
                            cls_id = int(box.cls[0].cpu().numpy())
                            
                            cls_name = self.class_names[cls_id] if cls_id < len(self.class_names) else str(cls_id)
                            color = CLASS_COLORS[cls_id % len(CLASS_COLORS)]
                            
                            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
                            
                            if self.show_confidence:
                                label = f"{cls_name} {conf:.2f}"
                            else:
                                label = f"{cls_name}"
                                
                            cv2.putText(img, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            else:
                for pred in results.xyxy[0].cpu().numpy():
                    x1, y1, x2, y2, conf, cls = pred
                    cls_id = int(cls)
                    
                    cls_name = self.class_names[cls_id] if cls_id < len(self.class_names) else str(cls_id)
                    color = CLASS_COLORS[cls_id % len(CLASS_COLORS)]
                    
                    cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
                    
                    if self.show_confidence:
                        label = f"{cls_name} {conf:.2f}"
                    else:
                        label = f"{cls_name}"
                        
                    cv2.putText(img, label, (int(x1), int(y1)-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        except Exception as e:
            print(f"Error drawing predictions: {e}")
            cv2.putText(img, f"Error: {str(e)}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
    
    def display_image(self, cv_img, canvas):
        canvas_width = canvas.winfo_width() or 500
        canvas_height = canvas.winfo_height() or 500
        height, width = cv_img.shape[:2]
        scale = min(canvas_width / width, canvas_height / height) * 0.9
        new_width = int(width * scale)
        new_height = int(height * scale)
        
        if scale != 1.0:
            cv_img = cv2.resize(cv_img, (new_width, new_height))
        
        pil_img = Image.fromarray(cv_img)
        tk_img = ImageTk.PhotoImage(pil_img)
        canvas.delete("all")
        
        x_offset = (canvas_width - new_width) // 2
        y_offset = (canvas_height - new_height) // 2
        
        canvas.create_image(x_offset, y_offset, anchor=tk.NW, image=tk_img)
        canvas.image = tk_img
        
        self.current_image_info = {
            'width': width, 'height': height, 'display_width': new_width,
            'display_height': new_height, 'x_offset': x_offset,
            'y_offset': y_offset, 'scale': scale
        }
    
    def next_image(self):
        if self.current_index < len(self.image_files) - 1:
            self.current_index += 1
            self.load_current_image()
    
    def prev_image(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.load_current_image()
            
    def skip_current(self):
        img_filename = self.image_files[self.current_index]
        was_moved = self.delete_mode_enabled
        self.store_action_for_undo('skip', img_filename, was_moved)
        self.move_to_delete_if_enabled(img_filename)
        self.status_label.config(text=f"Image skipped: {img_filename}")
        self.next_image()
    
    def save_current(self):
        if not self.image_files: return
        if self.drawing_mode and self.manual_bbox:
            self.save_with_manual_bbox()
            return
        
        img_filename = self.image_files[self.current_index]
        base_name = os.path.splitext(img_filename)[0]
        img_dest = os.path.join(self.output_img_folder, img_filename)
        try:
            shutil.copy2(self.current_img_path, img_dest)
        except Exception as e:
            self.status_label.config(text=f"Error: Could not copy image - {str(e)}")
            return
        
        label_path = os.path.join(self.output_label_folder, f"{base_name}.txt")
        try:
            self.write_label_file(label_path)
            was_moved = self.delete_mode_enabled
            self.store_action_for_undo('save', img_filename, was_moved)
            self.move_to_delete_if_enabled(img_filename)
            self.status_label.config(text=f"Image saved: {img_filename}")
            self.next_image()
        except Exception as e:
            self.status_label.config(text=f"Error: Could not write label - {str(e)}")
    
    def save_as_null(self):
        if not self.image_files: return
        img_filename = self.image_files[self.current_index]
        base_name = os.path.splitext(img_filename)[0]
        img_dest = os.path.join(self.output_img_folder, img_filename)
        try:
            shutil.copy2(self.current_img_path, img_dest)
        except Exception as e:
            self.status_label.config(text=f"Error: Could not copy image - {str(e)}")
            return
        
        label_path = os.path.join(self.output_label_folder, f"{base_name}.txt")
        open(label_path, 'w').close()
        
        was_moved = self.delete_mode_enabled
        self.store_action_for_undo('null', img_filename, was_moved)
        self.move_to_delete_if_enabled(img_filename)
        self.status_label.config(text=f"Image saved as NULL: {img_filename}")
        self.next_image()
    
    def write_label_file(self, label_path):
        img = cv2.imread(self.current_img_path)
        height, width = img.shape[:2]
        has_detections = False
        
        with open(label_path, 'w') as f:
            if self.model_type == "ultralytics":
                if len(self.current_results) > 0 and len(self.current_results[0].boxes) > 0:
                    for box in self.current_results[0].boxes:
                        xyxy = box.xyxy[0].cpu().numpy()
                        x1, y1, x2, y2 = xyxy
                        cls_id = int(box.cls[0].item())
                        
                        x_center = ((x1 + x2) / 2) / width
                        y_center = ((y1 + y2) / 2) / height
                        w = (x2 - x1) / width
                        h = (y2 - y1) / height
                        f.write(f"{cls_id} {x_center} {y_center} {w} {h}\n")
                        has_detections = True
            else:
                detections = self.current_results.xyxy[0].cpu().numpy()
                if len(detections) > 0:
                    for det in detections:
                        x1, y1, x2, y2, conf, cls = det
                        cls_id = int(cls)
                        
                        x_center = ((x1 + x2) / 2) / width
                        y_center = ((y1 + y2) / 2) / height
                        w = (x2 - x1) / width
                        h = (y2 - y1) / height
                        f.write(f"{cls_id} {x_center} {y_center} {w} {h}\n")
                        has_detections = True
        
        if not has_detections:
            open(label_path, 'w').close()
            
    def toggle_drawing_mode(self):
        if self.drawing_mode and self.manual_bbox:
            response = messagebox.askyesnocancel("Confirm Drawing", "Do you want to save this bounding box?\n\nYes = Save and continue\nNo = Redraw\nCancel = Exit drawing mode")
            if response is True:
                self.save_with_manual_bbox()
                return
            elif response is False:
                self.manual_bbox = None
                if self.current_rectangle:
                    self.original_canvas.delete(self.current_rectangle)
                    self.current_rectangle = None
                self.status_label.config(text="Draw a new bounding box")
                return
            else:
                self.drawing_mode = False
                self.load_current_image()
                self.status_label.config(text=f"Drawing mode disabled")
                return
                
        self.drawing_mode = not self.drawing_mode
        if self.drawing_mode:
            self.manual_bbox = None
            if self.current_rectangle:
                self.original_canvas.delete(self.current_rectangle)
                self.current_rectangle = None
            self.display_image(self.current_img, self.original_canvas)
            self.status_label.config(text="Drawing mode active: Select class from dropdown, draw a box, then press Enter.")
        else:
            self.load_current_image()
            self.status_label.config(text=f"Drawing mode disabled")
    
    def confirm_manual_bbox(self):
        if not self.drawing_mode or not self.manual_bbox: return
        cls_name = self.selected_class.get()
        response = messagebox.askyesno("Confirm Drawing", f"Save this bounding box as '{cls_name}' and continue?")
        if response:
            self.save_with_manual_bbox()
    
    def on_mouse_down(self, event):
        if not self.drawing_mode: return
        self.start_x, self.start_y = event.x, event.y
        if self.current_rectangle:
            self.original_canvas.delete(self.current_rectangle)
            self.manual_bbox = None
        self.current_rectangle = self.original_canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y, outline='red', width=2)
    
    def on_mouse_drag(self, event):
        if not self.drawing_mode or not self.current_rectangle: return
        self.original_canvas.coords(self.current_rectangle, self.start_x, self.start_y, event.x, event.y)
    
    def on_mouse_up(self, event):
        if not self.drawing_mode or not self.current_rectangle: return
        end_x, end_y = event.x, event.y
        x1, y1 = min(self.start_x, end_x), min(self.start_y, end_y)
        x2, y2 = max(self.start_x, end_x), max(self.start_y, end_y)
        self.original_canvas.coords(self.current_rectangle, x1, y1, x2, y2)
        
        x1_img = (x1 - self.current_image_info['x_offset']) / self.current_image_info['scale']
        y1_img = (y1 - self.current_image_info['y_offset']) / self.current_image_info['scale']
        x2_img = (x2 - self.current_image_info['x_offset']) / self.current_image_info['scale']
        y2_img = (y2 - self.current_image_info['y_offset']) / self.current_image_info['scale']
        
        x1_img = max(0, min(x1_img, self.current_image_info['width']))
        y1_img = max(0, min(y1_img, self.current_image_info['height']))
        x2_img = max(0, min(x2_img, self.current_image_info['width']))
        y2_img = max(0, min(y2_img, self.current_image_info['height']))
        
        self.manual_bbox = (x1_img, y1_img, x2_img, y2_img)
        self.status_label.config(text=f"Box drawn. Class: {self.selected_class.get()}. Press Enter to confirm or T to redraw.")
    
    def save_with_manual_bbox(self):
        if not self.manual_bbox:
            self.status_label.config(text="Draw a bounding box first!")
            return
            
        img_filename = self.image_files[self.current_index]
        base_name = os.path.splitext(img_filename)[0]
        img_dest = os.path.join(self.output_img_folder, img_filename)
        try:
            shutil.copy2(self.current_img_path, img_dest)
        except Exception as e:
            self.status_label.config(text=f"Error: Could not copy image - {str(e)}")
            return
        
        label_path = os.path.join(self.output_label_folder, f"{base_name}.txt")
        height, width = self.current_img.shape[:2]
        
        x1, y1, x2, y2 = self.manual_bbox
        x_center = ((x1 + x2) / 2) / width
        y_center = ((y1 + y2) / 2) / height
        w = (x2 - x1) / width
        h = (y2 - y1) / height
        
        # Get the class ID from the dropdown selection
        cls_name = self.selected_class.get()
        cls_id = self.class_names.index(cls_name)
        
        with open(label_path, 'w') as f:
            f.write(f"{cls_id} {x_center} {y_center} {w} {h}\n")
        
        was_moved = self.delete_mode_enabled
        self.store_action_for_undo('manual', img_filename, was_moved)
        self.move_to_delete_if_enabled(img_filename)
        self.status_label.config(text=f"Image saved with manual bounding box (Class: {cls_name}): {img_filename}")
        
        self.drawing_mode = False
        self.manual_bbox = None
        self.next_image()

def main():
    root = tk.Tk()
    app = YoloAnnotationApp(root, model_path, input_folder, output_img_folder, output_label_folder, delete_folder, enable_delete_mode, show_confidence)
    root.mainloop()

if __name__ == "__main__":
    main()
