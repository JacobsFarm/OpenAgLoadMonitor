# AgLoadMonitor 🚜📊

**Open Source Feed Loading Assistant powered by Computer Vision**

AgLoadMonitor is an open-source solution designed to digitize and simplify the feeding process on the farm. By using a Raspberry Pi and a custom-trained **YOLO (Ultralytics)** model, this system reads the weight display of your feed mixer or block wagon via a standard ip-camera and streams the data directly to your smartphone or tablet.

No expensive proprietary hardware upgrades needed—just smart software and off-the-shelf components.

---

## 🧠 How it Works

### 1. The Vision Pipeline (YOLO)
Instead of standard OCR (which struggles with digital screens in sunlight), we use a custom-trained **Ultralytics YOLO model**.
* **Detection:** The model detects individual digits on the screen.
* **Logic:** `[1] + [2] + [3] + [0]` detected → Parsed as `1230 kg`.
* **Stream Optimization:** To reduce latency on the local network, the web interface leverages the JavaScript framework JSMpeg.
  
<img width="641" height="410" alt="Schermafbeelding 2026-01-26 214556" src="https://github.com/user-attachments/assets/dd896495-5972-489a-8b5f-03c8952141c9" />

**OpenDataset:** for this project the dataset where is trained on is available at https://universe.roboflow.com/projects-4essy/feedload-monitors

### 2. The Data Flow
1.  **Startup:** Tractor starts → Pi Boots → Connects to Camera.
2.  **Loading:** User selects a Feed Plan on the phone.
3.  **Monitoring:** * Camera watches the scale.
    * YOLO parses the numbers.
    * App calculates "Remaining to load".
4.  **Completion:** User finishes loading.
5.  **Shutdown/Sync:** Pi connects to Farm WiFi → Uploads `logs.json` → Downloads updated `plans.json`.


**
---
   
## 🚀 Key Features

### Core Functionality
* **Real-time Weight Digitization:** Uses Computer Vision to read the 7-segment display of your existing weighing scale.
* **Digital Feed Plans:** Manage recipes (Grass, Maize, Meal, etc.) via a web interface.
* **Target Visualization:** Progress bars turn from **Red** to **Green** as you approach the target weight.
* **Quick Adjustments:** Buttons to instantly adjust the total feed amount by ±10% or ±20% based on herd appetite.

### Smart Logic (The "Easy" Factor)
* **🔄 Auto-Tare:** The software detects when the screen jumps to `0` and automatically switches to the next component in the feed plan.
* **⚖️ Stability Check:** The system waits for the weight to remain stable for **3 seconds** before logging the data, preventing false readings from a shaking wagon.
* **📸 Visual Audit Log:** Saves a low-res screenshot of the physical scale for every loaded component. (e.g., *"The system logged 1230kg, and here is the photo of the screen proving it."*)

### Connectivity & Sync
* **Offline-First Architecture:** The Raspberry Pi acts as a local server. You connect your phone directly to it in the tractor—no internet required to feed.
* **Smart Cloud Sync:** When the tractor is turned off (or returns to the farm yard), the Pi detects the home WiFi and pushes JSON logs to a cloud location (GitHub/Dropbox/Private Server). This ensures feed plans can be edited in the office and downloaded automatically the next morning.

---

## 🛠 Hardware Setup

1.  **Compute:** Jetson Nano acting as the local web server and Image processor.
    * *Power:* Connected to the tractor's 12V ignition (boots on start).
2.  **Vision:** Standard IP Camera.
    * *Mounting:* Directed at the weighing monitor.
    * *Optional:* Secondary camera inside the mixing tub (future feature).
3.  **Client:** Any smartphone, tablet, or laptop (via Browser).

---

## 📦 Installation & Usage

### Prerequisites
* Python 3.10
* Ultralytics (`pip install ultralytics`)
* Flask or Django (for the web server)
* OpenCV (`cv2`)
* winget install "Gyan.FFmpeg"
* go2rtc.exe downloadable from https://github.com/AlexxIT/go2rtc
* **The frontend is Built with SvelteKit.

