document.addEventListener("DOMContentLoaded", function() {
    console.log("Tractor Monitor JS geladen (Go2rtc versie)!");

    startDataPolling();

    const tabLinks = document.querySelectorAll('.tab-link');
    
    tabLinks.forEach(button => {
        button.addEventListener('click', function() {
            const targetTabId = this.getAttribute('data-tab');
            
            tabLinks.forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });

            this.classList.add('active');
            document.getElementById(targetTabId).classList.add('active');

            // Beheer streams afhankelijk van actieve tab
            if (targetTabId === 'stream-tab') {
                startStream();
            } else {
                stopStream();
            }
        });
    });

    const restartBtn = document.getElementById('restart-btn');
    if (restartBtn) {
        restartBtn.addEventListener('click', function() {
            stopStream();
            setTimeout(startStream, 500);
        });
    }
});

function startDataPolling() {
    setInterval(() => {
        fetch('/api/status')
            .then(response => response.json())
            .then(data => {
                if(data.gewicht !== undefined) {
                    updateDashboard(data.gewicht);
                }
            })
            .catch(err => console.error("API Fout:", err));
    }, 100); 
}

function updateDashboard(weight) {
    const weightDisplays = document.querySelectorAll('.weight-value, .clean-number');
    weightDisplays.forEach(el => {
        el.innerText = weight;
    });
}

// --- FUNCTIE: Go2rtc WebRTC Streams ---
function startStream() {
    console.log("Start Go2rtc streams...");
    
    // We gebruiken de dynamische host, zodat het werkt via localhost én netwerk-IP
    const go2rtcBaseUrl = `http://${window.location.hostname}:1984/webrtc.html`;
    
    const wrapperBak = document.getElementById('video-wrapper-bak');
    if (wrapperBak && !wrapperBak.innerHTML.includes('iframe')) {
        // HIER AANGEPAST: ?src=cam_bak is nu ?src=cam1 geworden!
        wrapperBak.innerHTML = `<iframe src="${go2rtcBaseUrl}?src=cam1" frameborder="0" scrolling="no" style="width: 100%; height: 100%; pointer-events: none;"></iframe>`;
    }

    const wrapperCam2 = document.getElementById('video-wrapper-cam2');
    if (wrapperCam2 && !wrapperCam2.innerHTML.includes('iframe')) {
        wrapperCam2.innerHTML = `<iframe src="${go2rtcBaseUrl}?src=cam2" frameborder="0" scrolling="no" style="width: 100%; height: 100%; pointer-events: none;"></iframe>`;
    }
}

function stopStream() {
    console.log("Stop streams (bespaart bandbreedte/batterij)");
    
    const wrapperBak = document.getElementById('video-wrapper-bak');
    if (wrapperBak) wrapperBak.innerHTML = ''; // Verwijdert de iframe en verbreekt de WebRTC connectie

    const wrapperCam2 = document.getElementById('video-wrapper-cam2');
    if (wrapperCam2) wrapperCam2.innerHTML = '';
}
