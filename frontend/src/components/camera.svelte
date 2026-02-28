<script>
    import { onMount } from 'svelte';
    export let addSecondCamera;
    
    let go2rtcBaseUrl = '';
    let showStreams = true;

    onMount(() => {
        // Zorg dat we het huidige IP/hostname pakken net als in main.js
        go2rtcBaseUrl = `http://${window.location.hostname}:1984/webrtc.html`;
    });

    function restartStreams() {
        showStreams = false;
        setTimeout(() => {
            showStreams = true;
        }, 500);
    }
</script>

<div class="tab-content active">
    {#if showStreams && go2rtcBaseUrl}
        <div class="card">
            <div class="card-header">Camera 1 (Bak) <span>📹</span></div>
            <div class="video-wrapper" style="aspect-ratio: 16/9; background: #000; border-radius: 8px; overflow: hidden;">
                <iframe src="{go2rtcBaseUrl}?src=cam1" frameborder="0" scrolling="no" style="width: 100%; height: 100%; pointer-events: none;" title="Camera 1"></iframe>
            </div>
        </div>

        {#if addSecondCamera}
        <div class="card" style="margin-top: 15px;">
            <div class="card-header">Camera 2 (Overzicht) <span>📹</span></div>
            <div class="video-wrapper" style="aspect-ratio: 16/9; background: #000; border-radius: 8px; overflow: hidden;">
                <iframe src="{go2rtcBaseUrl}?src=cam2" frameborder="0" scrolling="no" style="width: 100%; height: 100%; pointer-events: none;" title="Camera 2"></iframe>
            </div>
        </div>
        {/if}
    {/if}

    <div class="stream-controls" style="margin-top: 15px;">
        <div class="status-text">● Live Verbinding (WebRTC)</div>
        <button on:click={restartStreams} class="action-btn primary full-width" style="margin-top: 15px;">🔄 Herstart Streams</button>
    </div>
</div>