### Running the Server
```bash
# Check the ultralytics docs for booting the Jetson and installing the Embedded Cuda
https://docs.ultralytics.com/guides/nvidia-jetson/#detailed-comparison-tables 

# Clone the repository
git clone https://github.com/JacobsFarm/AgLoadmonitor.git

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py

Accessing the Interface

    Connect your phone to the Jetson's WiFi Hotspot.

    Navigate to http://192.168.x.x:5000 in your browser, (firefox doesn't work, chrome most stabile)

    Connecto to http://192.168.x.x:5000/video_feed_ocr #for seeing what the feedmonitor camera sees with yolo prediction
    Connecto to http://192.168.x.x:5000/video_feed_cam1 #for checking Camera 1 feed
    Connecto to http://192.168.x.x:5000/video_feed_cam2 #for checking Camera 2 feed

Running it on a (linux) pc it can with almost zero latency on 127.0.0.1:5001 
```
---

For the jetson

sudo apt update
sudo apt install ffmpeg


## 🗺 Roadmap & Challenges

- [x] **Browser Camera Integration:** Basic camera functionality operational in the browser.
- [x] **Automated Weight Reading:** Implement digit recognition using [YOLO](https://github.com/ultralytics/ultralytics).
- [x] **Stream handling:** Optimize stream handling for lower latency using go2rtc
- [x] **Better webapp:** Restructure to use the Svelte compiler
- [ ] **configuration:** Extra tabs for configuration, uploading feed plans, history
- [ ] **Feed Plan Logic:** Develop progress tracking, dynamic component switching, and visual feedback.
- [ ] **Feed Type Classification:** Auto-detect feed type (e.g., Grass vs. Maize) via internal camera to adjust the plan automatically.
- [ ] **start over:** The created technical debt is unsustainable, burn the the existing repo, re-engineer the system with a architecture that makes sense
- [ ] **Production Architecture:** Further Optimize for performance, security, fault tolerance, and simplify the installation/upgrade process.
- [ ] **Deployment** share ready webapp with server acces for saving feedplans and logs

## Build up tree

openagloadmonitor/
├── app
    ├── api
        ├── __init__.py
        └── endpoints.py
    ├── hardware
        └── __init__.py
    ├── services
        ├── __init__.py
        ├── data_handler.py
        ├── feed_logic.py
        └── weight_logic.py
    ├── vision
        ├── __init__.py
        ├── ocr.py
        └── streamer.py
    ├── web
        ├── __init__.py
        └── routes.py
    └── __init__.py
├── data
    ├── snapshots
    ├── config.json
    ├── feedplan.json
    └── history.json
├── frontend
    ├── public
        └── vite.svg
    ├── src
        ├── assets
            └── svelte.svg
        ├── components
            ├── camera.svelte
            ├── dashboard.svelte
            ├── lading.svelte
            ├── navigation.svelte
            └── settings.svelte
        ├── lib
            └── Counter.svelte
        ├── app.css
        ├── App.svelte
        ├── global.css
        └── main.js
    ├── index.html
    ├── jsconfig.json
    ├── package-lock.json
    ├── package.json
    ├── README.md
    ├── svelte.config.js
    └── vite.config.js
├── test
    ├── notes
    ├── test_image.jpg
    └── test_video.mp4
├── weights
    ├── agloadmonitor.pt
    └── NOTES.txt
├── .gitignore.txt
├── config.py
├── go2rtc.exe
├── go2rtc.yaml
├── LICENSE
├── README.md
├── requirements.txt
├── run.bat
└── run.py


## 🤝 Contributing

We welcome farmers and developers!

Connect me at jacobsfarmsocial@gmail.com

    Fork the Project

    Create your Feature Branch (git checkout -b feature/NewFeedLogic)

    Commit your Changes (git commit -m 'Add support for gallons')

    Push to the Branch (git push origin feature/NewFeedLogic)

    Open a Pull Request


