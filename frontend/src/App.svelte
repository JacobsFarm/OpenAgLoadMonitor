<script>
    import { onMount, onDestroy } from 'svelte';
    import Navigation from './components/Navigation.svelte';
    import Dashboard from './components/Dashboard.svelte';
    import Lading from './components/Lading.svelte';
    import Camera from './components/Camera.svelte';
    import Settings from './components/Settings.svelte';

    // State variabelen
    let activeTab = 'dashboard-tab';
    let gewicht = 0;
    
    // Deze kwamen eerst uit Jinja, zorg dat je API deze nu meestuurt!
    let stap = "Stap 1"; 
    let doel = 0;
    let addSecondCamera = true; // Komt normaliter uit je config

    let pollingInterval;

    // Start data polling wanneer de app laadt
    onMount(() => {
        pollingInterval = setInterval(async () => {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                if (data.gewicht !== undefined) {
                    gewicht = data.gewicht;
                }
                // Update hier ook stap en doel als je API die meestuurt
                if (data.stap) stap = data.stap;
                if (data.doel) doel = data.doel;
            } catch (err) {
                console.error("API Fout:", err);
            }
        }, 100);
    });

    onDestroy(() => {
        clearInterval(pollingInterval);
    });
</script>

<main class="app-wrapper">
    <Navigation bind:activeTab />

    {#if activeTab === 'dashboard-tab'}
        <Dashboard {gewicht} {stap} {doel} />
    {:else if activeTab === 'numbers-tab'}
        <Lading {gewicht} />
    {:else if activeTab === 'stream-tab'}
        <Camera {addSecondCamera} />
    {:else if activeTab === 'settings-tab'}
        <Settings />
    {/if}
</main>