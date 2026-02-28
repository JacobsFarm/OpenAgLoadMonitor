<script>
    export let activeTab;
</script>

<nav class="tab-navigation">
    <button class="tab-link {activeTab === 'dashboard-tab' ? 'active' : ''}" on:click={() => activeTab = 'dashboard-tab'}>
        <span>📊</span>
    </button>
    <button class="tab-link {activeTab === 'numbers-tab' ? 'active' : ''}" on:click={() => activeTab = 'numbers-tab'}>
        <span>⚖️</span>
    </button>
    <button class="tab-link {activeTab === 'stream-tab' ? 'active' : ''}" on:click={() => activeTab = 'stream-tab'}>
        <span>📹</span>
    </button>
    <button class="tab-link {activeTab === 'settings-tab' ? 'active' : ''}" on:click={() => activeTab = 'settings-tab'}>
        <span>⚙️</span>
    </button>
</nav>