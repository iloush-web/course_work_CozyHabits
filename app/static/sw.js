// Service Worker для CozyHabits (PWA)
// Подними версию (v2 -> v3), когда поменял фронтенд (CSS/JS/шаблоны/иконки):
// это удалит старый кэш у пользователей и заставит подтянуть свежие файлы.
const CACHE_VERSION = 'cozy-v4';

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

// Приём пуша: показать уведомление (работает даже когда сайт закрыт)
self.addEventListener('push', (event) => {
    let data = { title: 'CozyHabits', body: '', url: '/' };
    try {
        if (event.data) {
            data = Object.assign(data, event.data.json());
        }
    } catch (e) {
        if (event.data) data.body = event.data.text();
    }

    event.waitUntil(
        self.registration.showNotification(data.title, {
            body: data.body,
            icon: '/static/images/icons/icon-192.png',
            badge: '/static/images/icons/icon-192.png',
            data: { url: data.url || '/' },
        })
    );
});

// Клик по уведомлению: открыть/сфокусировать сайт на нужной странице
self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    const targetUrl = (event.notification.data && event.notification.data.url) || '/';

    event.waitUntil(
        self.clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then((clientList) => {
                // если вкладка уже открыта — фокусируем её
                for (const client of clientList) {
                    if ('focus' in client) {
                        client.navigate(targetUrl);
                        return client.focus();
                    }
                }
                // иначе открываем новую
                if (self.clients.openWindow) {
                    return self.clients.openWindow(targetUrl);
                }
            })
    );
});
