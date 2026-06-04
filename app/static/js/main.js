console.log('Flask App loaded');

// Регистрация service worker (PWA). sw.js отдаётся с корня сайта,
// чтобы его scope покрывал всё приложение, а не только /static/.
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js')
            .then((reg) => console.log('SW registered:', reg.scope))
            .catch((err) => console.log('SW registration failed:', err));
    });
}

// ===== Push-уведомления =====

// VAPID-ключ приходит в base64url, а Push API ждёт Uint8Array
function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const raw = atob(base64);
    const arr = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i++) arr[i] = raw.charCodeAt(i);
    return arr;
}

// Поддерживает ли браузер пуши вообще
function pushSupported() {
    return ('serviceWorker' in navigator) && ('PushManager' in window) && ('Notification' in window);
}

// Включить уведомления: спросить разрешение -> подписаться -> отправить подписку на сервер
async function enablePush(btn) {
    if (!pushSupported()) {
        alert('Ваш браузер не поддерживает уведомления.\nНа iPhone сначала добавьте сайт на главный экран.');
        return;
    }

    // 1. разрешение пользователя
    const permission = await Notification.requestPermission();
    if (permission !== 'granted') {
        alert('Уведомления не разрешены. Можно включить позже в настройках.');
        return;
    }

    if (btn) { btn.disabled = true; btn.textContent = 'Подключаем…'; }

    try {
        const reg = await navigator.serviceWorker.ready;

        // 2. публичный VAPID-ключ с сервера
        const keyResp = await fetch('/push/public-key');
        const { publicKey } = await keyResp.json();

        // 3. оформляем подписку в браузере
        const sub = await reg.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array(publicKey),
        });

        // 4. отправляем подписку на сервер
        await fetch('/push/subscribe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(sub),
        });

        if (btn) btn.textContent = 'Уведомления включены ✓';
    } catch (err) {
        console.error('Push subscribe failed:', err);
        alert('Не удалось включить уведомления.');
        if (btn) { btn.disabled = false; btn.textContent = 'Включить уведомления'; }
    }
}

// Тестовый пуш самому себе
async function sendTestPush() {
    try {
        const resp = await fetch('/push/test', { method: 'POST' });
        const data = await resp.json();
        if (!data.sent) {
            alert('Сначала включите уведомления (и проверьте, что подписка активна).');
        }
    } catch (e) {
        console.error(e);
    }
}

// Навешиваем обработчики на кнопки, если они есть на странице
document.addEventListener('DOMContentLoaded', () => {
    const enableBtn = document.getElementById('push-enable-btn');
    if (enableBtn) {
        enableBtn.addEventListener('click', () => enablePush(enableBtn));
    }
    const testBtn = document.getElementById('push-test-btn');
    if (testBtn) {
        testBtn.addEventListener('click', sendTestPush);
    }
});
