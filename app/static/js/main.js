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