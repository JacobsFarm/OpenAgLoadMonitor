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

def launch_kiosk(url, insecure=False):
    """Start de browser schermvullend zonder adresbalk (wagenscherm)."""
    browser = find_browser()
    if not browser:
        print("⚠️ Geen Chrome/Chromium/Edge gevonden voor kiosk-modus.")
        return False

    # Aparte profielmap voorkomt 'herstel sessie'-popups op het vaste scherm
    profile = os.path.join(os.path.expanduser("~"), ".agloadmonitor-kiosk")
    args = [
        browser,
        f"--app={url}",
        "--kiosk",
        "--start-fullscreen",
        "--noerrdialogs",
        "--disable-infobars",
        "--no-first-run",
        "--disable-session-crashed-bubble",
        f"--user-data-dir={profile}",
    ]
    # Bij ons eigen HTTPS-certificaat op localhost vertrouwt de browser de CA niet;
    # voor het lokale wagenscherm negeren we die waarschuwing zodat het beeld toont.
    if insecure:
        args.append("--ignore-certificate-errors")
    try:
        subprocess.Popen(args)
        return True
    except Exception as e:
        print(f"⚠️ Kon kiosk-browser niet starten: {e}")
        return False

def open_interface(kiosk, scheme="http", insecure=False):
    """Open de webinterface op het device: kiosk indien gewenst, anders gewone browser."""
    url = f"{scheme}://localhost:{PORT}"
    if kiosk and launch_kiosk(url, insecure):
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

    # HTTPS opzetten indien gewenst (nodig om de app op Android te installeren als PWA)
    ssl_context = None
    if app.config.get("USE_HTTPS", False):
        try:
            from app.cert import ensure_certificates
            cert_dir = os.path.join(os.getcwd(), "data", "certs")
            cert_p, key_p, ca_p = ensure_certificates(cert_dir)
            ssl_context = (cert_p, key_p)
            print(f"🔒 HTTPS aan op poort {PORT}. "
                  f"Installeer de CA op je telefoon via /rootCA.pem en open daarna https://<ip>:{PORT}")
        except Exception as e:
            print(f"⚠️ HTTPS kon niet worden opgezet ({e}); de server start op http.")

    scheme = "https" if ssl_context else "http"

    # Open de interface kort nadat de server is opgestart
    if auto_open:
        threading.Timer(2.0, open_interface, args=(kiosk, scheme, ssl_context is not None)).start()

    # Start de Flask server (cameras worden als MJPEG geserveerd, geen go2rtc meer nodig)
    app.run(host='0.0.0.0', port=PORT, debug=False, threaded=True, ssl_context=ssl_context)
