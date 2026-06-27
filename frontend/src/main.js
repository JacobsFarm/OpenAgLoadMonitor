import { mount } from 'svelte';
import './global.css';
import App from './App.svelte';

const app = mount(App, {
    target: document.getElementById('app')
});

// Registreer de service worker (PWA). Alleen in productie, zodat de
// Vite dev-server (HMR) niet door de cache wordt gehinderd.
if ('serviceWorker' in navigator && import.meta.env.PROD) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js').catch((err) => {
            console.warn('Service worker registratie mislukt:', err);
        });
    });
}

export default app;