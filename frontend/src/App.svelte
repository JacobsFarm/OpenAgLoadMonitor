<script>
    import { onMount, onDestroy } from 'svelte';
    import Navigation from './components/navigation.svelte';
    import Dashboard from './components/dashboard.svelte';
    import Lading from './components/lading.svelte';
    import Camera from './components/camera.svelte';
    import Settings from './components/settings.svelte';
    
    // 1. Importeer je nieuwe config pagina
    import ConfigPage from './components/config.svelte'; 

    // State variabelen
    let activeTab = 'dashboard-tab';
    let gewicht = 0;
    let stap = "Stap 1";
    let doel = 0;

    // 2. Check de huidige URL in de browser
    let currentPath = window.location.pathname;

    // Onbekende routes worden door Flask naar de SPA gestuurd; map de URL naar
    // de juiste tab zodat bv. /settings direct het instellingen-tabblad toont.
    const PATH_TO_TAB = {
        '/settings': 'settings-tab',
        '/numbers': 'numbers-tab',
        '/stream': 'stream-tab',
    };
    if (currentPath !== '/config' && PATH_TO_TAB[currentPath]) {
        activeTab = PATH_TO_TAB[currentPath];
    }

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
                // Foutmelding optioneel weglaten om console spam te voorkomen
                console.error("API Fout:", err); 
            }
        }, 100);
    });

    onDestroy(() => {
        clearInterval(pollingInterval);
    });
</script>

<main class="app-wrapper">
    {#if currentPath === '/config'}
        <ConfigPage />
    
    {:else}
        <Navigation bind:activeTab />

        {#if activeTab === 'dashboard-tab'}
            <Dashboard {gewicht} {stap} {doel} />
        {:else if activeTab === 'numbers-tab'}
            <Lading {gewicht} />
        {:else if activeTab === 'stream-tab'}
            <Camera />
        {:else if activeTab === 'settings-tab'}
            <Settings />
        {/if}
    {/if}
</main>
