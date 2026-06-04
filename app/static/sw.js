// Service Worker для CozyHabits (PWA)
// Версию меняй при обновлении, чтобы сбросить кэш.
const CACHE_VERSION = 'cozy-v1';

// Установка — сразу активируем новый SW
self.addEventListener('install', (event) => {
    self.skipWaiting();
});

// Активация — подчищаем старые кэши
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(
                keys.filter((k) => k !== CACHE_VERSION).map((k) => caches.delete(k))
            )
        ).then(() => self.clients.claim())
    );
});

// Сетевой запрос: сначала сеть, при отсутствии — кэш (network-first).
// Для трекера привычек важна свежесть данных, поэтому кэш — только запасной.
self.addEventListener('fetch', (event) => {
    const req = event.request;

    // кэшируем только GET (POST-формы трогать нельзя)
    if (req.method !== 'GET') {
        return;
    }

    event.respondWith(
        fetch(req)
            .then((res) => {
                // кладём свежую копию в кэш
                const copy = res.clone();
                caches.open(CACHE_VERSION).then((cache) => cache.put(req, copy));
                return res;
            })
            .catch(() => caches.match(req))   // нет сети — отдаём из кэша
    );
});
