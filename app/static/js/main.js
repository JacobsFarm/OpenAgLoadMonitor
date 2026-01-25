// Globale variabele voor de videospeler
let player = null;

document.addEventListener("DOMContentLoaded", function() {
    console.log("Tractor Monitor JS geladen!");

    // 1. Start direct met data ophalen (Polling)
    startDataPolling();

    // 2. Setup Tab Navigatie
    const tabLinks = document.querySelectorAll('.tab-link');
    
    tabLinks.forEach(button => {
        button.addEventListener('click', function() {
            const targetTabId = this.getAttribute('data-tab');
            
            // Verwijder active class van alle knoppen en content
            tabLinks.forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });

            // Activeer de aangeklikte tab
            this.classList.add('active');
            document.getElementById(targetTabId).classList.add('active');

            // Video logica: alleen afspelen als tab open is (bespaart data)
            if (targetTabId === 'stream-tab') {
                startStream();
            } else {
                 stopStream();
            }
        });
    });

    // 3. Setup Herstart knop
    const restartBtn = document.getElementById('restart-btn');
    if (restartBtn) {
        restartBtn.addEventListener('click', function() {
            stopStream();
            setTimeout(startStream, 500);
        });
    }
});

// --- FUNCTIE: Data ophalen van de API ---
function startDataPolling() {
    console.log("Polling gestart...");
    
    setInterval(() => {
        fetch('/api/status')
            .then(response => response.json())
            .then(data => {
                // UNCOMMENT DEZE REGEL OM TE ZIEN WAT ER BINNENKOMT:
                // console.log("Data binnen:", data); 
                
                if(data.gewicht !== undefined) {
                    updateDashboard(data.gewicht);
                }
            })
            .catch(err => console.error("API Fout (is de server online?):", err));
    }, 100); // Elke 0.1 seconde
}

function updateDashboard(weight) {
    // Update de grote getallen op Tab 1 en Tab 2
    const weightDisplays = document.querySelectorAll('.weight-value, .clean-number');
    
    weightDisplays.forEach(el => {
        el.innerText = weight;
    });
}

// --- FUNCTIE: JSMpeg Stream (Websocket 8080) ---
function startStream() {
    if (player) return; // Draait al

    const canvas = document.getElementById('video-canvas');
    // Verbind met de JSMpeg server op poort 8080
    const streamUrl = 'ws://' + window.location.hostname + ':8080/';

    console.log("Start JSMpeg op:", streamUrl);

    player = new JSMpeg.Player(streamUrl, {
        canvas: canvas, 
        autoplay: true, 
        audio: false,   
        loop: true      
    });
}

function stopStream() {
    if (player) {
        console.log("Stream gestopt");
        player.destroy();
        player = null;
    }
}