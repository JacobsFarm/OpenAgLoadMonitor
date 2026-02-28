<script>
    export let gewicht;
    export let stap;
    export let doel;
</script>

<div class="tab-content active">
    <div class="grid-container">
        <div class="card weight-card">
            <div class="card-header">Totaal Gewicht <span>⚖️</span></div>
            <div class="weight-display">
                <span class="weight-value">{gewicht}</span>
                <span class="weight-unit">KG</span>
            </div>
            <div class="weight-sub">Laatste vracht: 4500 kg</div>
        </div>

        <div class="card plan-card">
            <div class="card-header">Huidige Taak <span class="step-badge">{stap}</span></div>
            <div class="progress-section">
                <div class="progress-info" style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                    <strong>{stap}</strong>
                    <span>725 / {doel} KG</span>
                </div>
                <div class="progress-track">
                    <div class="progress-fill" style="width: 72.5%;"></div>
                </div>
            </div>
        </div>
        
        <div class="actions-container">
            <button class="action-btn secondary">-</button>
            <button class="action-btn primary">Volgende Stap</button>
            <button class="action-btn secondary">+</button>
        </div>
    </div>
</div>