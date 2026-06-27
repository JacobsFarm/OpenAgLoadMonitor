<div class="tab-content active">
    <div class="settings-grid">
        <button type="button" class="card settings-card" on:click={() => location.href='/config'}>
            <div class="settings-icon">🛠️</div>
            <div class="settings-text">
                <h3 style="margin-bottom: 5px; color: #fff;">Configuratie</h3>
                <p style="color: #aaa; font-size: 0.9rem;">Sensoren en systeeminstellingen</p>
            </div>
        </button>

        <button type="button" class="card settings-card" on:click={() => location.href='/voerplannen'}>
            <div class="settings-icon">📋</div>
            <div class="settings-text">
                <h3 style="margin-bottom: 5px; color: #fff;">Voerplannen</h3>
                <p style="color: #aaa; font-size: 0.9rem;">Rantsoenen beheren en laden</p>
            </div>
        </button>

        <button type="button" class="card settings-card" on:click={() => location.href='/kalibratie'}>
            <div class="settings-icon">⚖️</div>
            <div class="settings-text">
                <h3 style="margin-bottom: 5px; color: #fff;">Kalibratie</h3>
                <p style="color: #aaa; font-size: 0.9rem;">Nulpunt en schaalinstellingen</p>
            </div>
        </button>
    </div>
</div>

<style>
    /* settings-card is nu een <button>: reset de browser-knop-stijl zodat het
       er identiek uitziet als de oude clickable card, maar wel toetsenbord-/
       schermlezer-toegankelijk is. */
    .settings-card {
        width: 100%;
        text-align: left;
        font: inherit;
        color: inherit;
        border: none;
        cursor: pointer;
    }
</style>
