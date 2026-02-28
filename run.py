import json
import os
import sys
import subprocess
import atexit
from app import create_app

# Globale variabele om het go2rtc proces bij te houden
go2rtc_process = None

def generate_go2rtc_config():
    config_path = 'config.json'
    if not os.path.exists(config_path):
        config_path = os.path.join('data', 'config.json')
        
    try:
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
            # Gebruik de specifieke URL's uit config.json
            yaml_content += f"  cam1: {config.get('RTSP_URL_1')}\n"
            yaml_content += f"  cam2: {config.get('RTSP_URL_2')}\n"
            yaml_content += f"  cam_ocr: {config.get('RTSP_URL_OCR')}\n"

        with open('go2rtc.yaml', 'w') as f:
            f.write(yaml_content)
        print("✅ go2rtc.yaml gesynchroniseerd voor 3 camera's!")
        
    except Exception as e:
        print(f"⚠️ Fout: {e}")

def start_go2rtc():
    """Start de go2rtc server op de achtergrond"""
    global go2rtc_process
    
    # Bepaal automatisch de juiste bestandsnaam (Windows = .exe, Linux/Jetson = zonder extensie)
    exe_name = "go2rtc.exe" if sys.platform.startswith("win") else "./go2rtc"
    
    # Check of het bestand wel echt in de map staat
    if not os.path.exists(exe_name.replace("./", "")):
        print(f"❌ WAARSCHUWING: {exe_name.replace('./', '')} niet gevonden in deze map!")
        print("   Download het bestand en zet het naast run.py om de videostream te laten werken.")
        return

    print(f"🚀 Start {exe_name} op de achtergrond...")
    try:
        # Start het proces op de achtergrond
        go2rtc_process = subprocess.Popen([exe_name])
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

# Zorg dat de cleanup functie altijd draait als het script stopt (bijv. met CTRL+C)
atexit.register(cleanup)

# Initialiseer de Flask app
app = create_app()

if __name__ == '__main__':
    # 1. Update de configuratie
    generate_go2rtc_config()
    
    # 2. Start Go2rtc op de achtergrond
    start_go2rtc()
    
    # 3. Start de Flask server
    # threaded=True zorgt dat de videostream de website niet blokkeert
    app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)
