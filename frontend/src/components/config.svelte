<script>
    import { onMount } from 'svelte';

    let configData = {};
    let isLoading = true;
    let saveMessage = '';
    let isError = false;

    // Wachtwoord-zichtbaarheid voor de OCR-camera
    let showPassOCR = false;

    // Lijst met bekende camera merken en hun standaard stream-pad
    const cameraBrands = {
        "hikvision": "/h264Preview_01_sub",
        "hikvision_main": "/Streaming/Channels/101",
        "dahua": "/cam/realmonitor?channel=1&subtype=1",
        "uniview": "/media/video1",
        "tapo": "/stream2",
        "custom": ""
    };

    // Dynamische lijst kijk-camera's: voeg er zoveel toe als je wilt.
    let cameras = [];
    let camOCR = { user: 'admin', pass: '', ip: '', brand: 'hikvision', path: '' };

    function newCamera(name) {
        return { name: name || '', user: 'admin', pass: '', ip: '', brand: 'hikvision', path: '', show: false };
    }

    function addCamera() {
        cameras = [...cameras, newCamera(`Camera ${cameras.length + 1}`)];
    }

    function removeCamera(index) {
        cameras = cameras.filter((_, i) => i !== index);
    }

    function parseRtspUrl(url, camObj) {
        if (!url || !url.startsWith('rtsp://')) return;
        try {
            const urlParts = new URL(url);
            camObj.user = urlParts.username || 'admin';
            camObj.pass = urlParts.password || '';
            camObj.ip = urlParts.hostname || '';

            let fullPath = urlParts.pathname + urlParts.search;

            camObj.brand = 'custom';
            camObj.path = fullPath;
            for (const [merk, pad] of Object.entries(cameraBrands)) {
                if (pad === fullPath) {
                    camObj.brand = merk;
                    break;
                }
            }
        } catch (e) {
            console.warn("Kon RTSP URL niet netjes opknippen:", url);
            camObj.brand = 'custom';
            camObj.path = url;
        }
    }

    function buildRtspUrl(camObj) {
        if (!camObj.ip) return "";
        let finalPath = camObj.brand === 'custom' ? camObj.path : cameraBrands[camObj.brand];
        if (!finalPath.startsWith('/')) finalPath = '/' + finalPath;

        return `rtsp://${camObj.user}:${camObj.pass}@${camObj.ip}:554${finalPath}`;
    }

    onMount(async () => {
        try {
            const res = await fetch('/api/config');
            if (res.ok) {
                configData = await res.json();

                // Kijk-camera's inladen: nieuw CAMERAS-array of oude losse keys.
                if (Array.isArray(configData.CAMERAS) && configData.CAMERAS.length) {
                    cameras = configData.CAMERAS.map((c, i) => {
                        const obj = newCamera(c.name || `Camera ${i + 1}`);
                        parseRtspUrl(c.url, obj);
                        return obj;
                    });
                } else {
                    const c1 = newCamera('Bak');
                    parseRtspUrl(configData.RTSP_URL_1, c1);
                    cameras = [c1];
                    if (configData.ADD_SECOND_CAMERA) {
                        const c2 = newCamera('Overzicht');
                        parseRtspUrl(configData.RTSP_URL_2, c2);
                        cameras = [...cameras, c2];
                    }
                }
                if (!cameras.length) cameras = [newCamera('Camera 1')];

                parseRtspUrl(configData.RTSP_URL_OCR, camOCR);
                camOCR = camOCR;

                // Defaults voor oudere config-bestanden
                if (configData.OCR_ENABLED === undefined) configData.OCR_ENABLED = true;
                if (configData.SHOW_OCR_IN_CAMERAS === undefined) configData.SHOW_OCR_IN_CAMERAS = false;
            }
        } catch (error) {
            console.error("Netwerkfout:", error);
        } finally {
            isLoading = false;
        }
    });

    async function saveConfig() {
        configData.CAMERAS = cameras.map((c, i) => ({
            name: c.name || `Camera ${i + 1}`,
            url: buildRtspUrl(c),
        }));
        // Oude losse camera-keys opruimen zodat de array de enige bron is.
        delete configData.RTSP_URL_1;
        delete configData.RTSP_URL_2;
        delete configData.ADD_SECOND_CAMERA;

        configData.RTSP_URL_OCR = buildRtspUrl(camOCR);

        try {
            const res = await fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(configData)
            });

            if (res.ok) {
                isError = false;
                saveMessage = '✅ Instellingen succesvol opgeslagen!';
                setTimeout(() => saveMessage = '', 4000);
            } else {
                throw new Error("Server fout");
            }
        } catch (error) {
            isError = true;
            saveMessage = '❌ Fout bij opslaan.';
        }
    }

    function goBack() { location.href = '/settings'; }
