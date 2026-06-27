// Service worker voor AgLoadMonitor (PWA).
// Doel: de app-schil (HTML/JS/CSS/iconen) offline beschikbaar maken, zodat de
// app op de telefoon als app opent. Live data (/api) en videostreams
// (/video_feed_*) gaan ALTIJD direct over het netwerk en worden nooit gecached.

const CACHE = 'agload-shell-v1';

self.addEventListener('install', (event) => {
  // Nieuwe service worker meteen activeren
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(['/', '/manifest.webmanifest']))
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  const url = new URL(req.url);

  // Alleen same-origin GET's afhandelen
  if (req.method !== 'GET' || url.origin !== self.location.origin) {
    return;
  }

  // Nooit cachen: live API en videostreams -> altijd netwerk
  if (url.pathname.startsWith('/api') || url.pathname.startsWith('/video_feed')) {
    return; // laat de browser het normaal afhandelen
  }

  // Navigatie (de app zelf): netwerk eerst, val terug op gecachete schil
  if (req.mode === 'navigate') {
    event.respondWith(
      fetch(req).catch(() => caches.match('/'))
    );
    return;
  }

  // Statische assets: stale-while-revalidate
  event.respondWith(
    caches.match(req).then((cached) => {
      const network = fetch(req).then((res) => {
        if (res && res.status === 200) {
          const copy = res.clone();
          caches.open(CACHE).then((cache) => cache.put(req, copy));
        }
        return res;
      }).catch(() => cached);
      return cached || network;
    })
  );
});
