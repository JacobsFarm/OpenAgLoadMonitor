import asyncio
import websockets
import json
import os
import shutil

# --- 1. Instellingen Laden ---
def get_rtsp_url():
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # Probeer config te vinden in ..\data\ of .\data\
        paths_to_check = [
            os.path.join(base_dir, '..', 'data', 'config.json'),
            os.path.join(base_dir, 'data', 'config.json')
        ]
        
        json_path = None
        for path in paths_to_check:
            if os.path.exists(path):
                json_path = path
                break
        
        if json_path:
            with open(json_path, 'r') as f:
                data = json.load(f)
                return data.get("RTSP_URL_BAK")
        
        print("LET OP: Geen config.json gevonden!")
        return None

    except Exception as e:
        print(f"Fout bij laden config: {e}")
        return None

# --- 2. De Video Server Handler (Asyncio versie) ---
async def handler(websocket):
    print(f"Verbinding poging van: {websocket.remote_address}")
    
    rtsp_url = get_rtsp_url()
    if not rtsp_url:
        print("❌ Geen RTSP URL! Check config.")
        await websocket.close()
        return

    # Check of FFmpeg bestaat
    if not shutil.which("ffmpeg"):
        print("❌ CRITISCHE FOUT: 'ffmpeg' niet gevonden! Installeer FFmpeg en voeg toe aan PATH.")
        await websocket.close()
        return

    # FFmpeg commando
    command = [
        'ffmpeg',
        '-rtsp_transport', 'tcp',
        '-i', rtsp_url,
        '-f', 'mpegts',
        '-codec:v', 'mpeg1video',
        '-b:v', '800k',
        '-r', '25',
        '-s', '640x360',
        '-muxdelay', '0.001',
        '-'
    ]

    print("🎥 Start FFmpeg...")
    
    # Gebruik create_subprocess_exec (Niet-blokkerend!)
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL
    )

    try:
        while True:
            # Lees asynchroon data (blokkeert de socket niet)
            data = await process.stdout.read(4096)
            if not data:
                print("FFmpeg stuurde geen data meer (stream gestopt?)")
                break
            
            await websocket.send(data)
            
    except websockets.exceptions.ConnectionClosed:
        print("👋 Kijker heeft verbinding verbroken.")
    except Exception as e:
        print(f"⚠️ Fout in stream loop: {e}")
    finally:
        # Netjes opruimen
        if process.returncode is None:
            process.kill()
            await process.wait()
        print("Process beëindigd.")

# --- 3. Starten ---
async def main():
    print("🚀 Video Server gestart op poort 8080...")
    print("   (Zorg dat FFmpeg geïnstalleerd is!)")
    
    # Ping interval houdt de verbinding levend
    async with websockets.serve(handler, "0.0.0.0", 8080, ping_interval=None):
        await asyncio.get_running_loop().create_future()  # Run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server gestopt.")