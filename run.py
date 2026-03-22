import json
import os
import sys
import subprocess
import atexit
import multiprocessing
from app import create_app

# Globale variabele om het go2rtc proces bij te houden
go2rtc_process = None

def get_bundled_path(relative_path):
    """Vindt bestanden in de tijdelijke PyInstaller map (read-only)."""
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.abspath(relative_path)

def get_persistent_path(relative_path):
    """Vindt/maakt bestanden naast de .exe (read-write)."""
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), relative_path)
    return os.path.abspath(relative_path)

def generate_go2rtc_config():
    """Zorgt ervoor dat de config lokaal naast de .exe staat."""
    data_dir = get_persistent_path('data')
    os.makedirs(data_dir, exist_ok=True)
    config_path = os.path.join(data_dir, 'config.json')
        
    try:
        if not os.path.exists(config_path):
            with open(config_path, 'w') as f:
                json.dump({"VIDEO_SOURCE_TYPE": "file", "VIDEO_SOURCE_FILE": "test.mp4"}, f)

        with open(config_path, 'r') as f:
            config = json.load(f)
            
        yaml_content = "streams:\n"
        
        if config.get("VIDEO_SOURCE_TYPE") == "file":
            video_file = config.get("VIDEO_SOURCE_FILE", "test/test_video.mp4")
            loop_cmd = f"exec:ffmpeg -re -stream_loop -1 -i {video_file} -c:v copy -rtsp_transport tcp -f rtsp {{output}}"
            yaml_content += f"  cam1: '{loop_cmd}'\n"
            yaml_content += f"  cam2: '{loop_cmd}'\n"
            yaml_content += f"  cam_ocr: '{loop_cmd}'\n"
        else:
            yaml_content += f"  cam1: {config.get('RTSP_URL_1', '')}\n"
            yaml_content += f"  cam2: {config.get('RTSP_URL_2', '')}\n"
            yaml_content += f"  cam_ocr: {config.get('RTSP_URL_OCR', '')}\n"

        yaml_path = get_persistent_path('go2rtc.yaml')
        with open(yaml_path, 'w') as f:
            f.write(yaml_content)
        print("✅ go2rtc.yaml gesynchroniseerd voor 3 camera's!")
        
    except Exception as e:
        print(f"⚠️ Fout bij genereren config: {e}")

def start_go2rtc():
    """Start de go2rtc server op de achtergrond"""
    global go2rtc_process
    
    exe_name = "go2rtc.exe" if sys.platform.startswith("win") else "go2rtc"
    exe_path = get_bundled_path(exe_name)
    
    if not os.path.exists(exe_path):
        print(f"❌ WAARSCHUWING: {exe_path} niet gevonden!")
        print("   Zorg dat go2rtc gebundeld is of in de map staat.")
        return

    print(f"🚀 Start {exe_name} op de achtergrond...")
    try:
        # cwd zorgt dat go2rtc de yaml file kan vinden die we net hebben gemaakt
        go2rtc_process = subprocess.Popen([exe_path], cwd=get_persistent_path('.'))
        print("✅ Go2rtc draait!")
    except Exception as e:
        print(f"❌ Fout bij het starten van go2rtc: {e}")

def cleanup():
    """Zorgt ervoor dat go2rtc netjes afsluit als je de Python server stopt"""
    global go2rtc_process
    if go2rtc_process is not None:
        print("\n🛑 Go2rtc proces netjes afsluiten...")
        go2rtc_process.terminate()
        go2rtc_process.wait()

atexit.register(cleanup)

if __name__ == '__main__':
    # Belangrijk voor PyInstaller en Multiprocessing (zoals YOLO)
    multiprocessing.freeze_support()
    
    # Initialiseer de Flask app
    app = create_app()

    # 1. Update de configuratie
    generate_go2rtc_config()
    
    # 2. Start Go2rtc op de achtergrond
    start_go2rtc()
    
    # 3. Start de Flask server
    app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)
