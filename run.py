import os
import sys
import shutil
import subprocess
import threading
import webbrowser
import multiprocessing
from app import create_app

PORT = 5001

def find_browser():
    """Zoekt een Chromium-achtige browser (Chrome/Chromium/Edge) voor kiosk-modus."""
    candidates = []
    if sys.platform.startswith("win"):
        local = os.environ.get("LOCALAPPDATA", "")
        pf = os.environ.get("PROGRAMFILES", r"C:\Program Files")
        pf86 = os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")
        candidates = [
            os.path.join(pf, r"Google\Chrome\Application\chrome.exe"),
            os.path.join(pf86, r"Google\Chrome\Application\chrome.exe"),
            os.path.join(local, r"Google\Chrome\Application\chrome.exe"),
            os.path.join(pf86, r"Microsoft\Edge\Application\msedge.exe"),
            os.path.join(pf, r"Microsoft\Edge\Application\msedge.exe"),
        ]
    else:
        for name in ("google-chrome", "google-chrome-stable", "chromium",
                     "chromium-browser", "microsoft-edge"):
            found = shutil.which(name)
            if found:
                candidates.append(found)

    for path in candidates:
        if path and os.path.exists(path):
            return path
    return None

def launch_kiosk(url):
    """Start de browser schermvullend zonder adresbalk (wagenscherm)."""
    browser = find_browser()
    if not browser:
        print("⚠️ Geen Chrome/Chromium/Edge gevonden voor kiosk-modus.")
        return False

    # Aparte profielmap voorkomt 'herstel sessie'-popups op het vaste scherm
    profile = os.path.join(os.path.expanduser("~"), ".agloadmonitor-kiosk")
    try:
        subprocess.Popen([
            browser,
            f"--app={url}",
            "--kiosk",
            "--start-fullscreen",
            "--noerrdialogs",
            "--disable-infobars",
            "--no-first-run",
            "--disable-session-crashed-bubble",
            f"--user-data-dir={profile}",
        ])
        return True
    except Exception as e:
        print(f"⚠️ Kon kiosk-browser niet starten: {e}")
        return False

def open_interface(kiosk):
    """Open de webinterface op het device: kiosk indien gewenst, anders gewone browser."""
    url = f"http://localhost:{PORT}"
    if kiosk and launch_kiosk(url):
        print("🖥️  Kiosk-modus gestart")
        return
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"⚠️ Kon de browser niet automatisch openen: {e}")

if __name__ == '__main__':
    # Belangrijk voor PyInstaller en Multiprocessing (zoals YOLO)
    multiprocessing.freeze_support()

    # Initialiseer de Flask app (start ook de OCR- en camera-threads)
    app = create_app()

    kiosk = bool(app.config.get("KIOSK_MODE", False))
    auto_open = bool(app.config.get("AUTO_OPEN_BROWSER", True))

    # Open de interface kort nadat de server is opgestart
    if auto_open:
        threading.Timer(2.0, open_interface, args=(kiosk,)).start()

    # Start de Flask server (cameras worden als MJPEG geserveerd, geen go2rtc meer nodig)
    app.run(host='0.0.0.0', port=PORT, debug=False, threaded=True)
