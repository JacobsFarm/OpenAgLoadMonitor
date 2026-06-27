<script>
    import { onMount, onDestroy } from 'svelte';
    export let addSecondCamera;

    // 'vertical' = onder elkaar, 'horizontal' = naast elkaar, 'grid' = raster
    let layout = 'vertical';
    let showStreams = true;

    // Per camera een cache-buster (om de MJPEG-<img> te herladen) en verbindingsstatus
    let bust = { cam1: Date.now(), cam2: Date.now() };
    let connected = { cam1: null, cam2: null }; // null = nog onbekend
    let backendReachable = true;

    let statusTimer;

    $: cams = [
        { key: 'cam1', label: 'Cam 1 · Bak' },
        ...(addSecondCamera ? [{ key: 'cam2', label: 'Cam 2 · Overzicht' }] : []),
    ];

    async function loadConfig() {
        try {
            const res = await fetch('/api/config');
            if (res.ok) {
                const cfg = await res.json();
                if (cfg.STREAM_LAYOUT) layout = cfg.STREAM_LAYOUT;
                if (cfg.ADD_SECOND_CAMERA !== undefined) addSecondCamera = cfg.ADD_SECOND_CAMERA;
            }
        } catch (e) {
            console.warn('Kon stream-config niet laden:', e);
        }
    }

    async function pollStatus() {
        try {
            const res = await fetch('/api/stream_status');
            if (res.ok) {
                const s = await res.json();
                connected = {
                    cam1: s.cam1 ? s.cam1.connected : false,
                    cam2: s.cam2 ? s.cam2.connected : false,
                };
                backendReachable = true;
            }
        } catch (e) {
            backendReachable = false; // backend niet bereikbaar: geen valse "geen signaal"-spam
        }
    }

    // Herlaad alle streams (bv. nadat de tablet uit slaapstand komt)
    function reloadAll() {
        const now = Date.now();
        bust = { cam1: now, cam2: now };
    }

    // Forceer herverbinden: laat de backend de RTSP opnieuw openen én herlaad de <img>
    async function reconnectCam(key) {
        try {
            await fetch(`/api/reconnect/${key}`, { method: 'POST' });
        } catch (e) {
            console.warn('Herverbinden mislukt:', e);
        }
        bust = { ...bust, [key]: Date.now() };
        // status snel opnieuw ophalen
        setTimeout(pollStatus, 1500);
    }

    function setLayout(newLayout) {
        layout = newLayout;
        fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ STREAM_LAYOUT: newLayout })
        }).catch((e) => console.warn('Kon layout niet opslaan:', e));
    }

    function restartStreams() {
        showStreams = false;
        reloadAll();
        setTimeout(() => { showStreams = true; }, 300);
    }

    // --- Wakker worden / netwerk terug: automatisch herverbinden ---
    function handleWake() {
        if (document.visibilityState === 'visible') {
            reloadAll();
            pollStatus();
        }
    }
    function handleOnline() {
        reloadAll();
        pollStatus();
    }

    onMount(() => {
        loadConfig();
        pollStatus();
        statusTimer = setInterval(pollStatus, 2500);

        document.addEventListener('visibilitychange', handleWake);
        window.addEventListener('online', handleOnline);
        window.addEventListener('pageshow', handleOnline);
    });

    onDestroy(() => {
        clearInterval(statusTimer);
        document.removeEventListener('visibilitychange', handleWake);
        window.removeEventListener('online', handleOnline);
        window.removeEventListener('pageshow', handleOnline);
    });
</script>

<div class="cam-tab">
    <div class="layout-controls">
        <button class:active={layout === 'vertical'} on:click={() => setLayout('vertical')} title="Onder elkaar">▤</button>
        <button class:active={layout === 'horizontal'} on:click={() => setLayout('horizontal')} title="Naast elkaar">▥</button>
        <button class:active={layout === 'grid'} on:click={() => setLayout('grid')} title="Raster">▦</button>
        <button class="restart" on:click={restartStreams} title="Herstart streams">🔄</button>
    </div>

    {#if showStreams}
        <div class="stream-grid layout-{layout}">
            {#each cams as cam (cam.key)}
                <div class="video-tile">
                    <span class="cam-tag">
                        <span class="dot"
                              class:ok={connected[cam.key] === true}
                              class:bad={connected[cam.key] === false && backendReachable}></span>
                        {cam.label}
                    </span>

                    <img src="/video_feed_{cam.key}?t={bust[cam.key]}" alt={cam.label} />

                    {#if connected[cam.key] === false && backendReachable}
                        <button class="reconnect-overlay" on:click={() => reconnectCam(cam.key)}>
                            <span class="ro-icon">⟳</span>
                            <span>Geen signaal</span>
                            <span class="ro-sub">Tik om opnieuw te verbinden</span>
                        </button>
                    {/if}
                </div>
            {/each}
        </div>
    {/if}
</div>

<style>
    .cam-tab {
        padding: 4px;
    }

    .layout-controls {
        display: flex;
        align-items: center;
        gap: 6px;
        margin-bottom: 6px;
    }
    .layout-controls button {
        padding: 6px 10px;
        border-radius: 6px;
        background: #1a1a1a;
        border: 1px solid #333;
        color: var(--text-main);
        cursor: pointer;
        font-size: 1rem;
        line-height: 1;
    }
    .layout-controls button.active {
        border-color: var(--accent-green);
        color: var(--accent-green);
    }
    .layout-controls .restart {
        margin-left: auto;
    }

    .stream-grid {
        display: grid;
        gap: 6px;
    }
    .stream-grid.layout-vertical {
        grid-template-columns: 1fr;
    }
    .stream-grid.layout-horizontal {
        grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    }
    .stream-grid.layout-grid {
        grid-template-columns: repeat(2, 1fr);
    }
    @media (max-width: 600px) {
        .stream-grid.layout-grid {
            grid-template-columns: 1fr;
        }
    }

    .video-tile {
        position: relative;
        background: #000;
        border-radius: 6px;
        overflow: hidden;
        line-height: 0;
        min-height: 120px;
    }
    .video-tile img {
        width: 100%;
        height: auto;
        display: block;
    }

    .cam-tag {
        position: absolute;
        top: 6px;
        left: 6px;
        z-index: 2;
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 2px 8px;
        border-radius: 6px;
        background: rgba(0, 0, 0, 0.55);
        color: #fff;
        font-size: 0.75rem;
        line-height: 1.4;
    }
    .dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #888;            /* onbekend */
        flex: 0 0 auto;
    }
    .dot.ok { background: var(--accent-green); }
    .dot.bad { background: #e74c3c; }

    .reconnect-overlay {
        position: absolute;
        inset: 0;
        z-index: 3;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 4px;
        border: none;
        background: rgba(0, 0, 0, 0.7);
        color: #fff;
        cursor: pointer;
        font-size: 0.95rem;
        line-height: 1.3;
    }
    .reconnect-overlay .ro-icon { font-size: 1.8rem; }
    .reconnect-overlay .ro-sub { font-size: 0.78rem; color: #bbb; }
</style>