</script>

<div class="tab-content active">
    <div class="card" style="max-width: 900px; margin: 0 auto; display: block;">

        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px;">
            <h2 style="color: var(--text-main); margin: 0;">Systeem Configuratie</h2>
            <button class="action-btn secondary" style="padding: 10px 15px; font-size: 1rem;" on:click={goBack}>
                ⬅ Terug
            </button>
        </div>

        {#if isLoading}
            <p class="status-text">Gegevens inladen...</p>
        {:else}
            <form on:submit|preventDefault={saveConfig}>

                <div class="cam-section-header">
                    <span>Kijk-camera's</span>
                    <button type="button" class="action-btn secondary add-cam-btn" on:click={addCamera}>
                        ➕ Camera toevoegen
                    </button>
                </div>

                {#each cameras as cam, i (i)}
                    <div class="cam-block">
                        <div class="card-header cam-block-header">
                            <input
                                class="cam-name-input"
                                type="text"
                                bind:value={cam.name}
                                placeholder={`Camera ${i + 1}`}
                                title="Naam van deze camera"
                            />
                            <button
                                type="button"
                                class="remove-cam-btn"
                                title="Camera verwijderen"
                                disabled={cameras.length <= 1}
                                on:click={() => removeCamera(i)}
                            >✕</button>
                        </div>
                        <div class="grid-2-col">
                            <label class="form-group">
                                <span>IP Adres</span>
                                <input type="text" bind:value={cam.ip} placeholder="192.168..." />
                            </label>
                            <label class="form-group">
                                <span>Cameramerk</span>
                                <select bind:value={cam.brand}>
                                    <option value="hikvision">Hikvision / Safire (Sub-stream)</option>
                                    <option value="hikvision_main">Hikvision / Safire (Main-stream)</option>
                                    <option value="dahua">Dahua</option>
                                    <option value="uniview">Uniview</option>
                                    <option value="tapo">TP-Link Tapo</option>
                                    <option value="custom">Overig / Handmatig</option>
                                </select>
                            </label>
                            <label class="form-group">
                                <span>Gebruikersnaam</span>
                                <input type="text" bind:value={cam.user} />
                            </label>
                            <label class="form-group">
                                <span>Wachtwoord</span>
                                <input
                                    type={cam.show ? "text" : "password"}
                                    bind:value={cam.pass}
                                    on:focus={() => cam.show = true}
                                    on:blur={() => cam.show = false}
                                    placeholder="***"
                                />
                            </label>
                        </div>
                        {#if cam.brand === 'custom'}
                            <label class="form-group" style="margin-top: 10px;">
                                <span>Aangepast Stream Pad (bijv. /h264Preview_01_sub)</span>
                                <input type="text" bind:value={cam.path} />
                            </label>
                        {/if}
                    </div>
                {/each}

                <div class="cam-block">
                    <div class="card-header cam-block-header">
                        <span>Camera OCR (Display Uitlezing)</span>
                    </div>

                    <div class="ocr-toggles">
                        <label class="checkbox-group">
                            <input type="checkbox" bind:checked={configData.OCR_ENABLED} />
                            <span>Gewicht uitlezen (OCR) inschakelen — uit voor bijv. opraapwagen</span>
                        </label>
                        <label class="checkbox-group">
                            <input type="checkbox" bind:checked={configData.SHOW_OCR_IN_CAMERAS} />
                            <span>Deze camera ook tonen in de camera-weergave</span>
                        </label>
                    </div>

                    <div class="grid-2-col">
                        <label class="form-group">
                            <span>IP Adres</span>
                            <input type="text" bind:value={camOCR.ip} placeholder="192.168..." />
                        </label>
                        <label class="form-group">
                            <span>Cameramerk</span>
                            <select bind:value={camOCR.brand}>
                                <option value="hikvision">Hikvision / Safire</option>
                                <option value="dahua">Dahua</option>
                                <option value="custom">Handmatig</option>
                            </select>
                        </label>
                        <label class="form-group">
                            <span>Gebruikersnaam</span>
                            <input type="text" bind:value={camOCR.user} />
                        </label>
                        <label class="form-group">
                            <span>Wachtwoord</span>
                            <input
                                type={showPassOCR ? "text" : "password"}
                                bind:value={camOCR.pass}
                                on:focus={() => showPassOCR = true}
                                on:blur={() => showPassOCR = false}
                                placeholder="***"
                            />
                        </label>
                    </div>
                </div>

                <div class="card-header" style="margin-top: 30px;">Systeem & Video Modus</div>
                <div class="grid-2-col">
                    <label class="form-group">
                        <span>Video Bron Type</span>
                        <select bind:value={configData.VIDEO_SOURCE_TYPE}>
                            <option value="file">Lokaal Bestand (.mp4 test)</option>
                            <option value="stream">Live Netwerk Stream (RTSP)</option>
                        </select>
                    </label>
                    <label class="form-group">
                        <span>Confidence Threshold (0.0 - 1.0)</span>
                        <input type="number" step="0.05" min="0" max="1" bind:value={configData.CONFIDENCE_THRESHOLD} />
                    </label>
                </div>

                <div class="toggle-row">
                    <label class="checkbox-group">
                        <input type="checkbox" bind:checked={configData.AUTO_OPEN_BROWSER} />
                        <span>Browser automatisch openen bij opstart</span>
                    </label>
                    <label class="checkbox-group">
                        <input type="checkbox" bind:checked={configData.KIOSK_MODE} />
                        <span>Kiosk-modus (schermvullend, voor het wagenscherm)</span>
                    </label>
                </div>

                <div class="actions-container" style="margin-top: 30px;">
                    <button type="submit" class="action-btn primary">Instellingen Opslaan</button>
                </div>

                {#if saveMessage}
                    <p class="status-text" style="margin-top: 20px; color: {isError ? '#e74c3c' : 'var(--accent-green)'}; text-align: center; font-weight: bold;">
                        {saveMessage}
                    </p>
                {/if}
            </form>
        {/if}
    </div>
</div>

<style>
    .cam-block {
        background: #1a1a1a;
        padding: 15px;
        border-radius: 12px;
        border: 1px solid #333;
        margin-bottom: 20px;
    }

    .cam-section-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin: 10px 0 14px;
        color: var(--text-main);
        font-weight: bold;
        font-size: 1.05rem;
    }
    .add-cam-btn {
        padding: 8px 14px;
        font-size: 0.9rem;
    }

    .cam-block-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 10px;
        margin-bottom: 12px;
    }
    .cam-name-input {
        flex: 1;
        background: #111;
        border: 1px solid #444;
        border-radius: 8px;
        color: var(--text-main);
        padding: 8px 10px;
        font-size: 1rem;
        font-weight: bold;
        font-family: inherit;
    }
    .cam-name-input:focus { outline: none; border-color: var(--accent-green); }

    .remove-cam-btn {
        flex: 0 0 auto;
        width: 34px;
        height: 34px;
        border-radius: 8px;
        background: #2a1414;
        border: 1px solid #6b2b2b;
        color: #e74c3c;
        cursor: pointer;
        font-size: 1rem;
        line-height: 1;
    }
    .remove-cam-btn:hover:not(:disabled) { background: #3a1a1a; }
    .remove-cam-btn:disabled { opacity: 0.35; cursor: not-allowed; }

    .ocr-toggles {
        display: flex;
        flex-direction: column;
        gap: 10px;
        margin-bottom: 14px;
    }
    .ocr-toggles .checkbox-group span { color: var(--text-muted); font-size: 0.9rem; }

    .grid-2-col {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 15px;
    }

    @media (max-width: 600px) {
        .grid-2-col {
            grid-template-columns: 1fr;
        }
    }

    /* Label omhult nu de control (toegankelijk) en blijft verticaal stapelen */
    .form-group { display: flex; flex-direction: column; gap: 6px; }

    .checkbox-group { display: flex; align-items: center; gap: 8px; cursor: pointer; }
    .checkbox-group input { width: 18px; height: 18px; cursor: pointer; }

    .toggle-row { display: flex; flex-direction: column; gap: 12px; margin-top: 18px; }
    .toggle-row .checkbox-group span { color: var(--text-muted); font-size: 0.9rem; }

    .form-group > span {
        color: var(--text-muted);
        font-size: 0.9rem;
    }

    input[type="text"], input[type="password"], input[type="number"], select {
        width: 100%;
        padding: 10px 12px;
        border-radius: 8px;
        background-color: #111;
        border: 1px solid #444;
        color: var(--text-main);
        font-size: 0.95rem;
        font-family: inherit;
    }

    input:focus, select:focus {
        outline: none;
        border-color: var(--accent-green);
    }
</style>
